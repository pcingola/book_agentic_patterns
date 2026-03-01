"""Vector database: VectorDB class wrapping a Chroma collection."""

from __future__ import annotations

import asyncio
from pathlib import Path

import chromadb
from chromadb.api.types import Documents, Embeddings, EmbeddingFunction
from pydantic_ai import Embedder

from agentic_patterns.core.doc_ingestion.models import DocumentProvenance
from agentic_patterns.core.vectordb.config import (
    ChromaVectorDBConfig,
    load_vectordb_settings,
)
from agentic_patterns.core.vectordb.embeddings import embed_texts, get_embedder
from agentic_patterns.core.vectordb.models import Chunk, ChunkLevel, RetrievedDocument

_vector_dbs: dict[str, "VectorDB"] = {}
_chroma_clients: dict[str, chromadb.PersistentClient] = {}


class PydanticAIEmbeddingFunction(EmbeddingFunction):
    """Wraps a pydantic-ai embedder for use with Chroma."""

    def __init__(
        self, embedding_config: str | None = None, config_path: Path | str | None = None
    ):
        self._embedding_config = embedding_config
        self._config_path = config_path
        self._embedder = get_embedder(embedding_config, config_path)

    @staticmethod
    def name() -> str:
        return "pydantic-ai"

    def get_config(self) -> dict[str, str | None]:
        return {
            "embedding_config": self._embedding_config,
            "config_path": str(self._config_path) if self._config_path else None,
        }

    @staticmethod
    def build_from_config(
        config: dict[str, str | None],
    ) -> "PydanticAIEmbeddingFunction":
        return PydanticAIEmbeddingFunction(
            embedding_config=config.get("embedding_config"),
            config_path=config.get("config_path"),
        )

    def __call__(self, input: Documents) -> Embeddings:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import nest_asyncio

            nest_asyncio.apply()
        return asyncio.get_event_loop().run_until_complete(
            embed_texts(list(input), self._embedder)
        )


class VectorDB:
    """Wraps a Chroma collection with add, query, retrieve, and ingest operations."""

    def __init__(
        self,
        collection: chromadb.Collection,
        embedder: Embedder | None = None,
        client: chromadb.PersistentClient | None = None,
        ef: "PydanticAIEmbeddingFunction | None" = None,
    ) -> None:
        self._collection = collection
        self._embedder = embedder
        self._client = client
        self._ef = ef

    def __str__(self) -> str:
        return f"VectorDB({self._collection.name}, count={self._collection.count()})"

    @property
    def collection(self) -> chromadb.Collection:
        """Direct access to the underlying Chroma collection (escape hatch)."""
        return self._collection

    # ------------------------------------------------------------------
    # Low-level operations
    # ------------------------------------------------------------------

    def add(
        self, text: str, doc_id: str, meta: dict | None = None, force: bool = False
    ) -> str | None:
        """Add a document. Skips if doc_id already exists and force=False."""
        if not force and self.has(doc_id):
            return None
        self._collection.add(
            documents=[text], ids=[doc_id], metadatas=[meta] if meta else None
        )
        return doc_id

    def count(self) -> int:
        return self._collection.count()

    def reset(self) -> None:
        """Drop and recreate this collection, leaving it empty."""
        if self._client is None:
            raise RuntimeError("VectorDB was not created via get_vector_db; cannot reset.")
        name = self._collection.name
        self._client.delete_collection(name)
        self._collection = self._client.get_or_create_collection(name, embedding_function=self._ef)

    def get_by_id(self, doc_id: str) -> dict:
        return self._collection.get(ids=[doc_id])

    def has(self, doc_id: str) -> bool:
        return len(self.get_by_id(doc_id)["ids"]) > 0

    def _parse_chroma_results(
        self, results: dict, similarity_threshold: float | None = None
    ) -> list[RetrievedDocument]:
        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        items = []
        for doc_id, doc, meta, dist in zip(ids, documents, metadatas, distances):
            score = 1.0 - dist
            if similarity_threshold is None or score >= similarity_threshold:
                meta = meta or {}
                try:
                    level = ChunkLevel(meta.get("level", ChunkLevel.PARAGRAPH))
                except ValueError:
                    level = ChunkLevel.PARAGRAPH
                items.append(
                    RetrievedDocument(
                        doc_id=doc_id,
                        text=doc,
                        score=score,
                        level=level,
                        parent_id=meta.get("parent_id") or None,
                        metadata=meta,
                    )
                )
        return items

    def query(
        self,
        query: str,
        filter: dict | None = None,
        where_document: dict | None = None,
        max_items: int = 10,
        similarity_threshold: float | None = None,
    ) -> list[RetrievedDocument]:
        """Raw similarity search. Returns RetrievedDocument list sorted by score."""
        results = self._collection.query(
            query_texts=[query],
            n_results=max_items,
            where=filter,
            where_document=where_document,
            include=["documents", "metadatas", "distances"],
        )
        return self._parse_chroma_results(results, similarity_threshold)

    # ------------------------------------------------------------------
    # Higher-level retrieval
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
        """Async retrieve: embeds query in the current event loop, then queries Chroma synchronously.

        Avoids the event-loop mismatch that occurs when the sync embedding function
        is called from a thread pool (asyncio.to_thread).
        """
        embeddings = await embed_texts([query], self._embedder)

        effective_filter = dict(filter) if filter else None
        if level is not None:
            level_filter: dict = {"level": {"$eq": level.value}}
            effective_filter = (
                {"$and": [effective_filter, level_filter]} if effective_filter else level_filter
            )

        results = self._collection.query(
            query_embeddings=embeddings,
            n_results=max_results,
            where=effective_filter,
            include=["documents", "metadatas", "distances"],
        )
        docs = self._parse_chroma_results(results)

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

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

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
        pipeline: str = "standard",
        force: bool = False,
    ) -> int:
        """Load a file, chunk it, and store in the collection."""
        from agentic_patterns.core.vectordb.chunking import chunk as _chunk

        suffix = file.suffix.lower()
        if suffix in (".md", ".txt"):
            text = file.read_text(encoding="utf-8")
        else:
            from agentic_patterns.core.doc_ingestion.loader import load_document

            text = load_document(file, provenance, pipeline=pipeline)

        return self.ingest(_chunk(text, provenance), force=force)


def get_vector_db(
    collection_name: str,
    embedding_config: str | None = None,
    vectordb_config: str | None = None,
    config_path: Path | str | None = None,
) -> VectorDB:
    """Get or create a VectorDB for the named collection. Uses singleton pattern."""
    if collection_name in _vector_dbs:
        return _vector_dbs[collection_name]

    if config_path is None:
        from agentic_patterns.core.config.config import MAIN_PROJECT_DIR

        config_path = MAIN_PROJECT_DIR / "config.yaml"

    settings = load_vectordb_settings(config_path)
    vdb_config = settings.get_vectordb(vectordb_config or "default")

    if not isinstance(vdb_config, ChromaVectorDBConfig):
        raise ValueError(f"Only Chroma backend is supported, got: {type(vdb_config)}")

    persist_dir = Path(vdb_config.persist_directory)
    if not persist_dir.is_absolute():
        from agentic_patterns.core.config.config import MAIN_PROJECT_DIR

        persist_dir = MAIN_PROJECT_DIR / persist_dir
    persist_dir.mkdir(parents=True, exist_ok=True)

    persist_key = str(persist_dir)
    if persist_key not in _chroma_clients:
        _chroma_clients[persist_key] = chromadb.PersistentClient(path=str(persist_dir))

    ef = PydanticAIEmbeddingFunction(embedding_config, config_path)
    collection = _chroma_clients[persist_key].get_or_create_collection(
        name=collection_name,
        embedding_function=ef,
    )
    vdb = VectorDB(collection, ef._embedder, client=_chroma_clients[persist_key], ef=ef)
    _vector_dbs[collection_name] = vdb
    return vdb
