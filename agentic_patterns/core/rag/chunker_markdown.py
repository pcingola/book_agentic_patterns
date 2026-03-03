"""Markdown-aware chunker: splits at heading boundaries with hierarchy tracking."""

import re

from agentic_patterns.core.doc_ingestion.models import DocumentProvenance
from agentic_patterns.core.rag.chunker import Chunker
from agentic_patterns.core.rag.chunking import (
    get_stem,
    parse_sections,
    provenance_to_meta,
)
from agentic_patterns.core.vectordb.models import Chunk, ChunkLevel


class ChunkerMarkdown(Chunker):
    def __init__(self, max_chunk_size: int = 2000) -> None:
        self._max_chunk_size = max_chunk_size

    def chunk(self, text: str, provenance: DocumentProvenance) -> list[Chunk]:
        stem = get_stem(provenance)
        meta = provenance_to_meta(provenance)
        sections = parse_sections(text)

        chunks: list[Chunk] = []
        chapter_idx = 0
        section_idx = 0
        para_idx = 0
        current_doc_id: str | None = None
        current_chapter_id: str | None = None
        current_section_id: str | None = None

        for level, heading, body in sections:
            if level == 1:
                chapter_idx = 0
                section_idx = 0
                para_idx = 0
                doc_id = f"{stem}-doc"
                current_doc_id = doc_id
                current_chapter_id = None
                current_section_id = None
                chunk_level = ChunkLevel.DOCUMENT
                parent_id = None
            elif level == 2:
                chapter_idx += 1
                section_idx = 0
                para_idx = 0
                doc_id = f"{stem}-ch{chapter_idx}"
                current_chapter_id = doc_id
                current_section_id = None
                chunk_level = ChunkLevel.CHAPTER
                parent_id = current_doc_id
            elif level == 3:
                section_idx += 1
                para_idx = 0
                doc_id = f"{stem}-ch{chapter_idx}-sec{section_idx}"
                current_section_id = doc_id
                chunk_level = ChunkLevel.SECTION
                parent_id = current_chapter_id or current_doc_id
            else:
                para_idx += 1
                doc_id = f"{stem}-p{para_idx}"
                chunk_level = ChunkLevel.PARAGRAPH
                parent_id = current_section_id or current_chapter_id or current_doc_id

            full_text = (
                (f"{'#' * level} {heading}\n\n" if level > 0 else "") + body
                if body
                else (f"{'#' * level} {heading}" if level > 0 else "")
            )
            if not full_text.strip():
                continue

            chunks.append(
                Chunk(
                    doc_id=doc_id,
                    text=full_text,
                    level=chunk_level,
                    parent_id=parent_id,
                    metadata=dict(meta),
                )
            )

            if len(body) > self._max_chunk_size:
                sub_paragraphs = re.split(r"\n{2,}", body)
                sub_idx = 0
                for sub in sub_paragraphs:
                    sub = sub.strip()
                    if not sub:
                        continue
                    sub_idx += 1
                    sub_id = f"{doc_id}-p{sub_idx}"
                    chunks.append(
                        Chunk(
                            doc_id=sub_id,
                            text=sub,
                            level=ChunkLevel.PARAGRAPH,
                            parent_id=doc_id,
                            metadata=dict(meta),
                        )
                    )

        return chunks
