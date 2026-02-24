"""Retrieval pipeline functions. No LLM calls."""

import chromadb

from agentic_patterns.core.vectordb.models import ChunkLevel, RetrievedDocument
from agentic_patterns.core.vectordb.vectordb import vdb_get_by_id, vdb_query


def retrieve(
    vdb: chromadb.Collection,
    query: str,
    max_results: int = 10,
    filter: dict | None = None,
    level: ChunkLevel | None = None,
) -> list[RetrievedDocument]:
    """Query the vector database with deduplication and optional level filtering.

    level adds a metadata filter to restrict results to a specific chunk granularity.
    """
    effective_filter = dict(filter) if filter else None

    if level is not None:
        level_filter: dict = {"level": {"$eq": level.value}}
        if effective_filter:
            effective_filter = {"$and": [effective_filter, level_filter]}
        else:
            effective_filter = level_filter

    docs = vdb_query(vdb, query, filter=effective_filter, max_items=max_results)

    # Deduplicate by doc_id, keeping highest score
    seen: dict[str, RetrievedDocument] = {}
    for doc in docs:
        if doc.doc_id not in seen or doc.score > seen[doc.doc_id].score:
            seen[doc.doc_id] = doc

    return sorted(seen.values(), key=lambda d: d.score, reverse=True)


def fetch_parent(vdb: chromadb.Collection, doc: RetrievedDocument) -> RetrievedDocument | None:
    """Fetch the parent chunk by following parent_id, enabling context widening."""
    if not doc.parent_id:
        return None

    result = vdb_get_by_id(vdb, doc.parent_id)
    ids = result.get("ids", [])
    if not ids:
        return None

    documents = result.get("documents", [])
    metadatas = result.get("metadatas", [])
    parent_doc = documents[0] if documents else ""
    parent_meta = metadatas[0] if metadatas else {}
    parent_meta = parent_meta or {}

    level_str = parent_meta.get("level", ChunkLevel.PARAGRAPH)
    try:
        level = ChunkLevel(level_str)
    except ValueError:
        level = ChunkLevel.PARAGRAPH

    return RetrievedDocument(
        doc_id=ids[0],
        text=parent_doc,
        score=0.0,
        level=level,
        parent_id=parent_meta.get("parent_id") or None,
        metadata=parent_meta,
    )
