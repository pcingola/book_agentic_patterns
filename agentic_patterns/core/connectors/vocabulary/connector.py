"""VocabularyConnector: vocabulary and ontology operations."""

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
        backend = get_vocabulary(vocab_name)
        return _format_terms(backend.ancestors(term_code, max_depth))

    @tool_permission(ToolPermission.READ)
    @context_result()
    def children(self, vocab_name: str, term_code: str) -> str:
        """Get direct children of a term."""
        backend = get_vocabulary(vocab_name)
        return _format_terms(backend.children(term_code))

    @tool_permission(ToolPermission.READ)
    @context_result()
    def descendants(self, vocab_name: str, term_code: str, max_depth: int = 10) -> str:
        """Get all descendants (subtree)."""
        backend = get_vocabulary(vocab_name)
        return _format_terms(backend.descendants(term_code, max_depth))

    @tool_permission(ToolPermission.READ)
    def info(self, vocab_name: str) -> str:
        """Get vocabulary metadata."""
        backend = get_vocabulary(vocab_name)
        return str(backend.info())

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
        backend = get_vocabulary(vocab_name)
        term = backend.lookup(term_code)
        return str(term) if term else f"Term '{term_code}' not found in {vocab_name}."

    @tool_permission(ToolPermission.READ)
    def parent(self, vocab_name: str, term_code: str) -> str:
        """Get direct parent(s) of a term."""
        backend = get_vocabulary(vocab_name)
        return _format_terms(backend.parent(term_code))

    @tool_permission(ToolPermission.READ)
    def related(self, vocab_name: str, term_code: str, relation_type: str) -> str:
        """Get terms connected by a specific relation type."""
        backend = get_vocabulary(vocab_name)
        return _format_terms(backend.related(term_code, relation_type))

    @tool_permission(ToolPermission.READ)
    def relationships(self, vocab_name: str, term_code: str) -> str:
        """Get all typed relationships for a term."""
        backend = get_vocabulary(vocab_name)
        return _format_relationships(backend.relationships(term_code))

    @tool_permission(ToolPermission.READ)
    @context_result()
    def roots(self, vocab_name: str) -> str:
        """Get top-level terms."""
        backend = get_vocabulary(vocab_name)
        return _format_terms(backend.roots())

    @tool_permission(ToolPermission.READ)
    @context_result()
    def search(self, vocab_name: str, query: str, max_results: int = 10) -> str:
        """Search for terms matching a query."""
        backend = get_vocabulary(vocab_name)
        return _format_terms(backend.search(query, max_results))

    @tool_permission(ToolPermission.READ)
    @context_result()
    def siblings(self, vocab_name: str, term_code: str) -> str:
        """Get terms sharing the same parent."""
        backend = get_vocabulary(vocab_name)
        return _format_terms(backend.siblings(term_code))

    @tool_permission(ToolPermission.READ)
    @context_result()
    def subtree(self, vocab_name: str, term_code: str, max_depth: int = 3) -> str:
        """Get hierarchical view for browsing."""
        backend = get_vocabulary(vocab_name)
        return _format_terms(backend.subtree(term_code, max_depth))

    @tool_permission(ToolPermission.READ)
    def suggest(self, vocab_name: str, text: str, max_results: int = 10) -> str:
        """Semantic suggestions (RAG strategy only)."""
        backend = get_vocabulary(vocab_name)
        if not hasattr(backend, "suggest"):
            raise ValueError("suggest is only available for RAG-backed vocabularies.")
        return _format_terms(backend.suggest(text, max_results))

    @tool_permission(ToolPermission.READ)
    def validate(self, vocab_name: str, term_code: str) -> str:
        """Validate a term code. Returns validity and suggestion if invalid."""
        backend = get_vocabulary(vocab_name)
        is_valid, suggestion = backend.validate(term_code)
        if is_valid:
            return f"Valid: {term_code}"
        msg = f"Invalid: {term_code}"
        if suggestion:
            msg += f" (did you mean '{suggestion}'?)"
        return msg
