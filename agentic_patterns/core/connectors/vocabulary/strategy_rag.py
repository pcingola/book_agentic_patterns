"""RAG strategy: vector DB for large vocabularies (1000+ terms)."""

import json

from agentic_patterns.core.connectors.vocabulary.models import (
    VocabularyInfo,
    VocabularyStrategy,
    VocabularyTerm,
)
from agentic_patterns.core.vectordb.vectordb import VectorDB, get_vector_db


def _term_to_document(term: VocabularyTerm) -> str:
    """Build the document text for embedding: label | synonyms | definition."""
    parts = [term.label]
    if term.synonyms:
        parts.append(" | ".join(term.synonyms))
    if term.definition:
        parts.append(term.definition)
    return " | ".join(parts)


def _meta_to_term(doc_id: str, meta: dict) -> VocabularyTerm:
    """Reconstruct a VocabularyTerm from stored metadata."""
    return VocabularyTerm(
        id=doc_id,
        label=meta.get("label", ""),
        synonyms=json.loads(meta.get("synonyms", "[]")),
        definition=meta.get("definition"),
        parents=json.loads(meta.get("parents", "[]")),
        children=json.loads(meta.get("children", "[]")),
        relationships=json.loads(meta.get("relationships", "{}")),
    )


class StrategyRag:
    """Vector DB backed strategy using existing vectordb module."""

    def __init__(
        self,
        name: str,
        collection: str | None = None,
        embedding_config: str | None = None,
    ) -> None:
        self._name = name
        self._collection_name = collection or name
        self._embedding_config = embedding_config
        self._vdb: VectorDB = get_vector_db(
            self._collection_name, embedding_config=self._embedding_config
        )
        self._relation_types: set[str] = set()

    def _get_term_by_id(self, term_id: str) -> VocabularyTerm | None:
        result = self._vdb.get_by_id(term_id)
        if not result["ids"]:
            return None
        return _meta_to_term(term_id, result["metadatas"][0])

    def add_term(self, term: VocabularyTerm) -> None:
        """Index a term into the vector DB."""
        meta = {
            "term_id": term.id,
            "label": term.label,
            "synonyms": json.dumps(term.synonyms),
            "definition": term.definition or "",
            "parents": json.dumps(term.parents),
            "children": json.dumps(term.children),
            "relationships": json.dumps(term.relationships),
        }
        self._relation_types.update(term.relationships.keys())
        if term.parents:
            self._relation_types.add("is_a")
        self._vdb.add(_term_to_document(term), term.id, meta=meta, force=True)

    def ancestors(self, term_code: str, max_depth: int = 10) -> list[VocabularyTerm]:
        result: list[VocabularyTerm] = []
        visited: set[str] = {term_code}
        current_ids = [term_code]
        for _ in range(max_depth):
            next_ids: list[str] = []
            for cid in current_ids:
                term = self._get_term_by_id(cid)
                if term:
                    for pid in term.parents:
                        if pid not in visited:
                            visited.add(pid)
                            parent = self._get_term_by_id(pid)
                            if parent:
                                result.append(parent)
                                next_ids.append(pid)
            if not next_ids:
                break
            current_ids = next_ids
        return result

    def children(self, term_code: str) -> list[VocabularyTerm]:
        term = self._get_term_by_id(term_code)
        if not term:
            return []
        return [t for cid in term.children if (t := self._get_term_by_id(cid))]

    def descendants(self, term_code: str, max_depth: int = 10) -> list[VocabularyTerm]:
        result: list[VocabularyTerm] = []
        visited: set[str] = {term_code}
        current_ids = [term_code]
        for _ in range(max_depth):
            next_ids: list[str] = []
            for cid in current_ids:
                term = self._get_term_by_id(cid)
                if term:
                    for child_id in term.children:
                        if child_id not in visited:
                            visited.add(child_id)
                            child = self._get_term_by_id(child_id)
                            if child:
                                result.append(child)
                                next_ids.append(child_id)
            if not next_ids:
                break
            current_ids = next_ids
        return result

    def info(self) -> VocabularyInfo:
        return VocabularyInfo(
            name=self._name,
            strategy=VocabularyStrategy.RAG,
            source_format="vector_db",
            term_count=self._vdb.count(),
            relation_types=sorted(self._relation_types),
        )

    def lookup(self, term_code: str) -> VocabularyTerm | None:
        return self._get_term_by_id(term_code)

    def parent(self, term_code: str) -> list[VocabularyTerm]:
        term = self._get_term_by_id(term_code)
        if not term:
            return []
        return [t for pid in term.parents if (t := self._get_term_by_id(pid))]

    def related(self, term_code: str, relation_type: str) -> list[VocabularyTerm]:
        term = self._get_term_by_id(term_code)
        if not term:
            return []
        return [
            t
            for rid in term.relationships.get(relation_type, [])
            if (t := self._get_term_by_id(rid))
        ]

    def relationships(self, term_code: str) -> dict[str, list[str]]:
        term = self._get_term_by_id(term_code)
        if not term:
            return {}
        result = dict(term.relationships)
        if term.parents:
            result["is_a"] = term.parents
        return result

    def roots(self) -> list[VocabularyTerm]:
        ids, metadatas = self._vdb.get_all_metadatas()
        return [
            _meta_to_term(doc_id, meta)
            for doc_id, meta in zip(ids, metadatas)
            if not json.loads(meta.get("parents", "[]"))
        ]

    def search(self, query: str, max_results: int = 10) -> list[VocabularyTerm]:
        """Semantic search via vector DB."""
        return [
            _meta_to_term(doc.metadata["term_id"], doc.metadata)
            for doc in self._vdb.query(query, max_items=max_results)
            if doc.metadata
        ]

    def siblings(self, term_code: str) -> list[VocabularyTerm]:
        term = self._get_term_by_id(term_code)
        if not term or not term.parents:
            return []
        sibling_ids: set[str] = set()
        for pid in term.parents:
            parent = self._get_term_by_id(pid)
            if parent:
                sibling_ids.update(parent.children)
        sibling_ids.discard(term_code)
        return [t for sid in sibling_ids if (t := self._get_term_by_id(sid))]

    def subtree(self, term_code: str, max_depth: int = 3) -> list[VocabularyTerm]:
        term = self._get_term_by_id(term_code)
        if not term:
            return []
        return [term] + self.descendants(term_code, max_depth)

    def suggest(self, text: str, max_results: int = 10) -> list[VocabularyTerm]:
        """Semantic suggestion -- same as search for RAG."""
        return self.search(text, max_results)

    def validate(self, term_code: str) -> tuple[bool, str | None]:
        term = self._get_term_by_id(term_code)
        if term:
            return True, None
        results = self.search(term_code, max_results=1)
        return False, results[0].id if results else None
