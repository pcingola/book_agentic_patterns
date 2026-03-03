"""Paragraph-based chunker: splits at blank lines."""

from agentic_patterns.core.doc_ingestion.models import DocumentProvenance
from agentic_patterns.core.vectordb.chunker import Chunker
from agentic_patterns.core.vectordb.chunking import (
    get_stem,
    provenance_to_meta,
    split_paragraphs,
)
from agentic_patterns.core.vectordb.models import Chunk, ChunkLevel


class ChunkerParagraph(Chunker):
    def __init__(self, min_lines: int = 3) -> None:
        self._min_lines = min_lines

    def chunk(self, text: str, provenance: DocumentProvenance) -> list[Chunk]:
        stem = get_stem(provenance)
        meta = provenance_to_meta(provenance)
        paragraphs = split_paragraphs(text, self._min_lines)
        return [
            Chunk(
                doc_id=f"{stem}-p{i + 1}",
                text=p,
                level=ChunkLevel.PARAGRAPH,
                parent_id=None,
                metadata=dict(meta),
            )
            for i, p in enumerate(paragraphs)
        ]
