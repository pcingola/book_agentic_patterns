"""LLM-generated semantic descriptions for code symbols."""

import logging

from pydantic import BaseModel

from agentic_patterns.core.agents import get_agent
from agentic_patterns.core.rag.chunker_code import SymbolType
from agentic_patterns.core.vectordb.models import Chunk

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You generate concise one-sentence descriptions of code symbols. "
    "Focus on purpose and behavior, not implementation details. "
    "Do not start with 'This function' or 'This class'.\n\n"
    "You receive multiple symbols from the same file. "
    "Return a description for each one, preserving the exact symbol_name and symbol_type."
)


class SymbolDescription(BaseModel):
    symbol_name: str
    symbol_type: SymbolType
    description: str


class SymbolDescriptions(BaseModel):
    symbols: list[SymbolDescription]


async def describe_symbols(
    chunks: list[Chunk], config_name: str = "default"
) -> dict[str, str]:
    """Describe all symbols from a file in a single LLM call. Returns doc_id -> description."""
    filtered: list[Chunk] = [
        c
        for c in chunks
        if c.metadata.get("symbol_name", "")
        not in ("<preamble>", "<anonymous>", "<export>", "<decorated>")
    ]
    if not filtered:
        return {}

    # Build a single prompt with all symbols
    source = filtered[0].metadata.get("source", "")
    parts = [f"File: {source}\n"]
    key_to_doc_id: dict[str, str] = {}
    for chunk in filtered:
        name = chunk.metadata.get("symbol_name", "")
        stype = chunk.metadata.get("symbol_type", "")
        parts.append(f"### {stype} `{name}`\n```\n{chunk.text}\n```\n")
        key_to_doc_id[f"{stype}:{name}"] = chunk.doc_id

    agent = get_agent(
        config_name=config_name,
        system_prompt=_SYSTEM_PROMPT,
        output_type=SymbolDescriptions,
    )
    try:
        result = await agent.run("\n".join(parts))
        descriptions: dict[str, str] = {}
        for sd in result.output.symbols:
            key = f"{sd.symbol_type}:{sd.symbol_name}"
            doc_id = key_to_doc_id.get(key)
            if doc_id:
                descriptions[doc_id] = sd.description
        return descriptions
    except Exception:
        logger.warning("Failed to describe symbols in %s", source, exc_info=True)
        return {chunk.doc_id: "" for chunk in filtered}
