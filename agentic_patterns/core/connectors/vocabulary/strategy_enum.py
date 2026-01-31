"""Enum strategy: in-memory dict for small vocabularies (< 100 terms)."""

from difflib import get_close_matches

from agentic_patterns.core.connectors.vocabulary.models import VocabularyInfo, VocabularyStrategy, VocabularyTerm


class StrategyEnum:
    """Full vocabulary loaded as a dict. Exact and fuzzy lookup."""

    def __init__(self, name: str, terms: list[VocabularyTerm]) -> None:
        self._name = name
        self._by_id: dict[str, VocabularyTerm] = {t.id: t for t in terms}
        self._label_to_id: dict[str, str] = {t.label.lower(): t.id for t in terms}
        for t in terms:
            for syn in t.synonyms:
                self._label_to_id[syn.lower()] = t.id

    def ancestors(self, term_code: str, max_depth: int = 10) -> list[VocabularyTerm]:
        return []

    def children(self, term_code: str) -> list[VocabularyTerm]:
        return []

    def descendants(self, term_code: str, max_depth: int = 10) -> list[VocabularyTerm]:
        return []

    def info(self) -> VocabularyInfo:
        return VocabularyInfo(name=self._name, strategy=VocabularyStrategy.ENUM, source_format="json", term_count=len(self._by_id))

    def lookup(self, term_code: str) -> VocabularyTerm | None:
        return self._by_id.get(term_code)

    def parent(self, term_code: str) -> list[VocabularyTerm]:
        return []

    def related(self, term_code: str, relation_type: str) -> list[VocabularyTerm]:
        return []

    def relationships(self, term_code: str) -> dict[str, list[str]]:
        return {}

    def roots(self) -> list[VocabularyTerm]:
        return list(self._by_id.values())

    def search(self, query: str, max_results: int = 10) -> list[VocabularyTerm]:
        query_lower = query.lower()
        # Exact match first
        if query_lower in self._label_to_id:
            term = self._by_id[self._label_to_id[query_lower]]
            return [term]
        # Substring match
        results = []
        for term in self._by_id.values():
            if query_lower in term.label.lower() or any(query_lower in s.lower() for s in term.synonyms):
                results.append(term)
                if len(results) >= max_results:
                    break
        # Fuzzy match as fallback
        if not results:
            all_labels = list(self._label_to_id.keys())
            close = get_close_matches(query_lower, all_labels, n=max_results, cutoff=0.6)
            for label in close:
                tid = self._label_to_id[label]
                if tid not in [r.id for r in results]:
                    results.append(self._by_id[tid])
        return results[:max_results]

    def siblings(self, term_code: str) -> list[VocabularyTerm]:
        return []

    def subtree(self, term_code: str, max_depth: int = 3) -> list[VocabularyTerm]:
        return []

    def validate(self, term_code: str) -> tuple[bool, str | None]:
        """Returns (is_valid, suggestion_id_if_invalid)."""
        if term_code in self._by_id:
            return True, None
        close = get_close_matches(term_code, list(self._by_id.keys()), n=1, cutoff=0.6)
        return False, close[0] if close else None
