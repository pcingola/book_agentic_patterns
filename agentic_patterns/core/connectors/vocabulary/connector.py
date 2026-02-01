"""VocabularyConnector: vocabulary and ontology operations."""

from agentic_patterns.core.connectors.base import Connector
from agentic_patterns.core.connectors.vocabulary.models import VocabularyTerm
from agentic_patterns.core.connectors.vocabulary.registry import get_vocabulary, list_vocabularies as _list_vocabularies
from agentic_patterns.core.context.decorators import context_result


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

    def ancestors(self, vocab_name: str, term_code: str, max_depth: int = 10) -> str:
        """Get ancestor chain to root."""
        try:
            backend = get_vocabulary(vocab_name)
            return _format_terms(backend.ancestors(term_code, max_depth))
        except Exception as e:
            return f"[Error] {e}"

    @context_result()
    def children(self, vocab_name: str, term_code: str) -> str:
        """Get direct children of a term."""
        try:
            backend = get_vocabulary(vocab_name)
            return _format_terms(backend.children(term_code))
        except Exception as e:
            return f"[Error] {e}"

    @context_result()
    def descendants(self, vocab_name: str, term_code: str, max_depth: int = 10) -> str:
        """Get all descendants (subtree)."""
        try:
            backend = get_vocabulary(vocab_name)
            return _format_terms(backend.descendants(term_code, max_depth))
        except Exception as e:
            return f"[Error] {e}"

    def info(self, vocab_name: str) -> str:
        """Get vocabulary metadata."""
        try:
            backend = get_vocabulary(vocab_name)
            return str(backend.info())
        except Exception as e:
            return f"[Error] {e}"

    def list_vocabularies(self) -> str:
        """List all available vocabularies."""
        try:
            infos = _list_vocabularies()
            if not infos:
                return "No vocabularies registered."
            return "\n".join(str(i) for i in infos)
        except Exception as e:
            return f"[Error] {e}"

    def lookup(self, vocab_name: str, term_code: str) -> str:
        """Look up a term by its code/ID."""
        try:
            backend = get_vocabulary(vocab_name)
            term = backend.lookup(term_code)
            return str(term) if term else f"Term '{term_code}' not found in {vocab_name}."
        except Exception as e:
            return f"[Error] {e}"

    def parent(self, vocab_name: str, term_code: str) -> str:
        """Get direct parent(s) of a term."""
        try:
            backend = get_vocabulary(vocab_name)
            return _format_terms(backend.parent(term_code))
        except Exception as e:
            return f"[Error] {e}"

    def related(self, vocab_name: str, term_code: str, relation_type: str) -> str:
        """Get terms connected by a specific relation type."""
        try:
            backend = get_vocabulary(vocab_name)
            return _format_terms(backend.related(term_code, relation_type))
        except Exception as e:
            return f"[Error] {e}"

    def relationships(self, vocab_name: str, term_code: str) -> str:
        """Get all typed relationships for a term."""
        try:
            backend = get_vocabulary(vocab_name)
            return _format_relationships(backend.relationships(term_code))
        except Exception as e:
            return f"[Error] {e}"

    @context_result()
    def roots(self, vocab_name: str) -> str:
        """Get top-level terms."""
        try:
            backend = get_vocabulary(vocab_name)
            return _format_terms(backend.roots())
        except Exception as e:
            return f"[Error] {e}"

    @context_result()
    def search(self, vocab_name: str, query: str, max_results: int = 10) -> str:
        """Search for terms matching a query."""
        try:
            backend = get_vocabulary(vocab_name)
            return _format_terms(backend.search(query, max_results))
        except Exception as e:
            return f"[Error] {e}"

    @context_result()
    def siblings(self, vocab_name: str, term_code: str) -> str:
        """Get terms sharing the same parent."""
        try:
            backend = get_vocabulary(vocab_name)
            return _format_terms(backend.siblings(term_code))
        except Exception as e:
            return f"[Error] {e}"

    @context_result()
    def subtree(self, vocab_name: str, term_code: str, max_depth: int = 3) -> str:
        """Get hierarchical view for browsing."""
        try:
            backend = get_vocabulary(vocab_name)
            return _format_terms(backend.subtree(term_code, max_depth))
        except Exception as e:
            return f"[Error] {e}"

    def suggest(self, vocab_name: str, text: str, max_results: int = 10) -> str:
        """Semantic suggestions (RAG strategy only)."""
        try:
            backend = get_vocabulary(vocab_name)
            if not hasattr(backend, "suggest"):
                return "[Error] suggest is only available for RAG-backed vocabularies."
            return _format_terms(backend.suggest(text, max_results))
        except Exception as e:
            return f"[Error] {e}"

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
        except Exception as e:
            return f"[Error] {e}"
