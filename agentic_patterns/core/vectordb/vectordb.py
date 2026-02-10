"""Vector database implementation for embedding storage and similarity search."""

import asyncio
from pathlib import Path

import chromadb
from chromadb.api.types import EmbeddingFunction, Documents, Embeddings

from agentic_patterns.core.vectordb.config import (
    ChromaVectorDBConfig,
    load_vectordb_settings,
)
from agentic_patterns.core.vectordb.embeddings import embed_texts, get_embedder

_vector_dbs: dict[str, chromadb.Collection] = {}
_chroma_clients: dict[str, chromadb.PersistentClient] = {}


class PydanticAIEmbeddingFunction(EmbeddingFunction):
    """Embedding function that wraps pydantic-ai embedder for use with Chroma."""

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


def get_vector_db(
    collection_name: str,
    embedding_config: str | None = None,
    vectordb_config: str | None = None,
    config_path: Path | str | None = None,
) -> chromadb.Collection:
    """Get or create a vector database collection. Uses singleton pattern."""
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

    client = _chroma_clients[persist_key]
    embedding_fn = PydanticAIEmbeddingFunction(embedding_config, config_path)

    collection = client.get_or_create_collection(
        name=collection_name, embedding_function=embedding_fn
    )
    _vector_dbs[collection_name] = collection
    return collection


def vdb_add(
    vdb: chromadb.Collection,
    text: str,
    doc_id: str,
    meta: dict | None = None,
    force: bool = False,
) -> str | None:
    """Add a document to the collection if it doesn't already exist."""
    if not force and vdb_has_id(vdb, doc_id):
        return None
    metadatas = [meta] if meta else None
    vdb.add(documents=[text], ids=[doc_id], metadatas=metadatas)
    return doc_id


def vdb_get_by_id(vdb: chromadb.Collection, doc_id: str) -> dict:
    """Get document by id."""
    return vdb.get(ids=[doc_id])


def vdb_has_id(vdb: chromadb.Collection, doc_id: str) -> bool:
    """Check if a document with a given id exists."""
    result = vdb_get_by_id(vdb, doc_id)
    return len(result["ids"]) > 0


def vdb_query(
    vdb: chromadb.Collection,
    query: str,
    filter: dict[str, str] | None = None,
    where_document: dict[str, str] | None = None,
    max_items: int = 10,
    similarity_threshold: float | None = None,
) -> list[tuple[str, dict, float]]:
    """Query vector database with a given query, return top k results as (document, metadata, score) tuples."""
    results = vdb.query(
        query_texts=[query],
        n_results=max_items,
        where=filter,
        where_document=where_document,
        include=["documents", "metadatas", "distances"],
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    items = []
    for doc, meta, dist in zip(documents, metadatas, distances):
        score = 1.0 - dist  # Convert distance to similarity score
        if similarity_threshold is None or score >= similarity_threshold:
            items.append((doc, meta, score))

    return items
