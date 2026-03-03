"""Chroma-backed VectorDB implementation."""

from __future__ import annotations

import asyncio
from pathlib import Path

import chromadb
from chromadb.api.types import Documents, Embeddings, EmbeddingFunction
from pydantic_ai import Embedder

from agentic_patterns.core.vectordb.config import (
    ChromaVectorDBConfig,
    load_vectordb_settings,
)
from agentic_patterns.core.vectordb.embeddings import embed_texts, get_embedder
from agentic_patterns.core.vectordb.models import ChunkLevel, RetrievedDocument
from agentic_patterns.core.vectordb.vectordb import VectorDB

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
    def build_from_config(config: dict[str, str | None]) -> PydanticAIEmbeddingFunction:
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


class VectorDBChroma(VectorDB):
    """Chroma-backed VectorDB implementation."""

    def __init__(
        self,
        collection: chromadb.Collection,
        embedder: Embedder | None = None,
        client: chromadb.PersistentClient | None = None,
        ef: PydanticAIEmbeddingFunction | None = None,
    ) -> None:
        self._collection = collection
        self._embedder = embedder
        self._client = client
        self._ef = ef

    def __str__(self) -> str:
        return (
            f"VectorDBChroma({self._collection.name}, count={self._collection.count()})"
        )

    # ------------------------------------------------------------------
    # Abstract implementations
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return self._collection.name

    def add(
        self, text: str, doc_id: str, meta: dict | None = None, force: bool = False
    ) -> str | None:
        if not force and self.has(doc_id):
            return None
        self._collection.add(
            documents=[text], ids=[doc_id], metadatas=[meta] if meta else None
        )
        return doc_id

    def add_with_embeddings(
        self,
        texts: list[str],
        ids: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict] | None = None,
    ) -> None:
        self._collection.add(
            ids=ids, documents=texts, embeddings=embeddings, metadatas=metadatas
        )

    def count(self) -> int:
        return self._collection.count()

    def get_all_documents(self) -> tuple[list[str], list[str]]:
        result = self._collection.get(include=["documents"])
        ids = result.get("ids", [])
        texts = result.get("documents", []) or [""] * len(ids)
        return ids, texts

    def get_all_ids(self) -> list[str]:
        return self._collection.get()["ids"]

    def get_all_metadatas(self) -> tuple[list[str], list[dict]]:
        result = self._collection.get(include=["metadatas"])
        ids = result.get("ids", [])
        metadatas = result.get("metadatas", []) or [{}] * len(ids)
        return ids, metadatas

    def get_all_with_embeddings(
        self,
    ) -> tuple[list[str], list[str], list[dict], list[list[float]]]:
        result = self._collection.get(include=["embeddings", "documents", "metadatas"])
        ids = result.get("ids", [])
        texts = result.get("documents", []) or [""] * len(ids)
        metadatas = result.get("metadatas", []) or [{}] * len(ids)
        embeddings = result.get("embeddings", [])
        return ids, texts, metadatas, embeddings

    def get_by_id(self, doc_id: str) -> dict:
        return self._collection.get(ids=[doc_id])

    def has(self, doc_id: str) -> bool:
        return len(self.get_by_id(doc_id)["ids"]) > 0

    def query(
        self,
        query: str,
        filter: dict | None = None,
        where_document: dict | None = None,
        max_items: int = 10,
        similarity_threshold: float | None = None,
    ) -> list[RetrievedDocument]:
        results = self._collection.query(
            query_texts=[query],
            n_results=max_items,
            where=filter,
            where_document=where_document,
            include=["documents", "metadatas", "distances"],
        )
        return self._parse_chroma_results(results, similarity_threshold)

    def query_by_embedding(
        self,
        embedding: list[float],
        filter: dict | None = None,
        max_items: int = 10,
        similarity_threshold: float | None = None,
    ) -> list[RetrievedDocument]:
        results = self._collection.query(
            query_embeddings=[embedding],
            n_results=max_items,
            where=filter,
            include=["documents", "metadatas", "distances"],
        )
        return self._parse_chroma_results(results, similarity_threshold)

    def reset(self) -> None:
        if self._client is None:
            raise RuntimeError(
                "VectorDBChroma was not created via get_vector_db; cannot reset."
            )
        name = self._collection.name
        self._client.delete_collection(name)
        self._collection = self._client.get_or_create_collection(
            name, embedding_function=self._ef
        )

    def _get_embedder(self):
        return self._embedder

    # ------------------------------------------------------------------
    # Chroma-specific helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_chroma_results(
        results: dict, similarity_threshold: float | None = None
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

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @staticmethod
    def create(
        collection_name: str,
        embedding_config: str | None = None,
        vectordb_config: str | None = None,
        config_path: Path | str | None = None,
    ) -> VectorDBChroma:
        """Create a VectorDBChroma from configuration."""
        if config_path is None:
            from agentic_patterns.core.config.config import MAIN_PROJECT_DIR

            config_path = MAIN_PROJECT_DIR / "config.yaml"

        settings = load_vectordb_settings(config_path)
        vdb_config = settings.get_vectordb(vectordb_config or "default")

        if not isinstance(vdb_config, ChromaVectorDBConfig):
            raise ValueError(
                f"Only Chroma backend is supported, got: {type(vdb_config)}"
            )

        persist_dir = Path(vdb_config.persist_directory)
        if not persist_dir.is_absolute():
            from agentic_patterns.core.config.config import MAIN_PROJECT_DIR

            persist_dir = MAIN_PROJECT_DIR / persist_dir

        persist_dir.mkdir(parents=True, exist_ok=True)

        persist_key = str(persist_dir)
        if persist_key not in _chroma_clients:
            _chroma_clients[persist_key] = chromadb.PersistentClient(
                path=str(persist_dir)
            )

        ef = PydanticAIEmbeddingFunction(embedding_config, config_path)
        collection = _chroma_clients[persist_key].get_or_create_collection(
            name=collection_name, embedding_function=ef
        )
        return VectorDBChroma(
            collection, ef._embedder, client=_chroma_clients[persist_key], ef=ef
        )
