"""Rubric build pipeline: iterative merge-synthesize from extracted pool items."""

import functools
import math
import uuid

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
from agentic_patterns.core.config.config import PROMPTS_DIR
from agentic_patterns.core.prompt import load_prompt
from agentic_patterns.core.vectordb.clustering import cluster
from agentic_patterns.core.vectordb.embeddings import embed_text, embed_texts, get_embedder
from agentic_patterns.core.vectordb.models import Chunk, ChunkLevel, ClusterAlgorithm

_RUBRIC_PROMPTS = PROMPTS_DIR / "rubric"

# rubric items above this threshold use rubric_find_similar_items instead of full list in prompt
_LARGE_RUBRIC_THRESHOLD = 50


class _MergeOutput(BaseModel):
    """Structured output from the merge agent."""

    merged_text: str
    ejected_indices: list[int] = Field(default_factory=list)


class _ExtractedRequirement(BaseModel):
    title: str
    requirement_level: RequirementLevel
    requirement_text: str
    evidence_required: list[str]
    framework_mappings: dict[str, list[str]] = Field(default_factory=dict)
    tags: set[str] = Field(default_factory=set)


class _ExtractedRequirements(BaseModel):
    requirements: list[_ExtractedRequirement]


class _ExtractedConcerns(BaseModel):
    concerns: list[str]


def _format_pool_items(items: list[PoolItem]) -> str:
    parts = []
    for i, item in enumerate(items):
        sources_str = ", ".join(str(s) for s in item.sources)
        parts.append(f"[{i}] {item.text}\n    Sources: {sources_str}")
    return "\n\n".join(parts)


def _format_rubric_items(items: list[RubricItem]) -> str:
    return "\n".join(
        f"- [{item.item_id}] [{item.requirement_level.value}] {item.title}: {item.requirement_text}"
        for item in items
    )


class RubricBuilder:
    """Builds and refines rubrics using an iterative merge-synthesize pipeline.

    Both build-from-policy and refine-with-history flow through the same `build()` method.
    Intermediate merge passes cluster and reduce the pool; the synthesis phase commits items
    to the rubric through tool calls, using a shared ephemeral vector index for deduplication.
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

    async def build(self, items: list[PoolItem], rubric: Rubric | None = None) -> Rubric:
        """Run the pipeline: merge passes until pool fits in one batch, then synthesize.

        rubric=None starts from scratch; pass an existing Rubric to refine it.
        """
        pool = list(items)

        for pass_num in range(1, self._max_passes + 1):
            if len(pool) <= self._batch_size:
                break
            await self._listener.on_pass_start(pass_num, len(pool))
            new_pool = await self._merge_pass(pool, pass_num)
            if len(new_pool) >= len(pool):
                break
            pool = new_pool

        return await self._synthesis_phase(pool, rubric)

    async def build_from_policy(self, policy_index, rubric_name: str) -> Rubric:
        """Extract requirements from all policy chunks and build a rubric from scratch."""
        collection_name = policy_index.collection.name
        all_docs = policy_index.collection.get(include=["documents", "ids"])
        ids = all_docs.get("ids", [])
        texts = all_docs.get("documents", []) or []

        results = await run_parallel([
            self._extract_requirements(doc_id, text, collection_name)
            for doc_id, text in zip(ids, texts)
        ])
        pool = [item for chunk_items in results for item in chunk_items]
        return await self.build(pool, rubric=Rubric(name=rubric_name))

    async def _extract_requirements(self, doc_id: str, text: str, collection_name: str) -> list[PoolItem]:
        prompt = load_prompt(_RUBRIC_PROMPTS / "extract_requirements.md", chunk_text=text)
        agent = get_agent(config_name=self._config_name, output_type=_ExtractedRequirements)
        result = await agent.run(prompt)
        source = SourceRef(doc_id=doc_id, collection_name=collection_name)
        return [
            PoolItem(
                text=f"[{r.requirement_level.value}] {r.title}\n{r.requirement_text}",
                sources=[source],
            )
            for r in result.output.requirements
        ]

    async def _extract_concerns(self, doc_id: str, text: str, collection_name: str) -> list[PoolItem]:
        prompt = load_prompt(_RUBRIC_PROMPTS / "extract_concerns.md", chunk_text=text)
        agent = get_agent(config_name=self._config_name, output_type=_ExtractedConcerns)
        result = await agent.run(prompt)
        source = SourceRef(doc_id=doc_id, collection_name=collection_name)
        return [
            PoolItem(text=concern, sources=[source])
            for concern in result.output.concerns
        ]

    async def _merge_pass(self, pool: list[PoolItem], pass_num: int) -> list[PoolItem]:
        groups = self._cluster_pool(pool)
        n_total = len(groups)
        n_done = 0

        async def _process_group(group_items: list[PoolItem]) -> list[PoolItem]:
            nonlocal n_done
            merged = await self._run_merge_agent(group_items)
            n_done += 1
            await self._listener.on_group_done(pass_num, n_done, n_total)
            return merged

        results = await run_parallel([_process_group(g) for g in groups])
        return [item for sublist in results for item in sublist]

    def _cluster_pool(self, pool: list[PoolItem]) -> list[list[PoolItem]]:
        n_clusters = max(1, math.ceil(len(pool) / self._batch_size))
        chunks = [
            Chunk(doc_id=str(i), text=item.text, level=ChunkLevel.PARAGRAPH, parent_id=None, metadata={})
            for i, item in enumerate(pool)
        ]
        result = cluster(chunks, n_clusters=n_clusters, algorithm=self._algorithm, embedder=self._embedder)
        return [[pool[int(ci.doc_id)] for ci in c.items] for c in result.clusters]

    async def _run_merge_agent(self, group: list[PoolItem]) -> list[PoolItem]:
        if len(group) == 1:
            return group

        prompt = load_prompt(_RUBRIC_PROMPTS / "group_merge.md", items=_format_pool_items(group))
        result = await self._merge_agent.run(prompt)
        output: _MergeOutput = result.output

        ejected_set = set(i for i in output.ejected_indices if 0 <= i < len(group))
        ejected = [group[i] for i in sorted(ejected_set)]
        coherent = [item for i, item in enumerate(group) if i not in ejected_set]

        if not coherent or not output.merged_text.strip():
            return group

        seen: dict[tuple, SourceRef] = {}
        for item in coherent:
            for s in item.sources:
                seen[(s.doc_id, s.collection_name)] = s
        merged = PoolItem(text=output.merged_text, sources=list(seen.values()))
        return [merged] + ejected

    @functools.cached_property
    def _merge_agent(self):
        return get_agent(config_name=self._config_name, output_type=_MergeOutput)

    async def _synthesis_phase(self, pool: list[PoolItem], existing_rubric: Rubric | None) -> Rubric:
        import chromadb

        rubric_name = existing_rubric.name if existing_rubric else "rubric"
        rubric_id = existing_rubric.rubric_id if existing_rubric else str(uuid.uuid4())[:8]
        items: list[RubricItem] = list(existing_rubric.items) if existing_rubric else []

        client = chromadb.EphemeralClient()
        collection = client.create_collection("rubric_synthesis")

        if items:
            embs = await embed_texts([i.requirement_text for i in items], self._embedder)
            collection.add(
                ids=[i.item_id for i in items],
                documents=[i.requirement_text for i in items],
                embeddings=embs,
                metadatas=[{"title": i.title} for i in items],
            )

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
            """Add a new rubric item. Returns the new item_id."""
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
            return item_id

        async def rubric_add_source(item_id: str, doc_id: str, collection_name: str) -> None:
            """Record an additional source reference on an existing rubric item."""
            for item in items:
                if item.item_id == item_id:
                    item.sources.append(SourceRef(doc_id=doc_id, collection_name=collection_name))
                    return

        use_tool = len(items) > _LARGE_RUBRIC_THRESHOLD
        prompt_file = "group_synthesize_with_tool.md" if use_tool else "group_synthesize.md"
        system_prompt = load_prompt(_RUBRIC_PROMPTS / prompt_file)

        batches = [pool[i : i + self._batch_size] for i in range(0, len(pool), self._batch_size)]
        await self._listener.on_pass_start(0, len(pool))

        for batch_num, batch in enumerate(batches, 1):
            if use_tool:
                user_msg = f"## Pool items to process\n\n{_format_pool_items(batch)}"
            else:
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


async def refine_with_history(
    rubric: Rubric,
    history_index,
    config_name: str = "default",
    listener: RubricListener | None = None,
    **builder_kwargs,
) -> Rubric:
    """Extract concerns from historical documents and refine an existing rubric."""
    builder = RubricBuilder(config_name=config_name, listener=listener, **builder_kwargs)
    collection_name = history_index.collection.name
    all_docs = history_index.collection.get(include=["documents", "ids"])
    ids = all_docs.get("ids", [])
    texts = all_docs.get("documents", []) or []

    results = await run_parallel([
        builder._extract_concerns(doc_id, text, collection_name)
        for doc_id, text in zip(ids, texts)
    ])
    pool = [item for chunk_items in results for item in chunk_items]
    return await builder.build(pool, rubric=rubric)
