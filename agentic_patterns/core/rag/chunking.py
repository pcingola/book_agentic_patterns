"""Shared chunking utilities used by chunker classes."""

import re

from agentic_patterns.core.doc_ingestion.models import DocumentProvenance
from agentic_patterns.core.vectordb.models import Chunk


def get_stem(provenance: DocumentProvenance) -> str:
    if provenance.original_file:
        return provenance.original_file.stem
    if provenance.markdown_file:
        return provenance.markdown_file.stem
    if provenance.source:
        match = re.search(r"\w+", provenance.source)
        return match.group(0) if match else "doc"
    return "doc"


def parse_sections(text: str) -> list[tuple[int, str, str]]:
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


def provenance_to_meta(provenance: DocumentProvenance) -> dict:
    return {
        "original_file": str(provenance.original_file)
        if provenance.original_file
        else "",
        "markdown_file": str(provenance.markdown_file)
        if provenance.markdown_file
        else "",
        "source": provenance.source or "",
    }


def split_paragraphs(text: str, min_lines: int) -> list[str]:
    """Split text at blank lines, keeping only blocks with at least min_lines."""
    blocks = re.split(r"\n{2,}", text)
    return [
        b.strip()
        for b in blocks
        if b.strip() and len(b.strip().splitlines()) >= min_lines
    ]


# ---------------------------------------------------------------------------
# Backwards-compatible free functions (delegate to chunker classes)
# ---------------------------------------------------------------------------


def chunk_by_paragraphs(
    text: str, provenance: DocumentProvenance, min_lines: int = 3
) -> list[Chunk]:
    """Naive splitter at blank lines. All chunks at PARAGRAPH level with parent_id=None."""
    from agentic_patterns.core.rag.chunker_paragraph import ChunkerParagraph

    return ChunkerParagraph(min_lines=min_lines).chunk(text, provenance)


def chunk_by_markdown(
    text: str, provenance: DocumentProvenance, max_chunk_size: int = 2000
) -> list[Chunk]:
    """Split at heading boundaries with hierarchy tracking."""
    from agentic_patterns.core.rag.chunker_markdown import ChunkerMarkdown

    return ChunkerMarkdown(max_chunk_size=max_chunk_size).chunk(text, provenance)


def chunk(text: str, provenance: DocumentProvenance) -> list[Chunk]:
    """Auto-select chunking strategy (delegates to ChunkerSmart)."""
    from agentic_patterns.core.rag.chunker_smart import ChunkerSmart

    return ChunkerSmart().chunk(text, provenance)
