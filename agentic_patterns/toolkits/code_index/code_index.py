"""CodeIndex -- three-index architecture for semantic code navigation."""

import logging
from pathlib import Path

from agentic_patterns.core.connectors.code_repo.connector import CodeRepoConnector
from agentic_patterns.core.doc_ingestion.models import DocumentProvenance
from agentic_patterns.core.rag.chunker_code import ChunkerCode
from agentic_patterns.core.vectordb.models import Chunk, ChunkLevel
from agentic_patterns.core.vectordb.multi_source import MultiSourceRetriever
from agentic_patterns.core.vectordb.vectordb import VectorDB, get_vector_db
from agentic_patterns.toolkits.code_index.breadcrumbs import build_breadcrumbs
from agentic_patterns.toolkits.code_index.describe import describe_symbols
from agentic_patterns.toolkits.code_index.models import (
    CodeSearchResult,
    IndexListener,
    IndexStats,
)
from agentic_patterns.toolkits.code_index.registry import register, unregister

logger = logging.getLogger(__name__)


class CodeIndex:
    """Indexes and searches a code repository using three parallel vector indexes:
    code (raw source), descriptions (LLM-generated semantics), and breadcrumbs (structural context).
    """

    def __init__(self, repo_path: Path, collection_name: str) -> None:
        self.repo_path = repo_path
        self.collection_name = collection_name
        self._connector = CodeRepoConnector()
        self._chunker = ChunkerCode()
        self._vdb_code = get_vector_db(f"{collection_name}_code")
        self._vdb_descriptions = get_vector_db(f"{collection_name}_descriptions")
        self._vdb_breadcrumbs = get_vector_db(f"{collection_name}_breadcrumbs")
        self._retriever = MultiSourceRetriever(
            code=self._vdb_code,
            descriptions=self._vdb_descriptions,
            breadcrumbs=self._vdb_breadcrumbs,
        )

    def __str__(self) -> str:
        return f"CodeIndex({self.collection_name}, repo={self.repo_path})"

    def expand(self, doc_id: str) -> str:
        """Expand a doc_id into its full context: code, description, breadcrumbs, parent, and siblings."""
        parts: list[str] = []

        code_text, code_meta = _unpack_doc(self._vdb_code, doc_id)
        if code_text is None:
            return f"No document found for doc_id: {doc_id}"

        desc_text, _ = _unpack_doc(self._vdb_descriptions, doc_id)
        bc_text, _ = _unpack_doc(self._vdb_breadcrumbs, doc_id)

        symbol_name = code_meta.get("symbol_name", "")
        symbol_type = code_meta.get("symbol_type", "")
        source = code_meta.get("source", "")

        parts.append(f"## {symbol_type} `{symbol_name}` in {source}")

        if bc_text:
            parts.append(f"**Breadcrumb:** {bc_text}")

        if desc_text:
            parts.append(f"**Description:** {desc_text}")

        parts.append(f"```\n{code_text}\n```")

        # Parent context (class for a method)
        parent_id = code_meta.get("parent_id", "")
        if parent_id:
            parent_code, parent_meta = _unpack_doc(self._vdb_code, parent_id)
            if parent_code is not None:
                parent_name = parent_meta.get("symbol_name", "")
                parts.append(f"\n### Parent: `{parent_name}`")
                parent_desc, _ = _unpack_doc(self._vdb_descriptions, parent_id)
                if parent_desc:
                    parts.append(parent_desc)

        # Siblings (other symbols with the same parent)
        siblings = self._find_siblings(doc_id, parent_id)
        if siblings:
            parts.append("\n### Siblings")
            for sib_name, sib_type in siblings[:10]:
                parts.append(f"- {sib_type} `{sib_name}`")

        return "\n".join(parts)

    async def index(
        self,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
        config_name: str = "default",
        listener: IndexListener | None = None,
    ) -> IndexStats:
        """Index the repository into three parallel collections."""
        stats = IndexStats()
        files = self._connector.scan(self.repo_path, include_patterns, exclude_patterns)
        total = len(files)

        if listener:
            await listener.on_start(total)

        for i, file_path in enumerate(files, 1):
            rel_path = str(file_path.relative_to(self.repo_path))

            if listener:
                await listener.on_file_start(file_path, i, total)

            try:
                content, _ = self._connector.read_file(file_path)
                provenance = DocumentProvenance(
                    original_file=file_path, source=rel_path
                )
                chunks = self._chunker.chunk(content, provenance)

                # Code index -- store raw code for all chunks
                self._vdb_code.ingest(chunks, force=True)

                # Filter to meaningful symbols (skip preamble, file-level, etc.)
                symbol_chunks = [
                    c
                    for c in chunks
                    if c.metadata.get("symbol_name", "")
                    not in ("<preamble>", "<anonymous>", "<export>", "<decorated>")
                    and c.level != ChunkLevel.DOCUMENT
                ]

                # Breadcrumbs -- deterministic, no LLM
                breadcrumbs = build_breadcrumbs(chunks, file_path)
                for doc_id, bc_text in breadcrumbs.items():
                    chunk = self._find_chunk(doc_id, chunks)
                    if chunk:
                        meta = dict(chunk.metadata)
                        meta["level"] = chunk.level.value
                        meta["parent_id"] = chunk.parent_id or ""
                        self._vdb_breadcrumbs.add(
                            bc_text, doc_id, meta=meta, force=True
                        )

                # Descriptions -- LLM-generated
                descriptions = await describe_symbols(symbol_chunks, config_name)
                for doc_id, desc_text in descriptions.items():
                    if not desc_text:
                        continue
                    chunk = self._find_chunk(doc_id, chunks)
                    if chunk:
                        meta = dict(chunk.metadata)
                        meta["level"] = chunk.level.value
                        meta["parent_id"] = chunk.parent_id or ""
                        self._vdb_descriptions.add(
                            desc_text, doc_id, meta=meta, force=True
                        )

                stats.files_indexed += 1
                stats.chunks_created += len(chunks)

                if listener:
                    await listener.on_file_done(file_path, len(chunks), i, total)
            except Exception as e:
                logger.warning("Error indexing %s: %s", file_path, e)
                stats.errors.append(f"{file_path}: {e}")

        if listener:
            await listener.on_done(stats)

        return stats

    def lexical_search(self, pattern: str, max_results: int = 20) -> str:
        """Regex/literal search across source files in the repository."""
        return self._connector.lexical_search(self.repo_path, pattern, max_results)

    async def search(self, query: str, top_k: int = 10) -> list[CodeSearchResult]:
        """Search all three indexes and merge results by doc_id."""
        hits = await self._retriever.retrieve_all(query, max_results=top_k)
        results: list[CodeSearchResult] = []

        for hit in hits[:top_k]:
            doc_id = hit.doc_id

            # Always fetch code from the code index (hit.text may be a description)
            code_text, code_meta = _unpack_doc(self._vdb_code, doc_id)
            if code_text is None:
                code_text = hit.text
                code_meta = hit.metadata

            desc_text, _ = _unpack_doc(self._vdb_descriptions, doc_id)
            bc_text, _ = _unpack_doc(self._vdb_breadcrumbs, doc_id)

            results.append(
                CodeSearchResult(
                    doc_id=doc_id,
                    code=code_text,
                    description=desc_text or "",
                    breadcrumb=bc_text or "",
                    symbol_name=code_meta.get("symbol_name", ""),
                    symbol_type=code_meta.get("symbol_type", ""),
                    file_path=code_meta.get("source", ""),
                    start_line=int(code_meta.get("start_line", 0)),
                    end_line=int(code_meta.get("end_line", 0)),
                    score=hit.score,
                )
            )

        return results

    def _find_chunk(self, doc_id: str, chunks: list[Chunk]) -> Chunk | None:
        for c in chunks:
            if c.doc_id == doc_id:
                return c
        return None

    def _find_siblings(self, doc_id: str, parent_id: str) -> list[tuple[str, str]]:
        """Find (symbol_name, symbol_type) pairs that share the same parent_id."""
        if not parent_id:
            return []
        ids, metadatas = self._vdb_code.get_all_metadatas()
        siblings: list[tuple[str, str]] = []
        for sid, meta in zip(ids, metadatas):
            if sid == doc_id:
                continue
            if meta.get("parent_id") != parent_id:
                continue
            name = meta.get("symbol_name", "")
            if name and name not in ("<preamble>", "<anonymous>"):
                siblings.append((name, meta.get("symbol_type", "")))
        return siblings


def _unpack_doc(vdb: VectorDB, doc_id: str) -> tuple[str | None, dict]:
    """Fetch a document from Chroma and unpack the raw result into (text, metadata).

    Returns (None, {}) if the document does not exist.
    """
    try:
        result = vdb.get_by_id(doc_id)
        ids = result.get("ids", [])
        if not ids:
            return None, {}
        documents = result.get("documents", [])
        metadatas = result.get("metadatas", [])
        text = documents[0] if documents else ""
        meta = metadatas[0] if metadatas else {}
        return text, meta or {}
    except Exception:
        return None, {}
