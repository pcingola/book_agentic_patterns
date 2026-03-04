"""Code indexing operations -- scan, chunk, and store code in a vector database."""

from dataclasses import dataclass, field
from pathlib import Path

from agentic_patterns.core.connectors.code_repo.connector import CodeRepoConnector
from agentic_patterns.core.doc_ingestion.models import DocumentProvenance
from agentic_patterns.core.rag.chunker_code import ChunkerCode
from agentic_patterns.core.vectordb.vectordb import get_vector_db


@dataclass
class IndexStats:
    files_indexed: int = 0
    chunks_created: int = 0
    errors: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        msg = f"Indexed {self.files_indexed} files, {self.chunks_created} chunks"
        if self.errors:
            msg += f", {len(self.errors)} errors"
        return msg


def index_repo(
    repo_path: Path,
    collection_name: str,
    include_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
) -> IndexStats:
    """Scan a repository, chunk each file with tree-sitter, store in vector DB."""
    connector = CodeRepoConnector()
    chunker = ChunkerCode()
    vdb = get_vector_db(collection_name)
    stats = IndexStats()

    files = connector.scan(repo_path, include_patterns, exclude_patterns)
    for file_path in files:
        try:
            content, _ = connector.read_file(file_path)
            provenance = DocumentProvenance(
                original_file=file_path, source=str(file_path.relative_to(repo_path))
            )
            chunks = chunker.chunk(content, provenance)
            added = vdb.ingest(chunks, force=True)
            stats.files_indexed += 1
            stats.chunks_created += added
        except Exception as e:
            stats.errors.append(f"{file_path}: {e}")

    return stats


def reindex_files(
    repo_path: Path, collection_name: str, file_paths: list[Path]
) -> IndexStats:
    """Re-index specific files (deletes old chunks by file, re-chunks and stores)."""
    connector = CodeRepoConnector()
    chunker = ChunkerCode()
    vdb = get_vector_db(collection_name)
    stats = IndexStats()

    # Get all existing IDs to find ones matching these files
    existing_ids = vdb.get_all_ids()

    for file_path in file_paths:
        try:
            rel = str(file_path.relative_to(repo_path))
            stem = file_path.stem

            # Delete existing chunks for this file (matching by stem prefix)
            for doc_id in existing_ids:
                if doc_id.startswith(f"{stem}-"):
                    try:
                        vdb.add("", doc_id, force=True)  # overwrite placeholder
                    except Exception:
                        pass

            content, _ = connector.read_file(file_path)
            provenance = DocumentProvenance(original_file=file_path, source=rel)
            chunks = chunker.chunk(content, provenance)
            added = vdb.ingest(chunks, force=True)
            stats.files_indexed += 1
            stats.chunks_created += added
        except Exception as e:
            stats.errors.append(f"{file_path}: {e}")

    return stats
