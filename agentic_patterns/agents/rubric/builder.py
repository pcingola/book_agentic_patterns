"""Rubric build pipeline.

The pipeline has three phases:

  1. Extraction: each document chunk is sent to an LLM to pull out PoolItems
     (structured requirements). Runs in parallel across chunks. Each chunk
     extraction is retried on transient errors. Results are checkpointed
     per-chunk so a crash only loses the in-flight chunk.

  2. Merge passes: while the pool is larger than batch_size, cluster it by
     semantic similarity and run a merge agent on each cluster in parallel.
     The agent ejects outliers back to the pool and merges the coherent core
     into a single PoolItem with unified sources. Repeats until the pool fits
     in one batch or stops shrinking (convergence). Pool state is checkpointed
     after each completed pass.

  3. Synthesis: the reduced pool is processed in sequential batches by an agent
     that has three tools -- find_similar, add_item, add_source -- backed by a
     persistent per-session Chroma VDB in the workspace. Because batches are
     sequential and add_item writes to the VDB immediately, every batch sees
     items committed by previous ones, preventing duplicates across batches.
     The VDB persists across turns so multi-turn agents don't lose state.
     Both the pool and built items are checkpointed after each batch.

Checkpoints are scoped by content hash so different operations never collide.
All checkpoint files are preserved forever as audit logs -- never deleted,
never overwritten by a different operation. Re-running with the same content
resumes from checkpoint.

Checkpoint files are human-readable JSON (indented) for debugging.
"""

import asyncio
import functools
import hashlib
import math
import os
import tempfile
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path, PurePosixPath

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
from agentic_patterns.core.vectordb.embeddings import (
    embed_text,
    embed_texts,
    get_embedder,
)
from agentic_patterns.core.vectordb.models import Chunk, ChunkLevel, ClusterAlgorithm

_RUBRIC_PROMPTS = PROMPTS_DIR / "rubric"

# When the rubric already has more than this many items, the synthesis agent
# uses rubric_find_similar_items to search instead of receiving the full list.
_LARGE_RUBRIC_THRESHOLD = 50

# Exceptions worth retrying (transient network / provider errors).
_retryable: list[type[BaseException]] = [TimeoutError, ConnectionError, OSError]
try:
    from pydantic_ai.exceptions import ModelHTTPError

    _retryable.append(ModelHTTPError)
except ImportError:
    pass
try:
    from botocore.exceptions import ConnectTimeoutError, ReadTimeoutError

    _retryable.extend([ReadTimeoutError, ConnectTimeoutError])
except ImportError:
    pass
_RETRYABLE_EXCEPTIONS: tuple[type[BaseException], ...] = tuple(_retryable)

# Content-filter errors are non-retryable but non-fatal: skip the chunk.
_content_filter_exceptions: list[type[BaseException]] = []
try:
    from pydantic_ai.exceptions import ContentFilterError

    _content_filter_exceptions.append(ContentFilterError)
except ImportError:
    pass
_CONTENT_FILTER_EXCEPTIONS: tuple[type[BaseException], ...] = tuple(
    _content_filter_exceptions
)

_SENTINEL = object()

# Checkpoint file names.
_EXTRACTION_CKPT = "extraction.json"
_MERGE_CKPT = "merge.json"
_SYNTHESIS_CKPT = "synthesis.json"


# ---------------------------------------------------------------------------
# Checkpoint status
# ---------------------------------------------------------------------------


class _CheckpointStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


# ---------------------------------------------------------------------------
# Checkpoint models
# ---------------------------------------------------------------------------


class _ExtractionCheckpoint(BaseModel):
    phase: str = "extraction"
    status: _CheckpointStatus = _CheckpointStatus.IN_PROGRESS
    updated_at: str = ""
    total_chunks: int = 0
    completed_chunks: int = 0
    chunks: dict[str, list[dict]] = Field(default_factory=dict)


class _MergeGroupLog(BaseModel):
    group: int
    input_count: int
    input: list[dict]
    output_count: int
    output: list[dict]


class _MergePassLog(BaseModel):
    pass_num: int = Field(alias="pass")
    updated_at: str = ""
    input_pool_size: int = 0
    output_pool_size: int = 0
    n_groups: int = 0
    groups: list[_MergeGroupLog] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class _MergeCheckpoint(BaseModel):
    phase: str = "merge"
    status: _CheckpointStatus = _CheckpointStatus.IN_PROGRESS
    updated_at: str = ""
    pass_done: int = 0
    pool_size: int = 0
    pool: list[dict] = Field(default_factory=list)
    passes: list[_MergePassLog] = Field(default_factory=list)


class _SynthesisCheckpoint(BaseModel):
    phase: str = "synthesis"
    status: _CheckpointStatus = _CheckpointStatus.IN_PROGRESS
    updated_at: str = ""
    batch_done: int = 0
    total_batches: int = 0
    rubric_items_count: int = 0
    pool_size: int = 0
    pool: list[dict] = Field(default_factory=list)
    items: list[dict] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Atomic JSON writer / reader
# ---------------------------------------------------------------------------


def _write_checkpoint(path: Path, checkpoint: BaseModel) -> None:
    """Write checkpoint atomically: temp file + rename. Pretty-printed for humans."""
    content = checkpoint.model_dump_json(indent=2, by_alias=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    closed = False
    try:
        os.write(fd, content.encode("utf-8"))
        os.fsync(fd)
        os.close(fd)
        closed = True
        Path(tmp).rename(path)
    except BaseException:
        if not closed:
            os.close(fd)
        Path(tmp).unlink(missing_ok=True)
        raise


def _read_checkpoint[T: BaseModel](path: Path, model: type[T]) -> T:
    """Read and validate a checkpoint file."""
    return model.model_validate_json(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Private structured-output models (LLM responses, not part of public API)
# ---------------------------------------------------------------------------


class _MergeOutput(BaseModel):
    """What the merge agent returns for one cluster."""

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


# ---------------------------------------------------------------------------
# Prompt formatting helpers
# ---------------------------------------------------------------------------


def _format_pool_items(items: list[PoolItem]) -> str:
    """Format pool items for inclusion in an agent prompt."""
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


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _rubric_item_to_pool_item(item: RubricItem) -> PoolItem:
    display = f"[{item.requirement_level.value}] {item.title}\n{item.requirement_text}"
    if item.evidence_required:
        display += "\nEvidence required: " + "; ".join(item.evidence_required)
    return PoolItem(
        text=display,
        sources=list(item.sources),
        label=f"[{item.requirement_level.value}] {item.title}",
        requirement_level=item.requirement_level,
        title=item.title,
        requirement_text=item.requirement_text,
        evidence_required=list(item.evidence_required),
    )


# ---------------------------------------------------------------------------
# RubricBuilder
# ---------------------------------------------------------------------------


class RubricBuilder:
    """Builds and refines compliance rubrics from extracted text items.

    Every phase is checkpointed so the process can resume after a crash.
    Transient errors are retried with exponential backoff in all phases.
    Checkpoint files are human-readable JSON with indent=2.
    """

    def __init__(
        self,
        config_name: str = "default",
        batch_size: int = 20,
        max_passes: int = 10,
        algorithm: ClusterAlgorithm = ClusterAlgorithm.AGGLOMERATIVE,
        listener: RubricListener | None = None,
        max_retries: int = 3,
        retry_delay: float = 30.0,
    ) -> None:
        self._config_name = config_name
        self._batch_size = batch_size
        self._max_passes = max_passes
        self._algorithm = algorithm
        self._listener = listener or RubricListener()
        self._embedder = get_embedder()
        self._max_retries = max_retries
        self._retry_delay = retry_delay

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _clean_checkpoints(ckpt_dir: Path) -> None:
        """Remove all checkpoint files, leaving the VDB data intact."""
        for name in (_EXTRACTION_CKPT, _MERGE_CKPT, _SYNTHESIS_CKPT):
            (ckpt_dir / name).unlink(missing_ok=True)

    def _get_checkpoint_dir(self, rubric_id: str) -> Path:
        """Return (and create) the checkpoint directory for a rubric."""
        from agentic_patterns.core.workspace import workspace_to_host_path

        ckpt_dir = workspace_to_host_path(
            PurePosixPath(SANDBOX_PREFIX) / ".rubric_synthesis" / rubric_id
        )
        ckpt_dir.mkdir(parents=True, exist_ok=True)
        return ckpt_dir

    async def _with_retry(
        self,
        coro_factory,
        phase: str,
        detail: str,
        *,
        content_filter_fallback=_SENTINEL,
    ):
        """Run a coroutine with exponential-backoff retry on transient errors.

        If content_filter_fallback is provided, ContentFilterError returns
        that value instead of propagating (the chunk is skipped gracefully).
        """
        for attempt in range(self._max_retries):
            try:
                return await coro_factory()
            except _RETRYABLE_EXCEPTIONS as e:
                if hasattr(e, "status_code") and e.status_code < 500:
                    raise
                if attempt == self._max_retries - 1:
                    raise
                delay = self._retry_delay * (2**attempt)
                await self._listener.on_retry(phase, detail, attempt + 1, delay, e)
                await asyncio.sleep(delay)
            except _CONTENT_FILTER_EXCEPTIONS as e:
                if content_filter_fallback is _SENTINEL:
                    raise
                await self._listener.on_content_filtered(phase, detail, e)
                return content_filter_fallback

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def build(
        self, items: list[PoolItem], rubric: Rubric | None = None
    ) -> Rubric:
        """Phase 2 + 3: merge passes to reduce the pool, then synthesize into a Rubric."""
        if rubric is None:
            rubric = Rubric(name="rubric")
        ckpt_dir = self._get_checkpoint_dir(rubric.rubric_id)
        pool = list(items)

        # If a synthesis checkpoint already exists the pool is saved inside it,
        # so we can skip merge entirely and jump straight to synthesis.
        synthesis_ckpt = ckpt_dir / _SYNTHESIS_CKPT
        if not synthesis_ckpt.exists():
            pool = await self._merge_phase(pool, ckpt_dir)

        # Phase 3: synthesis.
        result = await self._synthesis_phase(pool, rubric, ckpt_dir)

        return result

    async def add_documents(
        self, rubric: Rubric, index, ckpt_dir: Path | None = None
    ) -> Rubric:
        """Extract requirements from index and merge into existing rubric.

        When ckpt_dir is None, checkpoints are scoped by a hash of the index's
        doc IDs under incremental/{content_hash}/.
        """
        if ckpt_dir is None:
            doc_ids = sorted(index.collection.get()["ids"])
            scope = hashlib.md5("|".join(doc_ids).encode()).hexdigest()[:8]
            base = self._get_checkpoint_dir(rubric.rubric_id)
            ckpt_dir = base / "incremental" / scope
            ckpt_dir.mkdir(parents=True, exist_ok=True)
        pool = await self._extract_with_checkpoint(
            index, self._extract_requirements, ckpt_dir
        )
        synthesis_ckpt = ckpt_dir / _SYNTHESIS_CKPT
        if not synthesis_ckpt.exists():
            pool = await self._merge_phase(pool, ckpt_dir)
        return await self._synthesis_phase(pool, rubric, ckpt_dir)

    async def deduplicate(self, rubric: Rubric, ckpt_dir: Path | None = None) -> Rubric:
        """Merge duplicate items in a rubric that has grown large across many documents."""
        if len(rubric.items) <= self._batch_size:
            return rubric
        await self._listener.on_dedup_start(len(rubric.items))
        pool = [_rubric_item_to_pool_item(item) for item in rubric.items]
        if ckpt_dir is None:
            item_ids = sorted(item.item_id for item in rubric.items)
            scope = hashlib.md5("|".join(item_ids).encode()).hexdigest()[:8]
            base = self._get_checkpoint_dir(rubric.rubric_id)
            ckpt_dir = base / "dedup" / scope
            ckpt_dir.mkdir(parents=True, exist_ok=True)
        pool = await self._merge_phase(pool, ckpt_dir)
        target = Rubric(rubric_id=rubric.rubric_id, name=rubric.name)
        result = await self._synthesis_phase(pool, target, ckpt_dir)
        await self._listener.on_dedup_done(len(rubric.items), len(result.items))
        return result

    # ------------------------------------------------------------------
    # Phase 1: extraction
    # ------------------------------------------------------------------

    async def _extract_requirements(
        self, doc_id: str, text: str, collection_name: str
    ) -> list[PoolItem]:
        """LLM call: extract MUST/SHOULD/MAY requirements from one policy chunk."""
        prompt = load_prompt(
            _RUBRIC_PROMPTS / "extract_requirements.md", chunk_text=text
        )
        agent = get_agent(
            config_name=self._config_name, output_type=_ExtractedRequirements
        )
        result = await agent.run(prompt)
        source = SourceRef(
            doc_id=doc_id, collection_name=collection_name, source_text=text
        )
        items = []
        for r in result.output.requirements:
            display = f"[{r.requirement_level.value}] {r.title}\n{r.requirement_text}"
            if r.evidence_required:
                display += "\nEvidence required: " + "; ".join(r.evidence_required)
            items.append(
                PoolItem(
                    text=display,
                    sources=[source],
                    label=f"[{r.requirement_level.value}] {r.title}",
                    requirement_level=r.requirement_level,
                    title=r.title,
                    requirement_text=r.requirement_text,
                    evidence_required=r.evidence_required,
                )
            )
        return items

    async def _extract_with_checkpoint(
        self, index, extractor, ckpt_dir: Path
    ) -> list[PoolItem]:
        """Extract from all chunks with per-chunk checkpointing.

        Each chunk's results are saved to disk as it completes. On restart,
        already-done chunks are skipped.
        """
        ckpt_path = ckpt_dir / _EXTRACTION_CKPT

        collection_name = index.collection.name
        all_docs = index.collection.get(include=["documents"])
        ids: list[str] = all_docs.get("ids", [])
        texts: list[str] = all_docs.get("documents", []) or []

        # Load checkpoint if one exists.
        done: dict[str, list[dict]] = {}
        if ckpt_path.exists():
            ckpt_data = _read_checkpoint(ckpt_path, _ExtractionCheckpoint)
            done = ckpt_data.chunks
            if ckpt_data.status == _CheckpointStatus.COMPLETED:
                pool = [
                    PoolItem.model_validate(d)
                    for doc_id in ids
                    for d in done.get(doc_id, [])
                ]
                await self._listener.on_checkpoint_loaded(
                    "extraction", f"completed, {len(pool)} pool items"
                )
                return pool

        pending = [
            (doc_id, text) for doc_id, text in zip(ids, texts) if doc_id not in done
        ]
        n_total = len(ids)
        n_done = n_total - len(pending)

        if not pending:
            pool = [
                PoolItem.model_validate(d)
                for doc_id in ids
                for d in done.get(doc_id, [])
            ]
            await self._listener.on_checkpoint_loaded(
                "extraction", f"{len(pool)} pool items from {ckpt_path}"
            )
            return pool

        if done:
            await self._listener.on_checkpoint_loaded(
                "extraction",
                f"{n_done}/{n_total} chunks done, {len(pending)} remaining",
            )

        await self._listener.on_pass_start(-1, n_total)

        ckpt_lock = asyncio.Lock()

        async def _tracked(doc_id: str, text: str) -> list[PoolItem]:
            nonlocal n_done
            items = await self._with_retry(
                lambda d=doc_id, t=text: extractor(d, t, collection_name),
                "extraction",
                doc_id,
                content_filter_fallback=[],
            )
            async with ckpt_lock:
                done[doc_id] = [item.model_dump(mode="json") for item in items]
                n_done += 1
                _write_checkpoint(
                    ckpt_path,
                    _ExtractionCheckpoint(
                        updated_at=_now(),
                        total_chunks=n_total,
                        completed_chunks=n_done,
                        chunks=done,
                    ),
                )
            await self._listener.on_group_done(
                -1, n_done, n_total, items=[i.label for i in items]
            )
            return items

        await run_parallel([_tracked(doc_id, text) for doc_id, text in pending])

        _write_checkpoint(
            ckpt_path,
            _ExtractionCheckpoint(
                status=_CheckpointStatus.COMPLETED,
                updated_at=_now(),
                total_chunks=n_total,
                completed_chunks=n_total,
                chunks=done,
            ),
        )

        return [
            PoolItem.model_validate(d) for doc_id in ids for d in done.get(doc_id, [])
        ]

    # ------------------------------------------------------------------
    # Phase 2: merge passes
    # ------------------------------------------------------------------

    async def _merge_phase(
        self, pool: list[PoolItem], ckpt_dir: Path
    ) -> list[PoolItem]:
        """Run merge passes with per-pass checkpointing.

        Everything goes into a single merge.json: the current pool for resume,
        plus a passes[] array with per-group detail for debugging.
        """
        merge_ckpt_path = ckpt_dir / _MERGE_CKPT
        start_pass = 0
        passes_log: list[_MergePassLog] = []

        if merge_ckpt_path.exists():
            ckpt = _read_checkpoint(merge_ckpt_path, _MergeCheckpoint)
            pool = [PoolItem.model_validate(d) for d in ckpt.pool]
            start_pass = ckpt.pass_done
            passes_log = ckpt.passes
            if ckpt.status == _CheckpointStatus.COMPLETED:
                await self._listener.on_checkpoint_loaded(
                    "merge", f"completed, {len(pool)} pool items"
                )
                return pool
            await self._listener.on_checkpoint_loaded(
                "merge",
                f"pass {start_pass}, {len(pool)} pool items from {merge_ckpt_path}",
            )

        def pool_dicts():
            return [item.model_dump(mode="json") for item in pool]

        for pass_num in range(start_pass + 1, self._max_passes + 1):
            if len(pool) <= self._batch_size:
                break
            await self._listener.on_pass_start(pass_num, len(pool))
            new_pool, group_logs = await self._merge_pass(pool, pass_num)
            if len(new_pool) >= len(pool):
                break

            passes_log.append(
                _MergePassLog(
                    **{"pass": pass_num},
                    updated_at=_now(),
                    input_pool_size=len(pool),
                    output_pool_size=len(new_pool),
                    n_groups=len(group_logs),
                    groups=group_logs,
                )
            )
            pool = new_pool

            _write_checkpoint(
                merge_ckpt_path,
                _MergeCheckpoint(
                    updated_at=_now(),
                    pass_done=pass_num,
                    pool_size=len(pool),
                    pool=pool_dicts(),
                    passes=passes_log,
                ),
            )

        _write_checkpoint(
            merge_ckpt_path,
            _MergeCheckpoint(
                status=_CheckpointStatus.COMPLETED,
                updated_at=_now(),
                pass_done=pass_num if passes_log else 0,
                pool_size=len(pool),
                pool=pool_dicts(),
                passes=passes_log,
            ),
        )

        return pool

    def _cluster_pool(self, pool: list[PoolItem]) -> list[list[PoolItem]]:
        """Partition pool into ~batch_size clusters by semantic similarity."""
        n_clusters = max(1, math.ceil(len(pool) / self._batch_size))
        chunks = [
            Chunk(
                doc_id=str(i),
                text=item.text,
                level=ChunkLevel.PARAGRAPH,
                parent_id=None,
                metadata={},
            )
            for i, item in enumerate(pool)
        ]
        result = cluster(
            chunks,
            n_clusters=n_clusters,
            algorithm=self._algorithm,
            embedder=self._embedder,
        )
        return [[pool[int(ci.doc_id)] for ci in c.items] for c in result.clusters]

    @functools.cached_property
    def _merge_agent(self):
        return get_agent(config_name=self._config_name, output_type=_MergeOutput)

    async def _merge_pass(
        self, pool: list[PoolItem], pass_num: int
    ) -> tuple[list[PoolItem], list[_MergeGroupLog]]:
        """Cluster the pool and run the merge agent on each cluster in parallel."""
        groups = self._cluster_pool(pool)
        n_total = len(groups)
        n_done = 0
        group_logs: list[_MergeGroupLog] = []
        log_lock = asyncio.Lock()

        async def _process_group(
            group_items: list[PoolItem], group_num: int
        ) -> list[PoolItem]:
            nonlocal n_done
            await self._listener.on_group_start(pass_num, group_num, n_total)
            merged = await self._run_merge_agent(group_items)
            n_done += 1

            entry = _MergeGroupLog(
                group=group_num,
                input_count=len(group_items),
                input=[{"label": it.label, "text": it.text} for it in group_items],
                output_count=len(merged),
                output=[{"label": it.label, "text": it.text} for it in merged],
            )
            async with log_lock:
                group_logs.append(entry)

            await self._listener.on_group_done(pass_num, n_done, n_total)
            return merged

        results = await run_parallel(
            [_process_group(g, i + 1) for i, g in enumerate(groups)]
        )
        new_pool = [item for sublist in results for item in sublist]

        return new_pool, sorted(group_logs, key=lambda g: g.group)

    async def _run_merge_agent(self, group: list[PoolItem]) -> list[PoolItem]:
        """LLM call: merge a cluster into one PoolItem, eject outliers back to pool."""
        if len(group) == 1:
            return group

        prompt = load_prompt(
            _RUBRIC_PROMPTS / "group_merge.md", items=_format_pool_items(group)
        )
        result = await self._with_retry(
            lambda: self._merge_agent.run(prompt),
            "merge",
            f"{len(group)} items",
            content_filter_fallback=None,
        )
        if result is None:
            return group
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

    # ------------------------------------------------------------------
    # Phase 3: synthesis
    # ------------------------------------------------------------------

    async def _synthesis_phase(
        self, pool: list[PoolItem], rubric: Rubric, ckpt_dir: Path
    ) -> Rubric:
        """Convert pool items into RubricItems via a tool-calling agent."""
        import chromadb

        rubric_name = rubric.name
        rubric_id = rubric.rubric_id

        # items is the live rubric being built -- tools mutate it in place.
        items: list[RubricItem] = list(rubric.items)

        # The VDB lives in the checkpoint directory.
        client = chromadb.PersistentClient(path=str(ckpt_dir))

        # Check for a checkpoint from a previous run.
        checkpoint_path = ckpt_dir / _SYNTHESIS_CKPT
        start_batch = 0
        if checkpoint_path.exists():
            ckpt = _read_checkpoint(checkpoint_path, _SynthesisCheckpoint)
            restored = [RubricItem.model_validate(d) for d in ckpt.items]
            if ckpt.status == _CheckpointStatus.COMPLETED:
                rubric = Rubric(rubric_id=rubric_id, name=rubric_name, items=restored)
                await self._listener.on_checkpoint_loaded(
                    "synthesis", f"completed, {len(restored)} rubric items"
                )
                await self._listener.on_done(rubric)
                return rubric
            if restored:
                items.clear()
                items.extend(restored)
                start_batch = ckpt.batch_done
            if ckpt.pool:
                pool = [PoolItem.model_validate(d) for d in ckpt.pool]
            await self._listener.on_checkpoint_loaded(
                "synthesis",
                f"batch {start_batch}, {len(items)} rubric items from {checkpoint_path}",
            )

        # (Re)create the collection so it's always in sync with `items`.
        try:
            client.delete_collection("rubric_synthesis")
        except Exception:
            pass
        collection = client.create_collection("rubric_synthesis")

        if items:
            embs = await embed_texts(
                [i.requirement_text for i in items], self._embedder
            )
            collection.add(
                ids=[i.item_id for i in items],
                documents=[i.requirement_text for i in items],
                embeddings=embs,
                metadatas=[{"title": i.title} for i in items],
            )

        # Build a lookup for source_text so synthesis tools can preserve it.
        source_text_lookup: dict[tuple[str, str], str] = {}
        for p in pool:
            for s in p.sources:
                key = (s.doc_id, s.collection_name)
                if key not in source_text_lookup and s.source_text:
                    source_text_lookup[key] = s.source_text

        def _resolve_source(doc_id: str, collection_name: str) -> SourceRef:
            return SourceRef(
                doc_id=doc_id,
                collection_name=collection_name,
                source_text=source_text_lookup.get((doc_id, collection_name), ""),
            )

        # ------------------------------------------------------------------
        # Tools -- closures over `items` and `collection`.
        # ------------------------------------------------------------------

        async def rubric_find_similar_items(text: str, top_k: int = 5) -> list[dict]:
            """Semantic search over current rubric items."""
            if not items:
                return []
            emb = await embed_text(text, self._embedder)
            n = min(top_k, len(items))
            res = collection.query(
                query_embeddings=[emb],
                n_results=n,
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
                    res["ids"][0],
                    res["metadatas"][0],
                    res["documents"][0],
                    res["distances"][0],
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
            source_refs = [
                _resolve_source(s["doc_id"], s["collection_name"]) for s in sources
            ]
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

        async def rubric_add_source(
            item_id: str, doc_id: str, collection_name: str
        ) -> None:
            """Record an additional source reference on an existing rubric item."""
            for item in items:
                if item.item_id == item_id:
                    item.sources.append(_resolve_source(doc_id, collection_name))
                    await self._listener.on_source_mapped(item_id, item.title)
                    return

        # ------------------------------------------------------------------
        # Batch loop
        # ------------------------------------------------------------------

        tools = [rubric_find_similar_items, rubric_add_item, rubric_add_source]
        batches = [
            pool[i : i + self._batch_size]
            for i in range(0, len(pool), self._batch_size)
        ]
        n_batches = len(batches)
        await self._listener.on_pass_start(0, len(pool))

        for batch_num, batch in enumerate(batches, 1):
            if batch_num <= start_batch:
                continue

            await self._listener.on_group_start(0, batch_num, n_batches)

            async def _run_batch(b=batch):
                use_tool_search = len(items) > _LARGE_RUBRIC_THRESHOLD
                prompt_file = (
                    "group_synthesize_with_tool.md"
                    if use_tool_search
                    else "group_synthesize.md"
                )
                system_prompt = load_prompt(_RUBRIC_PROMPTS / prompt_file)
                if use_tool_search:
                    user_msg = f"## Pool items to process\n\n{_format_pool_items(b)}"
                else:
                    rubric_section = (
                        f"## Current rubric\n\n{_format_rubric_items(items)}\n\n"
                        if items
                        else ""
                    )
                    user_msg = f"{rubric_section}## Pool items to process\n\n{_format_pool_items(b)}"
                agent = get_agent(
                    config_name=self._config_name,
                    system_prompt=system_prompt,
                    tools=tools,
                )
                await agent.run(user_msg)

            await self._with_retry(_run_batch, "synthesis", f"batch {batch_num}")
            await self._listener.on_group_done(0, batch_num, n_batches)

            pool_dicts = [p.model_dump(mode="json") for p in pool]
            item_dicts = [item.model_dump(mode="json") for item in items]
            _write_checkpoint(
                checkpoint_path,
                _SynthesisCheckpoint(
                    updated_at=_now(),
                    batch_done=batch_num,
                    total_batches=n_batches,
                    rubric_items_count=len(items),
                    pool_size=len(pool),
                    pool=pool_dicts,
                    items=item_dicts,
                ),
            )

        pool_dicts = [p.model_dump(mode="json") for p in pool]
        item_dicts = [item.model_dump(mode="json") for item in items]
        _write_checkpoint(
            checkpoint_path,
            _SynthesisCheckpoint(
                status=_CheckpointStatus.COMPLETED,
                updated_at=_now(),
                batch_done=n_batches,
                total_batches=n_batches,
                rubric_items_count=len(items),
                pool_size=len(pool),
                pool=pool_dicts,
                items=item_dicts,
            ),
        )

        rubric = Rubric(rubric_id=rubric_id, name=rubric_name, items=items)
        await self._listener.on_done(rubric)
        return rubric
