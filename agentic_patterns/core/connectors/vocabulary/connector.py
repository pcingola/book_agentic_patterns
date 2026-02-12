"""VocabularyConnector: vocabulary and ontology operations."""

from pydantic_ai import ModelRetry

from agentic_patterns.core.connectors.base import Connector
from agentic_patterns.core.connectors.vocabulary.models import VocabularyTerm
from agentic_patterns.core.connectors.vocabulary.registry import (
    get_vocabulary,
    list_vocabularies as _list_vocabularies,
)
from agentic_patterns.core.context.decorators import context_result
from agentic_patterns.core.tools.permissions import ToolPermission, tool_permission


def _format_terms(terms: list[VocabularyTerm]) -> str:
    if not terms:
        return "No results."
    return "\n---\n".join(str(t) for t in terms)


def _format_relationships(rels: dict[str, list[str]]) -> str:
    if not rels:
        return "No relationships."
    return "\n".join(f"{rel_type}: {', '.join(ids)}" for rel_type, ids in rels.items())


class VocabularyConnector(Connector):
    """Vocabulary operations. String returns for agent consumption."""

    @tool_permission(ToolPermission.READ)
    def ancestors(self, vocab_name: str, term_code: str, max_depth: int = 10) -> str:
        """Get ancestor chain to root."""
        try:
            backend = get_vocabulary(vocab_name)
            return _format_terms(backend.ancestors(term_code, max_depth))
        except (KeyError, ValueError) as e:
            raise ModelRetry(str(e)) from e

    @tool_permission(ToolPermission.READ)
    @context_result()
    def children(self, vocab_name: str, term_code: str) -> str:
        """Get direct children of a term."""
        try:
            backend = get_vocabulary(vocab_name)
            return _format_terms(backend.children(term_code))
        except (KeyError, ValueError) as e:
            raise ModelRetry(str(e)) from e

    @tool_permission(ToolPermission.READ)
    @context_result()
    def descendants(self, vocab_name: str, term_code: str, max_depth: int = 10) -> str:
        """Get all descendants (subtree)."""
        try:
            backend = get_vocabulary(vocab_name)
            return _format_terms(backend.descendants(term_code, max_depth))
        except (KeyError, ValueError) as e:
            raise ModelRetry(str(e)) from e

    @tool_permission(ToolPermission.READ)
    def info(self, vocab_name: str) -> str:
        """Get vocabulary metadata."""
        try:
            backend = get_vocabulary(vocab_name)
            return str(backend.info())
        except (KeyError, ValueError) as e:
            raise ModelRetry(str(e)) from e

    @tool_permission(ToolPermission.READ)
    def list_vocabularies(self) -> str:
        """List all available vocabularies."""
        infos = _list_vocabularies()
        if not infos:
            return "No vocabularies registered."
        return "\n".join(str(i) for i in infos)

    @tool_permission(ToolPermission.READ)
    def lookup(self, vocab_name: str, term_code: str) -> str:
        """Look up a term by its code/ID."""
        try:
            backend = get_vocabulary(vocab_name)
            term = backend.lookup(term_code)
            return (
                str(term) if term else f"Term '{term_code}' not found in {vocab_name}."
            )
        except (KeyError, ValueError) as e:
            raise ModelRetry(str(e)) from e

    @tool_permission(ToolPermission.READ)
    def parent(self, vocab_name: str, term_code: str) -> str:
        """Get direct parent(s) of a term."""
        try:
            backend = get_vocabulary(vocab_name)
            return _format_terms(backend.parent(term_code))
        except (KeyError, ValueError) as e:
            raise ModelRetry(str(e)) from e

    @tool_permission(ToolPermission.READ)
    def related(self, vocab_name: str, term_code: str, relation_type: str) -> str:
        """Get terms connected by a specific relation type."""
        try:
            backend = get_vocabulary(vocab_name)
            return _format_terms(backend.related(term_code, relation_type))
        except (KeyError, ValueError) as e:
            raise ModelRetry(str(e)) from e

    @tool_permission(ToolPermission.READ)
    def relationships(self, vocab_name: str, term_code: str) -> str:
        """Get all typed relationships for a term."""
        try:
            backend = get_vocabulary(vocab_name)
            return _format_relationships(backend.relationships(term_code))
        except (KeyError, ValueError) as e:
            raise ModelRetry(str(e)) from e

    @tool_permission(ToolPermission.READ)
    @context_result()
    def roots(self, vocab_name: str) -> str:
        """Get top-level terms."""
        try:
            backend = get_vocabulary(vocab_name)
            return _format_terms(backend.roots())
        except (KeyError, ValueError) as e:
            raise ModelRetry(str(e)) from e

    @tool_permission(ToolPermission.READ)
    @context_result()
    def search(self, vocab_name: str, query: str, max_results: int = 10) -> str:
        """Search for terms matching a query."""
        try:
            backend = get_vocabulary(vocab_name)
            return _format_terms(backend.search(query, max_results))
        except (KeyError, ValueError) as e:
            raise ModelRetry(str(e)) from e

    @tool_permission(ToolPermission.READ)
    @context_result()
    def siblings(self, vocab_name: str, term_code: str) -> str:
        """Get terms sharing the same parent."""
        try:
            backend = get_vocabulary(vocab_name)
            return _format_terms(backend.siblings(term_code))
        except (KeyError, ValueError) as e:
            raise ModelRetry(str(e)) from e

    @tool_permission(ToolPermission.READ)
    @context_result()
    def subtree(self, vocab_name: str, term_code: str, max_depth: int = 3) -> str:
        """Get hierarchical view for browsing."""
        try:
            backend = get_vocabulary(vocab_name)
            return _format_terms(backend.subtree(term_code, max_depth))
        except (KeyError, ValueError) as e:
            raise ModelRetry(str(e)) from e

    @tool_permission(ToolPermission.READ)
    def suggest(self, vocab_name: str, text: str, max_results: int = 10) -> str:
        """Semantic suggestions (RAG strategy only)."""
        try:
            backend = get_vocabulary(vocab_name)
            if not hasattr(backend, "suggest"):
                raise ModelRetry(
                    "suggest is only available for RAG-backed vocabularies. Use search instead."
                )
            return _format_terms(backend.suggest(text, max_results))
        except (KeyError, ValueError) as e:
            raise ModelRetry(str(e)) from e

    @tool_permission(ToolPermission.READ)
    def validate(self, vocab_name: str, term_code: str) -> str:
        """Validate a term code. Returns validity and suggestion if invalid."""
        try:
            backend = get_vocabulary(vocab_name)
            is_valid, suggestion = backend.validate(term_code)
            if is_valid:
                return f"Valid: {term_code}"
            msg = f"Invalid: {term_code}"
            if suggestion:
                msg += f" (did you mean '{suggestion}'?)"
            return msg
        except (KeyError, ValueError) as e:
            raise ModelRetry(str(e)) from e
