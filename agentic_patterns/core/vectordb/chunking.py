"""Pure-text chunking functions. No LLM calls. All return list[Chunk]."""

import re
from pathlib import Path

from agentic_patterns.core.doc_ingestion.models import DocumentProvenance
from agentic_patterns.core.vectordb.models import Chunk, ChunkLevel


def _get_stem(provenance: DocumentProvenance) -> str:
    if provenance.original_file:
        return provenance.original_file.stem
    if provenance.markdown_file:
        return provenance.markdown_file.stem
    if provenance.source:
        match = re.search(r"\w+", provenance.source)
        return match.group(0) if match else "doc"
    return "doc"


def _provenance_to_meta(provenance: DocumentProvenance) -> dict:
    return {
        "original_file": str(provenance.original_file) if provenance.original_file else "",
        "markdown_file": str(provenance.markdown_file) if provenance.markdown_file else "",
        "source": provenance.source or "",
    }


def _parse_sections(text: str) -> list[tuple[int, str, str]]:
    """Parse markdown into (heading_level, heading_text, body) tuples.

    heading_level=0 means no heading (text before first heading).
    Respects code fences -- headings inside code blocks are ignored.
    """
    lines = text.split("\n")
    sections: list[tuple[int, str, str]] = []
    current_level = 0
    current_heading = ""
    current_body: list[str] = []
    in_code_fence = False
    fence_marker = ""

    for line in lines:
        if not in_code_fence:
            stripped = line.lstrip()
            if stripped.startswith("```") or stripped.startswith("~~~"):
                in_code_fence = True
                fence_marker = stripped[:3]
                current_body.append(line)
                continue
        else:
            if line.lstrip().startswith(fence_marker):
                in_code_fence = False
            current_body.append(line)
            continue

        heading_match = re.match(r"^(#{1,3})\s+(.*)", line)
        if heading_match:
            # Save current section before starting a new one
            body_text = "\n".join(current_body).strip()
            if body_text or current_level > 0:
                sections.append((current_level, current_heading, body_text))
            current_level = len(heading_match.group(1))
            current_heading = heading_match.group(2).strip()
            current_body = []
        else:
            current_body.append(line)

    body_text = "\n".join(current_body).strip()
    if body_text or current_level > 0:
        sections.append((current_level, current_heading, body_text))

    return sections


def _split_paragraphs(text: str, min_lines: int) -> list[str]:
    """Split text at blank lines, keeping only blocks with at least min_lines."""
    blocks = re.split(r"\n{2,}", text)
    return [b.strip() for b in blocks if b.strip() and len(b.strip().splitlines()) >= min_lines]


def chunk_by_paragraphs(text: str, provenance: DocumentProvenance, min_lines: int = 3) -> list[Chunk]:
    """Naive splitter at blank lines. All chunks at PARAGRAPH level with parent_id=None."""
    stem = _get_stem(provenance)
    meta = _provenance_to_meta(provenance)
    paragraphs = _split_paragraphs(text, min_lines)
    return [
        Chunk(doc_id=f"{stem}-p{i + 1}", text=p, level=ChunkLevel.PARAGRAPH, parent_id=None, metadata=dict(meta))
        for i, p in enumerate(paragraphs)
    ]


def chunk_by_markdown(text: str, provenance: DocumentProvenance, max_chunk_size: int = 2000) -> list[Chunk]:
    """Split at heading boundaries with hierarchy tracking.

    Heading mapping: #->DOCUMENT, ##->CHAPTER, ###->SECTION, no heading->PARAGRAPH.
    parent_id links each chunk to its parent heading chunk.
    If a section body exceeds max_chunk_size, paragraph sub-chunks are added under it.
    """
    stem = _get_stem(provenance)
    meta = _provenance_to_meta(provenance)
    sections = _parse_sections(text)

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
            # Text before any heading or between headings
            para_idx += 1
            doc_id = f"{stem}-p{para_idx}"
            chunk_level = ChunkLevel.PARAGRAPH
            parent_id = current_section_id or current_chapter_id or current_doc_id

        full_text = (f"{'#' * level} {heading}\n\n" if level > 0 else "") + body if body else (f"{'#' * level} {heading}" if level > 0 else "")
        if not full_text.strip():
            continue

        chunks.append(Chunk(doc_id=doc_id, text=full_text, level=chunk_level, parent_id=parent_id, metadata=dict(meta)))

        # Add paragraph sub-chunks when body exceeds max_chunk_size
        if len(body) > max_chunk_size:
            sub_paragraphs = re.split(r"\n{2,}", body)
            sub_idx = 0
            for sub in sub_paragraphs:
                sub = sub.strip()
                if not sub:
                    continue
                sub_idx += 1
                sub_id = f"{doc_id}-p{sub_idx}"
                chunks.append(Chunk(doc_id=sub_id, text=sub, level=ChunkLevel.PARAGRAPH, parent_id=doc_id, metadata=dict(meta)))

    return chunks


def chunk(text: str, provenance: DocumentProvenance) -> list[Chunk]:
    """Auto-select chunking strategy.

    Uses chunk_by_markdown if text contains markdown headings, otherwise chunk_by_paragraphs.
    """
    if re.search(r"^#{1,3}\s+\S", text, re.MULTILINE):
        return chunk_by_markdown(text, provenance)
    return chunk_by_paragraphs(text, provenance)
