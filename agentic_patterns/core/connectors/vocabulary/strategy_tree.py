"""Tree strategy: adjacency list with typed edges for medium vocabularies (< 1000 terms)."""

from collections import deque
from difflib import get_close_matches

from agentic_patterns.core.connectors.vocabulary.models import VocabularyInfo, VocabularyStrategy, VocabularyTerm


class StrategyTree:
    """Tree/graph with parent-child and typed relationships. Supports BFS/DFS traversal."""

    def __init__(self, name: str, terms: list[VocabularyTerm]) -> None:
        self._name = name
        self._by_id: dict[str, VocabularyTerm] = {t.id: t for t in terms}
        self._label_to_id: dict[str, str] = {t.label.lower(): t.id for t in terms}
        for t in terms:
            for syn in t.synonyms:
                self._label_to_id[syn.lower()] = t.id
        self._relation_types: set[str] = set()
        for t in terms:
            self._relation_types.update(t.relationships.keys())
            if t.parents:
                self._relation_types.add("is_a")

    def _bfs(self, start_id: str, direction: str, max_depth: int) -> list[VocabularyTerm]:
        """BFS traversal. direction is 'parents' or 'children'."""
        if start_id not in self._by_id:
            return []
        visited: set[str] = set()
        result: list[VocabularyTerm] = []
        queue: deque[tuple[str, int]] = deque([(start_id, 0)])
        visited.add(start_id)
        while queue:
            current_id, depth = queue.popleft()
            if depth > 0:
                term = self._by_id.get(current_id)
                if term:
                    result.append(term)
            if depth >= max_depth:
                continue
            current_term = self._by_id.get(current_id)
            if not current_term:
                continue
            neighbors = current_term.parents if direction == "parents" else current_term.children
            for nid in neighbors:
                if nid not in visited:
                    visited.add(nid)
                    queue.append((nid, depth + 1))
        return result

    def ancestors(self, term_code: str, max_depth: int = 10) -> list[VocabularyTerm]:
        return self._bfs(term_code, "parents", max_depth)

    def children(self, term_code: str) -> list[VocabularyTerm]:
        term = self._by_id.get(term_code)
        if not term:
            return []
        return [self._by_id[cid] for cid in term.children if cid in self._by_id]

    def descendants(self, term_code: str, max_depth: int = 10) -> list[VocabularyTerm]:
        return self._bfs(term_code, "children", max_depth)

    def info(self) -> VocabularyInfo:
        return VocabularyInfo(name=self._name, strategy=VocabularyStrategy.TREE, source_format="obo", term_count=len(self._by_id), relation_types=sorted(self._relation_types))

    def lookup(self, term_code: str) -> VocabularyTerm | None:
        return self._by_id.get(term_code)

    def parent(self, term_code: str) -> list[VocabularyTerm]:
        term = self._by_id.get(term_code)
        if not term:
            return []
        return [self._by_id[pid] for pid in term.parents if pid in self._by_id]

    def related(self, term_code: str, relation_type: str) -> list[VocabularyTerm]:
        term = self._by_id.get(term_code)
        if not term:
            return []
        ids = term.relationships.get(relation_type, [])
        return [self._by_id[rid] for rid in ids if rid in self._by_id]

    def relationships(self, term_code: str) -> dict[str, list[str]]:
        term = self._by_id.get(term_code)
        if not term:
            return {}
        result = dict(term.relationships)
        if term.parents:
            result["is_a"] = term.parents
        return result

    def roots(self) -> list[VocabularyTerm]:
        return [t for t in self._by_id.values() if not t.parents]

    def search(self, query: str, max_results: int = 10) -> list[VocabularyTerm]:
        query_lower = query.lower()
        if query_lower in self._label_to_id:
            return [self._by_id[self._label_to_id[query_lower]]]
        results = []
        for term in self._by_id.values():
            if query_lower in term.label.lower() or any(query_lower in s.lower() for s in term.synonyms):
                results.append(term)
                if len(results) >= max_results:
                    break
        if not results:
            close = get_close_matches(query_lower, list(self._label_to_id.keys()), n=max_results, cutoff=0.6)
            for label in close:
                tid = self._label_to_id[label]
                if tid not in [r.id for r in results]:
                    results.append(self._by_id[tid])
        return results[:max_results]

    def siblings(self, term_code: str) -> list[VocabularyTerm]:
        term = self._by_id.get(term_code)
        if not term or not term.parents:
            return []
        sibling_ids: set[str] = set()
        for pid in term.parents:
            parent_term = self._by_id.get(pid)
            if parent_term:
                sibling_ids.update(parent_term.children)
        sibling_ids.discard(term_code)
        return [self._by_id[sid] for sid in sibling_ids if sid in self._by_id]

    def subtree(self, term_code: str, max_depth: int = 3) -> list[VocabularyTerm]:
        term = self._by_id.get(term_code)
        if not term:
            return []
        return [term] + self.descendants(term_code, max_depth)

    def validate(self, term_code: str) -> tuple[bool, str | None]:
        if term_code in self._by_id:
            return True, None
        close = get_close_matches(term_code, list(self._by_id.keys()), n=1, cutoff=0.6)
        return False, close[0] if close else None
