"""Vocabulary agent: PydanticAI agent with vocabulary tools for term resolution."""

from typing import Any

from pydantic_ai import Agent

from agentic_patterns.core.agents.agents import get_agent, run_agent
from agentic_patterns.core.connectors.vocabulary.connector import VocabularyConnector
from agentic_patterns.core.connectors.vocabulary.registry import list_vocabularies


SYSTEM_PROMPT = """You are a vocabulary and ontology expert. You help users resolve terms, \
navigate hierarchies, validate codes, and cross-reference across controlled vocabularies.

You have access to tools for looking up terms, searching, validating codes, browsing \
hierarchies (parents, children, ancestors, descendants), and exploring relationships \
in biomedical and scientific vocabularies."""


def create_vocabulary_agent(vocab_names: list[str] | None = None) -> Agent:
    """Create a vocabulary agent with tools bound to available vocabularies.

    If vocab_names is provided, only those vocabularies are mentioned in instructions.
    Otherwise, all registered vocabularies are listed.
    """
    instructions = _build_instructions(vocab_names)
    tools = _get_tools()
    return get_agent(system_prompt=SYSTEM_PROMPT, instructions=instructions, tools=tools)


async def run_vocabulary_query(query: str, vocab_names: list[str] | None = None, verbose: bool = False) -> tuple[Any, list]:
    """Run a vocabulary query using the vocabulary agent."""
    agent = create_vocabulary_agent(vocab_names)
    return await run_agent(agent, query, verbose=verbose)


def _build_instructions(vocab_names: list[str] | None = None) -> str:
    """Build instructions listing available vocabularies."""
    infos = list_vocabularies()
    if vocab_names:
        infos = [i for i in infos if i.name in vocab_names]
    if not infos:
        return "No vocabularies are currently loaded."
    lines = ["Available vocabularies:"]
    for info in infos:
        lines.append(f"- {info.name}: {info.strategy.value} strategy, {info.term_count} terms ({info.source_format})")
    return "\n".join(lines)


def _get_tools() -> list:
    """Get vocabulary tools as async functions for the agent."""

    async def vocab_lookup(vocab_name: str, term_code: str) -> str:
        """Look up a term by its code/ID in a vocabulary."""
        return VocabularyConnector.lookup(vocab_name, term_code)

    async def vocab_search(vocab_name: str, query: str, max_results: int = 10) -> str:
        """Search for terms matching a text query."""
        return VocabularyConnector.search(vocab_name, query, max_results)

    async def vocab_validate(vocab_name: str, term_code: str) -> str:
        """Validate whether a term code exists. Suggests corrections if invalid."""
        return VocabularyConnector.validate(vocab_name, term_code)

    async def vocab_suggest(vocab_name: str, text: str, max_results: int = 10) -> str:
        """Get semantic suggestions for free text (RAG vocabularies only)."""
        return VocabularyConnector.suggest(vocab_name, text, max_results)

    async def vocab_parent(vocab_name: str, term_code: str) -> str:
        """Get direct parent(s) of a term."""
        return VocabularyConnector.parent(vocab_name, term_code)

    async def vocab_children(vocab_name: str, term_code: str) -> str:
        """Get direct children of a term."""
        return VocabularyConnector.children(vocab_name, term_code)

    async def vocab_ancestors(vocab_name: str, term_code: str, max_depth: int = 10) -> str:
        """Get ancestor chain to root."""
        return VocabularyConnector.ancestors(vocab_name, term_code, max_depth)

    async def vocab_descendants(vocab_name: str, term_code: str, max_depth: int = 10) -> str:
        """Get all descendants up to max_depth."""
        return VocabularyConnector.descendants(vocab_name, term_code, max_depth)

    async def vocab_relationships(vocab_name: str, term_code: str) -> str:
        """Get all typed relationships for a term."""
        return VocabularyConnector.relationships(vocab_name, term_code)

    async def vocab_related(vocab_name: str, term_code: str, relation_type: str) -> str:
        """Get terms connected by a specific relation type."""
        return VocabularyConnector.related(vocab_name, term_code, relation_type)

    async def vocab_info(vocab_name: str) -> str:
        """Get metadata about a vocabulary."""
        return VocabularyConnector.info(vocab_name)

    async def vocab_list() -> str:
        """List all available vocabularies."""
        return VocabularyConnector.list_vocabularies()

    return [
        vocab_lookup, vocab_search, vocab_validate, vocab_suggest,
        vocab_parent, vocab_children, vocab_ancestors, vocab_descendants,
        vocab_relationships, vocab_related, vocab_info, vocab_list,
    ]
