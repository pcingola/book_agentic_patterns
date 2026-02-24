"""LLM-based semantic chunking."""

import re

from pydantic import BaseModel
from pydantic_ai import Agent

from agentic_patterns.core.agents import get_agent
from agentic_patterns.core.config.config import PROMPTS_DIR
from agentic_patterns.core.doc_ingestion.models import DocumentProvenance
from agentic_patterns.core.prompt import load_prompt
from agentic_patterns.core.vectordb.chunking import _get_stem, _provenance_to_meta
from agentic_patterns.core.vectordb.models import Chunk, ChunkLevel


class _ChunkList(BaseModel):
    chunks: list[str]


def _split_at_paragraphs(text: str, max_size: int) -> list[str]:
    """Split text into batches of at most max_size chars, breaking at paragraph boundaries."""
    paragraphs = re.split(r"\n{2,}", text)
    batches: list[str] = []
    current_parts: list[str] = []
    current_size = 0

    for para in paragraphs:
        if current_size + len(para) > max_size and current_parts:
            batches.append("\n\n".join(current_parts))
            current_parts = []
            current_size = 0
        current_parts.append(para)
        current_size += len(para)

    if current_parts:
        batches.append("\n\n".join(current_parts))

    return batches


async def chunk_with_llm(
    text: str,
    provenance: DocumentProvenance,
    agent: Agent | None = None,
    batch_size: int = 15000,
) -> list[Chunk]:
    """Semantic chunking via LLM. Returns chunks at SECTION level.

    Splits text into batches at paragraph boundaries. The last chunk of each batch
    is prepended to the next batch to preserve continuity across boundaries.
    """
    if agent is None:
        agent = get_agent(output_type=_ChunkList)

    prompt_path = PROMPTS_DIR / "rag" / "chunk_boundaries.md"
    stem = _get_stem(provenance)
    meta = _provenance_to_meta(provenance)

    batches = _split_at_paragraphs(text, batch_size)
    all_texts: list[str] = []
    leftover = ""

    for batch in batches:
        batch_text = (leftover + "\n\n" + batch).strip() if leftover else batch
        prompt = load_prompt(prompt_path, text=batch_text)
        result = await agent.run(prompt)
        chunk_texts: list[str] = result.output.chunks

        if not chunk_texts:
            continue

        # Last chunk might be incomplete -- save as leftover for next batch
        all_texts.extend(chunk_texts[:-1])
        leftover = chunk_texts[-1]

    if leftover:
        all_texts.append(leftover)

    return [
        Chunk(
            doc_id=f"{stem}-llm-sec{i + 1}",
            text=t.strip(),
            level=ChunkLevel.SECTION,
            parent_id=None,
            metadata=dict(meta),
        )
        for i, t in enumerate(all_texts)
        if t.strip()
    ]
