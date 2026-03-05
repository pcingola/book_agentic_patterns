"""Vector database ABC and factory function."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

from agentic_patterns.core.doc_ingestion.models import DocumentProvenance
from agentic_patterns.core.vectordb.embeddings import embed_texts
from agentic_patterns.core.vectordb.models import Chunk, ChunkLevel, RetrievedDocument

if TYPE_CHECKING:
    from agentic_patterns.core.rag.chunker import Chunker

_vector_dbs: dict[str, "VectorDB"] = {}


class VectorDB(ABC):
    """Abstract base class for vector databases."""

    # ------------------------------------------------------------------
    # Abstract primitives
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def name(self) -> str:
        """Collection / index name."""
        ...

    @abstractmethod
    def add(
        self, text: str, doc_id: str, meta: dict | None = None, force: bool = False
    ) -> str | None:
        """Add a document. Skips if doc_id already exists and force=False."""
        ...

    @abstractmethod
    def add_with_embeddings(
        self,
        texts: list[str],
        ids: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict] | None = None,
    ) -> None:
        """Bulk add with pre-computed embeddings."""
        ...

    @abstractmethod
    def count(self) -> int: ...

    @abstractmethod
    def get_all_documents(self) -> tuple[list[str], list[str]]:
        """Return (ids, texts) for all documents."""
        ...

    @abstractmethod
    def get_all_ids(self) -> list[str]:
        """Return all document IDs in the collection."""
        ...

    @abstractmethod
    def get_all_metadatas(self) -> tuple[list[str], list[dict]]:
        """Return (ids, metadatas) for all documents."""
        ...

    @abstractmethod
    def get_all_with_embeddings(
        self,
    ) -> tuple[list[str], list[str], list[dict], list[list[float]]]:
        """Return (ids, texts, metadatas, embeddings) for all documents."""
        ...

    @abstractmethod
    def get_by_id(self, doc_id: str) -> dict: ...

    @abstractmethod
    def has(self, doc_id: str) -> bool: ...

    @abstractmethod
    def query(
        self,
        query: str,
        filter: dict | None = None,
        where_document: dict | None = None,
        max_items: int = 10,
        similarity_threshold: float | None = None,
    ) -> list[RetrievedDocument]:
        """Raw similarity search."""
        ...

    @abstractmethod
    def query_by_embedding(
        self,
        embedding: list[float],
        filter: dict | None = None,
        max_items: int = 10,
        similarity_threshold: float | None = None,
    ) -> list[RetrievedDocument]:
        """Query using a pre-computed embedding vector."""
        ...

    @abstractmethod
    def reset(self) -> None:
        """Drop and recreate this collection, leaving it empty."""
        ...

    # ------------------------------------------------------------------
    # Concrete methods (shared across backends)
    # ------------------------------------------------------------------

    def retrieve(
        self,
        query: str,
        max_results: int = 10,
        filter: dict | None = None,
        level: ChunkLevel | None = None,
    ) -> list[RetrievedDocument]:
        """Query with deduplication and optional chunk-level filtering."""
        effective_filter = dict(filter) if filter else None
        if level is not None:
            level_filter: dict = {"level": {"$eq": level.value}}
            effective_filter = (
                {"$and": [effective_filter, level_filter]}
                if effective_filter
                else level_filter
            )

        docs = self.query(query, filter=effective_filter, max_items=max_results)

        seen: dict[str, RetrievedDocument] = {}
        for doc in docs:
            if doc.doc_id not in seen or doc.score > seen[doc.doc_id].score:
                seen[doc.doc_id] = doc
        return sorted(seen.values(), key=lambda d: d.score, reverse=True)

    async def aretrieve(
        self,
        query: str,
        max_results: int = 10,
        filter: dict | None = None,
        level: ChunkLevel | None = None,
    ) -> list[RetrievedDocument]:
        """Async retrieve: embeds query, then queries by embedding."""
        embeddings = await embed_texts([query], self._get_embedder())

        effective_filter = dict(filter) if filter else None
        if level is not None:
            level_filter: dict = {"level": {"$eq": level.value}}
            effective_filter = (
                {"$and": [effective_filter, level_filter]}
                if effective_filter
                else level_filter
            )

        docs = self.query_by_embedding(
            embeddings[0],
            filter=effective_filter,
            max_items=max_results,
        )

        seen: dict[str, RetrievedDocument] = {}
        for doc in docs:
            if doc.doc_id not in seen or doc.score > seen[doc.doc_id].score:
                seen[doc.doc_id] = doc
        return sorted(seen.values(), key=lambda d: d.score, reverse=True)

    def fetch_parent(self, doc: RetrievedDocument) -> RetrievedDocument | None:
        """Fetch the parent chunk by following parent_id for context widening."""
        if not doc.parent_id:
            return None
        result = self.get_by_id(doc.parent_id)
        ids = result.get("ids", [])
        if not ids:
            return None
        parent_meta = (result.get("metadatas") or [{}])[0] or {}
        try:
            level = ChunkLevel(parent_meta.get("level", ChunkLevel.PARAGRAPH))
        except ValueError:
            level = ChunkLevel.PARAGRAPH
        return RetrievedDocument(
            doc_id=ids[0],
            text=(result.get("documents") or [""])[0],
            score=0.0,
            level=level,
            parent_id=parent_meta.get("parent_id") or None,
            metadata=parent_meta,
        )

    def ingest(self, chunks: list[Chunk], force: bool = False) -> int:
        """Store chunks in the collection. Returns count of added chunks."""
        added = 0
        for c in chunks:
            meta = dict(c.metadata)
            meta["level"] = c.level.value
            meta["parent_id"] = c.parent_id or ""
            if self.add(c.text, c.doc_id, meta=meta, force=force) is not None:
                added += 1
        return added

    def ingest_file(
        self,
        file: Path,
        provenance: DocumentProvenance,
        chunker: "Chunker | None" = None,
        pipeline: str = "standard",
        force: bool = False,
    ) -> int:
        """Load a file, chunk it, and store in the collection."""
        if chunker is None:
            from agentic_patterns.core.rag.chunker_smart import ChunkerSmart

            chunker = ChunkerSmart()

        suffix = file.suffix.lower()
        if suffix in (".md", ".txt"):
            text = file.read_text(encoding="utf-8")
        else:
            from agentic_patterns.core.doc_ingestion.loader import load_document

            text = load_document(file, provenance, pipeline=pipeline)

        return self.ingest(chunker.chunk(text, provenance), force=force)

    @abstractmethod
    def _get_embedder(self):
        """Return the embedder used by this instance (for aretrieve)."""
        ...


def get_vector_db(
    collection_name: str,
    embedding_config: str | None = None,
    vectordb_config: str | None = None,
    config_path: Path | str | None = None,
) -> VectorDB:
    """Get or create a VectorDB for the named collection. Uses singleton pattern.

    Collections are process-global and shared across all users. Do not mix
    documents with different sensitivity levels in the same collection unless
    retrieval-time access-control filtering is implemented. For user-scoped
    data, include the user_id in the collection name or enforce filtering at
    query time.
    """
    if collection_name in _vector_dbs:
        return _vector_dbs[collection_name]

    from agentic_patterns.core.vectordb.vectordb_chroma import VectorDBChroma

    vdb = VectorDBChroma.create(
        collection_name, embedding_config, vectordb_config, config_path
    )
    _vector_dbs[collection_name] = vdb
    return vdb
