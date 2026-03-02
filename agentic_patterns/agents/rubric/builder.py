"""Rubric build pipeline.

The pipeline has three phases:

  1. Extraction: each document chunk is sent to an LLM to pull out PoolItems
     (requirements or concerns). Runs in parallel across chunks.

  2. Merge passes: while the pool is larger than batch_size, cluster it by
     semantic similarity and run a merge agent on each cluster in parallel.
     The agent ejects outliers back to the pool and merges the coherent core
     into a single PoolItem with unified sources. Repeats until the pool fits
     in one batch or stops shrinking (convergence).

  3. Synthesis: the reduced pool is processed in sequential batches by an agent
     that has three tools -- find_similar, add_item, add_source -- backed by a
     persistent per-session Chroma VDB in the workspace. Because batches are
     sequential and add_item writes to the VDB immediately, every batch sees
     items committed by previous ones, preventing duplicates across batches.
     The VDB persists across turns so multi-turn agents don't lose state.
"""

import functools
import math
import uuid
from pathlib import PurePosixPath

from pydantic import BaseModel, Field

from agentic_patterns.agents.rubric.listener import RubricListener
from agentic_patterns.agents.rubric.models import (
    PoolItem,
    RequirementLevel,
    Rubric,
    RubricItem,
    SourceRef,
)
from agentic_patterns.core.agents.agents import get_agent
from agentic_patterns.core.agents.utils import run_parallel
from agentic_patterns.core.config.config import PROMPTS_DIR, SANDBOX_PREFIX
from agentic_patterns.core.prompt import load_prompt
from agentic_patterns.core.vectordb.clustering import cluster
from agentic_patterns.core.vectordb.embeddings import embed_text, embed_texts, get_embedder
from agentic_patterns.core.vectordb.models import Chunk, ChunkLevel, ClusterAlgorithm

_RUBRIC_PROMPTS = PROMPTS_DIR / "rubric"

# When the rubric already has more than this many items, the synthesis agent
# uses rubric_find_similar_items to search instead of receiving the full list.
_LARGE_RUBRIC_THRESHOLD = 50


# ---------------------------------------------------------------------------
# Private structured-output models (LLM responses, not part of public API)
# ---------------------------------------------------------------------------

class _MergeOutput(BaseModel):
    """What the merge agent returns for one cluster.

    merged_text: the single unified requirement text for the coherent core.
    ejected_indices: zero-based indices of items that did not belong in the cluster.
    """
    merged_text: str
    ejected_indices: list[int] = Field(default_factory=list)


class _ExtractedRequirement(BaseModel):
    """One requirement extracted from a policy chunk."""
    title: str
    requirement_level: RequirementLevel
    requirement_text: str
    evidence_required: list[str]


class _ExtractedRequirements(BaseModel):
    requirements: list[_ExtractedRequirement]


class _ExtractedConcerns(BaseModel):
    concerns: list[str]


# ---------------------------------------------------------------------------
# Prompt formatting helpers
# ---------------------------------------------------------------------------

def _format_pool_items(items: list[PoolItem]) -> str:
    """Format pool items for inclusion in an agent prompt.

    Each item shows its index (so the merge agent can reference ejected_indices),
    its text, and the source references the synthesis agent must pass to add_item.
    """
    parts = []
    for i, item in enumerate(items):
        sources_str = ", ".join(str(s) for s in item.sources)
        parts.append(f"[{i}] {item.text}\n    Sources: {sources_str}")
    return "\n\n".join(parts)


def _format_rubric_items(items: list[RubricItem]) -> str:
    """Format current rubric items for the synthesis agent (small-rubric path)."""
    return "\n".join(
        f"- [{item.item_id}] [{item.requirement_level.value}] {item.title}: {item.requirement_text}"
        for item in items
    )


# ---------------------------------------------------------------------------
# RubricBuilder
# ---------------------------------------------------------------------------

class RubricBuilder:
    """Builds and refines compliance rubrics from extracted text items.

    The pipeline has three phases:

    Phase 1 -- Extraction (build_from_policy / refine_with_history only):
        Each document chunk is sent to an LLM in parallel. For policy documents
        the LLM extracts structured requirements (title, MUST/SHOULD/MAY level,
        evidence needed). For history documents it extracts concern sentences.
        Each result becomes a PoolItem: a piece of text with one or more SourceRefs
        pointing back to the chunk it came from.

    Phase 2 -- Merge passes (build):
        When the pool is larger than batch_size it cannot be sent to a single LLM
        call. The pool is clustered by semantic similarity into groups of ~batch_size.
        A merge agent runs on each group in parallel: it ejects items that do not
        belong and merges the coherent core into one PoolItem whose sources are the
        union of all merged items. This repeats until the pool fits in one batch or
        stops shrinking (convergence guard).

    Phase 3 -- Synthesis (build):
        The reduced pool is processed in sequential batches. A synthesis agent
        receives each batch and decides for every PoolItem whether it is already
        covered by the rubric or genuinely new, using three tools:
          - rubric_find_similar_items: cosine search over the rubric VDB
          - rubric_add_item: creates a RubricItem, appends it to the live items
            list, and writes it to the VDB immediately so the next tool call
            (within the same batch or the next) already sees it
          - rubric_add_source: records an additional SourceRef on an existing item
        Batches are sequential -- not parallel -- so the shared VDB state is
        always consistent and no two batches can independently add the same item.
        The VDB is a PersistentClient stored in the workspace (isolated per
        user/session), so it survives across turns in a multi-turn conversation.

    Entry points:
        build(items, rubric=None)  -- core method; rubric=None builds from scratch,
                                      pass an existing Rubric to refine it
        build_from_policy(index)   -- runs Phase 1 then delegates to build()
        refine_with_history(rubric, index)  -- module-level wrapper, same pattern
    """

    def __init__(
        self,
        config_name: str = "default",
        batch_size: int = 20,
        max_passes: int = 10,
        algorithm: ClusterAlgorithm = ClusterAlgorithm.AGGLOMERATIVE,
        listener: RubricListener | None = None,
    ) -> None:
        self._config_name = config_name
        self._batch_size = batch_size
        self._max_passes = max_passes
        self._algorithm = algorithm
        self._listener = listener or RubricListener()
        self._embedder = get_embedder()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def build(self, items: list[PoolItem], rubric: Rubric | None = None) -> Rubric:
        """Phase 2 + 3: merge passes to reduce the pool, then synthesize into a Rubric."""
        pool = list(items)

        # Phase 2: merge passes -- keep going until the pool fits in one batch
        # or until no further reduction is possible (convergence guard).
        for pass_num in range(1, self._max_passes + 1):
            if len(pool) <= self._batch_size:
                break
            await self._listener.on_pass_start(pass_num, len(pool))
            new_pool = await self._merge_pass(pool, pass_num)
            if len(new_pool) >= len(pool):   # no progress -- stop early
                break
            pool = new_pool

        # Phase 3: synthesize the (now small) pool into rubric items.
        return await self._synthesis_phase(pool, rubric)

    async def build_from_policy(self, policy_index, rubric_name: str) -> Rubric:
        """Phase 1 + pipeline: extract requirements from policy chunks, then build."""
        pool = await self._extract_all(policy_index, extractor=self._extract_requirements)
        return await self.build(pool, rubric=Rubric(name=rubric_name))

    # ------------------------------------------------------------------
    # Phase 1: extraction
    # ------------------------------------------------------------------

    async def _extract_all(self, index, extractor) -> list[PoolItem]:
        """Fetch all chunks from a VectorDB and run extractor on each in parallel."""
        collection_name = index.collection.name
        all_docs = index.collection.get(include=["documents"])
        ids = all_docs.get("ids", [])
        texts = all_docs.get("documents", []) or []

        n_chunks = len(ids)
        n_done = 0
        await self._listener.on_pass_start(-1, n_chunks)

        async def _tracked(doc_id: str, text: str) -> list[PoolItem]:
            nonlocal n_done
            items = await extractor(doc_id, text, collection_name)
            n_done += 1
            await self._listener.on_group_done(-1, n_done, n_chunks, items=[i.label for i in items])
            return items

        results = await run_parallel([_tracked(doc_id, text) for doc_id, text in zip(ids, texts)])
        return [item for chunk_items in results for item in chunk_items]

    async def _extract_requirements(self, doc_id: str, text: str, collection_name: str) -> list[PoolItem]:
        """LLM call: extract MUST/SHOULD/MAY requirements from one policy chunk."""
        prompt = load_prompt(_RUBRIC_PROMPTS / "extract_requirements.md", chunk_text=text)
        agent = get_agent(config_name=self._config_name, output_type=_ExtractedRequirements)
        result = await agent.run(prompt)
        source = SourceRef(doc_id=doc_id, collection_name=collection_name)
        items = []
        for r in result.output.requirements:
            text = f"[{r.requirement_level.value}] {r.title}\n{r.requirement_text}"
            if r.evidence_required:
                text += "\nEvidence required: " + "; ".join(r.evidence_required)
            items.append(PoolItem(text=text, sources=[source], label=f"[{r.requirement_level.value}] {r.title}"))
        return items

    async def _extract_concerns(self, doc_id: str, text: str, collection_name: str) -> list[PoolItem]:
        """LLM call: extract concern sentences from one history chunk."""
        prompt = load_prompt(_RUBRIC_PROMPTS / "extract_concerns.md", chunk_text=text)
        agent = get_agent(config_name=self._config_name, output_type=_ExtractedConcerns)
        result = await agent.run(prompt)
        source = SourceRef(doc_id=doc_id, collection_name=collection_name)
        return [PoolItem(text=concern, sources=[source], label=concern[:80]) for concern in result.output.concerns]

    # ------------------------------------------------------------------
    # Phase 2: merge passes
    # ------------------------------------------------------------------

    async def _merge_pass(self, pool: list[PoolItem], pass_num: int) -> list[PoolItem]:
        """Cluster the pool and run the merge agent on each cluster in parallel."""
        groups = self._cluster_pool(pool)
        n_total = len(groups)
        n_done = 0

        async def _process_group(group_items: list[PoolItem], group_num: int) -> list[PoolItem]:
            nonlocal n_done
            await self._listener.on_group_start(pass_num, group_num, n_total)
            merged = await self._run_merge_agent(group_items)
            n_done += 1
            await self._listener.on_group_done(pass_num, n_done, n_total)
            return merged

        results = await run_parallel([_process_group(g, i + 1) for i, g in enumerate(groups)])
        return [item for sublist in results for item in sublist]

    def _cluster_pool(self, pool: list[PoolItem]) -> list[list[PoolItem]]:
        """Partition pool into ~batch_size clusters by semantic similarity.

        Uses doc_id=str(index) so we can map cluster items back to the original pool.
        """
        n_clusters = max(1, math.ceil(len(pool) / self._batch_size))
        chunks = [
            Chunk(doc_id=str(i), text=item.text, level=ChunkLevel.PARAGRAPH, parent_id=None, metadata={})
            for i, item in enumerate(pool)
        ]
        result = cluster(chunks, n_clusters=n_clusters, algorithm=self._algorithm, embedder=self._embedder)
        return [[pool[int(ci.doc_id)] for ci in c.items] for c in result.clusters]

    async def _run_merge_agent(self, group: list[PoolItem]) -> list[PoolItem]:
        """LLM call: merge a cluster into one PoolItem, eject outliers back to pool.

        Returns [merged_item] + ejected_items. If the agent finds no coherent core,
        all items are returned unchanged.
        """
        if len(group) == 1:
            return group

        prompt = load_prompt(_RUBRIC_PROMPTS / "group_merge.md", items=_format_pool_items(group))
        result = await self._merge_agent.run(prompt)
        output: _MergeOutput = result.output

        ejected_set = set(i for i in output.ejected_indices if 0 <= i < len(group))
        ejected = [group[i] for i in sorted(ejected_set)]
        coherent = [item for i, item in enumerate(group) if i not in ejected_set]

        if not coherent or not output.merged_text.strip():
            # No coherent core found -- return all items unchanged
            return group

        # Accumulate sources from all coherent items, deduplicating by (doc_id, collection)
        seen: dict[tuple, SourceRef] = {}
        for item in coherent:
            for s in item.sources:
                seen[(s.doc_id, s.collection_name)] = s
        merged = PoolItem(text=output.merged_text, sources=list(seen.values()))
        return [merged] + ejected

    @functools.cached_property
    def _merge_agent(self):
        return get_agent(config_name=self._config_name, output_type=_MergeOutput)

    # ------------------------------------------------------------------
    # Phase 3: synthesis
    # ------------------------------------------------------------------

    async def _synthesis_phase(self, pool: list[PoolItem], existing_rubric: Rubric | None) -> Rubric:
        """Convert pool items into RubricItems via a tool-calling agent.

        The agent has three tools:
          - rubric_find_similar_items: cosine search over the rubric VDB
          - rubric_add_item: creates a RubricItem and writes it to both the
            in-memory items list and the VDB immediately, so the next tool
            call within the same batch (or the next batch) already sees it
          - rubric_add_source: records an additional SourceRef on an existing item

        The VDB is a per-session PersistentClient stored in the workspace.
        It persists across turns so multi-turn agents can refine incrementally.
        Batches are processed sequentially (not in parallel) so the shared VDB
        state is consistent -- no two batches can add the same item independently.
        """
        import chromadb
        from agentic_patterns.core.workspace import workspace_to_host_path

        rubric_name = existing_rubric.name if existing_rubric else "rubric"
        rubric_id = existing_rubric.rubric_id if existing_rubric else str(uuid.uuid4())[:8]

        # items is the live rubric being built -- tools mutate it in place.
        items: list[RubricItem] = list(existing_rubric.items) if existing_rubric else []

        # The VDB lives in the workspace, isolated per user/session.
        # Path: WORKSPACE_DIR/user_id/session_id/.rubric_synthesis/{rubric_id}
        vdb_path = workspace_to_host_path(PurePosixPath(SANDBOX_PREFIX) / ".rubric_synthesis" / rubric_id)
        vdb_path.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(vdb_path))
        collection = client.get_or_create_collection("rubric_synthesis")

        # Seed the VDB with any items already in the rubric (refine path).
        if items:
            embs = await embed_texts([i.requirement_text for i in items], self._embedder)
            collection.add(
                ids=[i.item_id for i in items],
                documents=[i.requirement_text for i in items],
                embeddings=embs,
                metadatas=[{"title": i.title} for i in items],
            )

        # ------------------------------------------------------------------
        # Tools -- closures over `items` and `collection`.
        # Each write goes to both so they stay in sync.
        # ------------------------------------------------------------------

        async def rubric_find_similar_items(text: str, top_k: int = 5) -> list[dict]:
            """Semantic search over current rubric items. Returns item_id, title, requirement_text, score."""
            if not items:
                return []
            emb = await embed_text(text, self._embedder)
            n = min(top_k, len(items))
            res = collection.query(
                query_embeddings=[emb], n_results=n,
                include=["documents", "metadatas", "distances"],
            )
            return [
                {
                    "item_id": iid,
                    "title": meta.get("title", ""),
                    "requirement_text": doc,
                    "score": round(1.0 - dist, 4),
                }
                for iid, meta, doc, dist in zip(
                    res["ids"][0], res["metadatas"][0], res["documents"][0], res["distances"][0]
                )
            ]

        async def rubric_add_item(
            title: str,
            requirement_level: str,
            requirement_text: str,
            evidence_required: list[str],
            sources: list[dict],
        ) -> str:
            """Add a new rubric item. Writes to both items list and VDB. Returns the new item_id."""
            item_id = f"r{len(items) + 1:03d}"
            source_refs = [SourceRef(doc_id=s["doc_id"], collection_name=s["collection_name"]) for s in sources]
            item = RubricItem(
                item_id=item_id,
                title=title,
                requirement_level=RequirementLevel(requirement_level),
                requirement_text=requirement_text,
                evidence_required=evidence_required,
                sources=source_refs,
            )
            items.append(item)
            emb = await embed_text(requirement_text, self._embedder)
            collection.add(
                ids=[item_id],
                documents=[requirement_text],
                embeddings=[emb],
                metadatas=[{"title": title}],
            )
            await self._listener.on_item_added(item_id, title, requirement_level)
            return item_id

        async def rubric_add_source(item_id: str, doc_id: str, collection_name: str) -> None:
            """Record an additional source reference on an existing rubric item."""
            for item in items:
                if item.item_id == item_id:
                    item.sources.append(SourceRef(doc_id=doc_id, collection_name=collection_name))
                    await self._listener.on_source_mapped(item_id, item.title)
                    return

        # ------------------------------------------------------------------
        # Batch loop -- sequential so the shared VDB stays consistent.
        # When the rubric is small, pass the full item list in the prompt.
        # When large, the agent uses rubric_find_similar_items instead.
        # ------------------------------------------------------------------

        use_tool_search = len(items) > _LARGE_RUBRIC_THRESHOLD
        prompt_file = "group_synthesize_with_tool.md" if use_tool_search else "group_synthesize.md"
        system_prompt = load_prompt(_RUBRIC_PROMPTS / prompt_file)

        batches = [pool[i : i + self._batch_size] for i in range(0, len(pool), self._batch_size)]
        await self._listener.on_pass_start(0, len(pool))

        for batch_num, batch in enumerate(batches, 1):
            await self._listener.on_group_start(0, batch_num, len(batches))

            if use_tool_search:
                user_msg = f"## Pool items to process\n\n{_format_pool_items(batch)}"
            else:
                # Include the current rubric so the agent can see it directly.
                # `items` grows as the agent adds items, so each batch sees all
                # items committed by previous batches.
                rubric_section = f"## Current rubric\n\n{_format_rubric_items(items)}\n\n" if items else ""
                user_msg = f"{rubric_section}## Pool items to process\n\n{_format_pool_items(batch)}"

            agent = get_agent(
                config_name=self._config_name,
                system_prompt=system_prompt,
                tools=[rubric_find_similar_items, rubric_add_item, rubric_add_source],
            )
            await agent.run(user_msg)
            await self._listener.on_group_done(0, batch_num, len(batches))

        rubric = Rubric(rubric_id=rubric_id, name=rubric_name, items=items)
        await self._listener.on_done(rubric)
        return rubric


# ---------------------------------------------------------------------------
# Convenience wrapper for Stage 2
# ---------------------------------------------------------------------------

async def refine_with_history(
    rubric: Rubric,
    history_index,
    config_name: str = "default",
    listener: RubricListener | None = None,
    **builder_kwargs,
) -> Rubric:
    """Phase 1 + pipeline: extract concerns from history chunks, refine existing rubric."""
    builder = RubricBuilder(config_name=config_name, listener=listener, **builder_kwargs)
    pool = await builder._extract_all(history_index, extractor=builder._extract_concerns)
    return await builder.build(pool, rubric=rubric)
