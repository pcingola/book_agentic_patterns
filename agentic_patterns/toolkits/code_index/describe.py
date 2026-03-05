"""LLM-generated semantic descriptions for code symbols."""

import logging

from pydantic import BaseModel

from agentic_patterns.core.agents import get_agent
from agentic_patterns.core.prompt import get_prompt
from agentic_patterns.core.rag.chunker_code import SymbolType
from agentic_patterns.core.vectordb.models import Chunk

logger = logging.getLogger(__name__)


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

    prompt = get_prompt("code_index/describe_symbols")
    agent = get_agent(
        config_name=config_name,
        system_prompt=prompt,
        output_type=SymbolDescriptions,
    )
    try:
        result = await agent.run("\n".join(parts))
        descriptions: dict[str, str] = {}
        for sd in result.output.symbols:
            key = f"{sd.symbol_type.value}:{sd.symbol_name}"
            doc_id = key_to_doc_id.get(key)
            if doc_id:
                descriptions[doc_id] = sd.description
        return descriptions
    except Exception:
        logger.warning("Failed to describe symbols in %s", source, exc_info=True)
        return {chunk.doc_id: "" for chunk in filtered}


async def summarize_descriptions(
    descriptions: list[str], config_name: str = "default"
) -> str:
    """Produce a short plain-text summary of a code index from its symbol descriptions."""
    if not descriptions:
        return ""
    sample = descriptions[:50]
    prompt = get_prompt("code_index/summarize_index")
    agent = get_agent(config_name=config_name, system_prompt=prompt, output_type=str)
    try:
        result = await agent.run("Symbol descriptions:\n" + "\n".join(f"- {d}" for d in sample))
        return result.output.strip()
    except Exception:
        logger.warning("Failed to summarize index descriptions", exc_info=True)
        return ""
