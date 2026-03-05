"""LLM-generated semantic descriptions for code symbols."""

import asyncio
import logging

from agentic_patterns.core.agents import get_agent
from agentic_patterns.core.vectordb.models import Chunk

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You generate concise one-sentence descriptions of what a code symbol does. "
    "Focus on purpose and behavior, not implementation details. "
    "Do not start with 'This function' or 'This class'. "
    "Example: 'Establishes a connection to a remote server with retry logic, "
    "attempting up to MAX_RETRIES times.'"
)

_MAX_CONCURRENT = 10


async def describe_symbol(
    code: str,
    symbol_name: str,
    symbol_type: str,
    file_context: str,
    config_name: str = "default",
    semaphore: asyncio.Semaphore | None = None,
) -> str:
    """Generate a one-sentence semantic description of a code symbol via LLM."""
    agent = get_agent(
        config_name=config_name, system_prompt=_SYSTEM_PROMPT, output_type=str
    )
    prompt = f"{symbol_type} `{symbol_name}` in {file_context}:\n\n```\n{code}\n```"
    if semaphore:
        async with semaphore:
            result = await agent.run(prompt)
    else:
        result = await agent.run(prompt)
    return result.output


async def describe_symbols(
    chunks: list[Chunk], config_name: str = "default"
) -> dict[str, str]:
    """Generate descriptions for multiple chunks concurrently (bounded). Returns doc_id -> description."""
    semaphore = asyncio.Semaphore(_MAX_CONCURRENT)
    tasks = []
    doc_ids = []
    for chunk in chunks:
        name = chunk.metadata.get("symbol_name", "")
        if name in ("<preamble>", "<anonymous>", "<export>", "<decorated>"):
            continue
        stype = chunk.metadata.get("symbol_type", "")
        source = chunk.metadata.get("source", "")
        tasks.append(
            describe_symbol(chunk.text, name, stype, source, config_name, semaphore)
        )
        doc_ids.append(chunk.doc_id)

    results = await asyncio.gather(*tasks, return_exceptions=True)
    descriptions: dict[str, str] = {}
    for doc_id, result in zip(doc_ids, results):
        if isinstance(result, Exception):
            logger.warning("Failed to describe %s: %s", doc_id, result)
            descriptions[doc_id] = ""
        else:
            descriptions[doc_id] = result
    return descriptions
