"""High-level API for building rubrics from documents.

RubricSession manages the full lifecycle: chunking, indexing, extraction,
merge, synthesis, and deduplication. Each operation is checkpointed so it
can resume after a crash, and all checkpoint files are preserved as audit logs.

Two workflows:
  - Incremental: add_document() repeatedly. Each call extracts + builds against
    the existing rubric.
  - Batch: extract() many documents, then build() once. On subsequent runs,
    only new extractions are processed.
"""

import hashlib
import tempfile
from pathlib import Path

import chromadb

from agentic_patterns.agents.rubric.builder import (
    RubricBuilder,
    _CheckpointStatus,
    _EXTRACTION_CKPT,
    _ExtractionCheckpoint,
    _read_checkpoint,
)
from agentic_patterns.agents.rubric.listener import RubricListener
from agentic_patterns.agents.rubric.models import PoolItem, Rubric
from agentic_patterns.core.doc_ingestion.models import DocumentProvenance
from agentic_patterns.core.vectordb.chunking import chunk_by_paragraphs
from agentic_patterns.core.vectordb.vectordb import (
    PydanticAIEmbeddingFunction,
    VectorDB,
)


class RubricSession:
    """High-level API for building rubrics from documents.

    Manages chunking, indexing, extraction, and synthesis with scoped
    checkpoints so nothing is ever lost.
    """

    def __init__(
        self,
        name: str,
        rubric_id: str | None = None,
        listener: RubricListener | None = None,
        **builder_kwargs,
    ) -> None:
        self._name = name
        self._rubric_id = rubric_id or hashlib.md5(name.encode()).hexdigest()[:8]
        self._listener = listener or RubricListener()
        self._builder = RubricBuilder(listener=self._listener, **builder_kwargs)
        self._rubric = self._load_latest_rubric()

    @property
    def rubric(self) -> Rubric:
        return self._rubric

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def add_document(self, text: str, source: str) -> Rubric:
        """Extract from one document and incrementally build into rubric."""
        index = self._create_temp_index(text, source)
        return await self.add_index(index)

    async def add_index(self, index: VectorDB) -> Rubric:
        """Incremental build from a pre-built VectorDB index."""
        from agentic_patterns.agents.rubric.builder import _SYNTHESIS_CKPT

        doc_ids = sorted(index.collection.get()["ids"])
        scope = hashlib.md5("|".join(doc_ids).encode()).hexdigest()[:8]
        base = self._builder._get_checkpoint_dir(self._rubric_id)

        extract_dir = base / "extractions" / scope
        extract_dir.mkdir(parents=True, exist_ok=True)
        pool = await self._builder._extract_with_checkpoint(
            index, self._builder._extract_requirements, extract_dir
        )

        incr_dir = base / "incremental" / scope
        incr_dir.mkdir(parents=True, exist_ok=True)
        synthesis_ckpt = incr_dir / _SYNTHESIS_CKPT
        if not synthesis_ckpt.exists():
            pool = await self._builder._merge_phase(pool, incr_dir)
        self._rubric = await self._builder._synthesis_phase(
            pool, self._rubric, incr_dir
        )
        return self._rubric

    async def build(self) -> Rubric:
        """Full rebuild from all completed extractions."""
        base = self._builder._get_checkpoint_dir(self._rubric_id)
        extractions_dir = base / "extractions"
        if not extractions_dir.exists():
            return self._rubric

        pool = self._collect_all_extractions(extractions_dir)
        if not pool:
            return self._rubric

        scopes = sorted(d.name for d in extractions_dir.iterdir() if d.is_dir())
        build_hash = hashlib.md5("|".join(scopes).encode()).hexdigest()[:8]
        build_dir = base / "builds" / build_hash
        build_dir.mkdir(parents=True, exist_ok=True)

        target = Rubric(rubric_id=self._rubric_id, name=self._name)
        self._rubric = await self._builder.build(pool, rubric=target)
        return self._rubric

    async def deduplicate(self) -> Rubric:
        """Merge duplicate items in the current rubric."""
        item_ids = sorted(item.item_id for item in self._rubric.items)
        scope = hashlib.md5("|".join(item_ids).encode()).hexdigest()[:8]
        base = self._builder._get_checkpoint_dir(self._rubric_id)
        dedup_dir = base / "dedup" / scope
        dedup_dir.mkdir(parents=True, exist_ok=True)
        self._rubric = await self._builder.deduplicate(self._rubric, ckpt_dir=dedup_dir)
        return self._rubric

    async def extract(self, text: str, source: str) -> None:
        """Extract requirements from text. Checkpointed, skipped if already done."""
        index = self._create_temp_index(text, source)
        doc_ids = sorted(index.collection.get()["ids"])
        scope = hashlib.md5("|".join(doc_ids).encode()).hexdigest()[:8]
        base = self._builder._get_checkpoint_dir(self._rubric_id)
        extract_dir = base / "extractions" / scope
        extract_dir.mkdir(parents=True, exist_ok=True)
        await self._builder._extract_with_checkpoint(
            index, self._builder._extract_requirements, extract_dir
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _collect_all_extractions(self, extractions_dir: Path) -> list[PoolItem]:
        """Load all completed extraction checkpoints into a single pool."""
        pool: list[PoolItem] = []
        for scope_dir in sorted(extractions_dir.iterdir()):
            if not scope_dir.is_dir():
                continue
            ckpt_path = scope_dir / _EXTRACTION_CKPT
            if not ckpt_path.exists():
                continue
            ckpt = _read_checkpoint(ckpt_path, _ExtractionCheckpoint)
            if ckpt.status != _CheckpointStatus.COMPLETED:
                continue
            for items in ckpt.chunks.values():
                pool.extend(PoolItem.model_validate(d) for d in items)
        return pool

    def _create_temp_index(self, text: str, source: str) -> VectorDB:
        """Chunk text and ingest into a temporary Chroma index."""
        chunks = chunk_by_paragraphs(
            text, DocumentProvenance(source=source), min_lines=1
        )
        tmp_dir = tempfile.mkdtemp(prefix="rubric_idx_")
        client = chromadb.PersistentClient(path=tmp_dir)
        ef = PydanticAIEmbeddingFunction()
        collection = client.get_or_create_collection(
            name=f"rubric_{source}", embedding_function=ef
        )
        index = VectorDB(collection, ef._embedder, client=client, ef=ef)
        index.ingest(chunks)
        return index

    def _load_latest_rubric(self) -> Rubric:
        """Try to load a completed rubric from the latest checkpoint."""
        from agentic_patterns.agents.rubric.builder import (
            _SYNTHESIS_CKPT,
            _SynthesisCheckpoint,
        )
        from agentic_patterns.agents.rubric.models import RubricItem

        base = self._builder._get_checkpoint_dir(self._rubric_id)

        # Search builds/, then incremental/ for the most recent completed synthesis
        for subdir in ("builds", "incremental"):
            parent = base / subdir
            if not parent.exists():
                continue
            for scope_dir in sorted(parent.iterdir(), reverse=True):
                if not scope_dir.is_dir():
                    continue
                ckpt_path = scope_dir / _SYNTHESIS_CKPT
                if not ckpt_path.exists():
                    continue
                ckpt = _read_checkpoint(ckpt_path, _SynthesisCheckpoint)
                if ckpt.status == _CheckpointStatus.COMPLETED and ckpt.items:
                    items = [RubricItem.model_validate(d) for d in ckpt.items]
                    return Rubric(
                        rubric_id=self._rubric_id, name=self._name, items=items
                    )

        return Rubric(rubric_id=self._rubric_id, name=self._name)
