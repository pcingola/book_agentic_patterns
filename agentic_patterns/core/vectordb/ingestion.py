"""Compose loading, chunking, and storing into the vector database."""

from pathlib import Path

import chromadb

from agentic_patterns.core.doc_ingestion.models import DocumentProvenance
from agentic_patterns.core.vectordb.chunking import chunk
from agentic_patterns.core.vectordb.models import Chunk
from agentic_patterns.core.vectordb.vectordb import vdb_add


def _chunk_meta(c: Chunk) -> dict:
    """Build flat Chroma-compatible metadata from a Chunk."""
    meta = dict(c.metadata)
    meta["level"] = c.level.value
    meta["parent_id"] = c.parent_id or ""
    return meta


def ingest(vdb: chromadb.Collection, chunks: list[Chunk], force: bool = False) -> int:
    """Store chunks in the vector database. Returns count of added chunks."""
    added = 0
    for c in chunks:
        result = vdb_add(vdb, c.text, c.doc_id, meta=_chunk_meta(c), force=force)
        if result is not None:
            added += 1
    return added


def ingest_file(
    vdb: chromadb.Collection,
    file: Path,
    provenance: DocumentProvenance,
    pipeline: str = "standard",
    force: bool = False,
) -> int:
    """Load a file, chunk it, and store in the vector database. Returns count of added chunks."""
    if file.suffix.lower() == ".md":
        from agentic_patterns.core.doc_ingestion.loader import load_markdown
        text = load_markdown(file, provenance)
    else:
        from agentic_patterns.core.doc_ingestion.loader import load_document
        text = load_document(file, provenance, pipeline=pipeline)

    chunks = chunk(text, provenance)
    return ingest(vdb, chunks, force=force)
