"""Smart chunker: auto-selects strategy based on content size and structure."""

import re

from agentic_patterns.core.doc_ingestion.models import DocumentProvenance
from agentic_patterns.core.rag.chunker import Chunker
from agentic_patterns.core.rag.chunking import (
    get_stem,
    provenance_to_meta,
    split_paragraphs,
)
from agentic_patterns.core.vectordb.models import Chunk, ChunkLevel


class ChunkerSmart(Chunker):
    """Production default chunker.

    - Short documents (<=max_chunk_chars): single DOCUMENT-level chunk.
    - Markdown with headings: delegates to ChunkerMarkdown.
    - Otherwise: aggregates paragraphs up to max_chunk_chars into SECTION-level chunks.
    """

    def __init__(self, max_chunk_chars: int = 100_000) -> None:
        self._max_chunk_chars = max_chunk_chars

    def chunk(self, text: str, provenance: DocumentProvenance) -> list[Chunk]:
        if len(text) <= self._max_chunk_chars:
            return self._single_document_chunk(text, provenance)

        if re.search(r"^#{1,3}\s+\S", text, re.MULTILINE):
            from agentic_patterns.core.rag.chunker_markdown import ChunkerMarkdown

            return ChunkerMarkdown(max_chunk_size=self._max_chunk_chars).chunk(
                text, provenance
            )

        return self._aggregate_paragraphs(text, provenance)

    def _aggregate_paragraphs(
        self, text: str, provenance: DocumentProvenance
    ) -> list[Chunk]:
        """Merge consecutive paragraphs up to max_chunk_chars into SECTION-level chunks."""
        stem = get_stem(provenance)
        meta = provenance_to_meta(provenance)
        paragraphs = split_paragraphs(text, min_lines=1)

        chunks: list[Chunk] = []
        current_parts: list[str] = []
        current_size = 0

        for para in paragraphs:
            if current_size + len(para) > self._max_chunk_chars and current_parts:
                chunks.append(
                    self._make_section(stem, meta, len(chunks) + 1, current_parts)
                )
                current_parts = []
                current_size = 0
            current_parts.append(para)
            current_size += len(para)

        if current_parts:
            chunks.append(
                self._make_section(stem, meta, len(chunks) + 1, current_parts)
            )

        return chunks

    @staticmethod
    def _make_section(stem: str, meta: dict, idx: int, parts: list[str]) -> Chunk:
        return Chunk(
            doc_id=f"{stem}-sec{idx}",
            text="\n\n".join(parts),
            level=ChunkLevel.SECTION,
            parent_id=None,
            metadata=dict(meta),
        )

    @staticmethod
    def _single_document_chunk(
        text: str, provenance: DocumentProvenance
    ) -> list[Chunk]:
        stem = get_stem(provenance)
        meta = provenance_to_meta(provenance)
        return [
            Chunk(
                doc_id=f"{stem}-doc",
                text=text,
                level=ChunkLevel.DOCUMENT,
                parent_id=None,
                metadata=meta,
            )
        ]
