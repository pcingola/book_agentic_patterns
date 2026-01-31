"""Tests for the vocabulary connector (Phase 1 -- toy data)."""

import unittest

from agentic_patterns.core.connectors.vocabulary.connector import VocabularyConnector
from agentic_patterns.core.connectors.vocabulary.models import VocabularyStrategy
from agentic_patterns.core.connectors.vocabulary.registry import get_vocabulary, list_vocabularies, register_vocabulary, reset
from agentic_patterns.core.connectors.vocabulary.strategy_enum import StrategyEnum
from agentic_patterns.core.connectors.vocabulary.strategy_tree import StrategyTree
from agentic_patterns.core.connectors.vocabulary.toy_data import get_toy_enum_terms, get_toy_tree_terms


class TestStrategyEnum(unittest.TestCase):

    def setUp(self) -> None:
        self.backend = StrategyEnum("biotypes", get_toy_enum_terms())

    def test_lookup_existing(self) -> None:
        term = self.backend.lookup("protein_coding")
        assert term is not None
        assert term.label == "Protein coding"

    def test_lookup_missing(self) -> None:
        assert self.backend.lookup("nonexistent") is None

    def test_search_exact(self) -> None:
        results = self.backend.search("Protein coding")
        assert len(results) == 1
        assert results[0].id == "protein_coding"

    def test_search_synonym(self) -> None:
        results = self.backend.search("mRNA")
        assert len(results) >= 1
        assert results[0].id == "protein_coding"

    def test_search_substring(self) -> None:
        results = self.backend.search("nuclear")
        assert len(results) >= 1
        ids = {r.id for r in results}
        assert "snRNA" in ids

    def test_search_fuzzy(self) -> None:
        results = self.backend.search("Pseudogen")
        assert len(results) >= 1
        assert results[0].id == "pseudogene"

    def test_validate_valid(self) -> None:
        is_valid, suggestion = self.backend.validate("miRNA")
        assert is_valid is True
        assert suggestion is None

    def test_validate_invalid_with_suggestion(self) -> None:
        is_valid, suggestion = self.backend.validate("miRN")
        assert is_valid is False
        assert suggestion == "miRNA"

    def test_info(self) -> None:
        info = self.backend.info()
        assert info.strategy == VocabularyStrategy.ENUM
        assert info.term_count == 10

    def test_roots_returns_all_for_flat_vocab(self) -> None:
        roots = self.backend.roots()
        assert len(roots) == 10


class TestStrategyTree(unittest.TestCase):

    def setUp(self) -> None:
        self.backend = StrategyTree("sequence_ontology", get_toy_tree_terms())

    def test_lookup(self) -> None:
        term = self.backend.lookup("SO:0000704")
        assert term is not None
        assert term.label == "gene"

    def test_children(self) -> None:
        children = self.backend.children("SO:0000704")
        ids = {c.id for c in children}
        assert "SO:0001217" in ids
        assert "SO:0000336" in ids

    def test_parent(self) -> None:
        parents = self.backend.parent("SO:0000704")
        assert len(parents) == 1
        assert parents[0].id == "SO:0000110"

    def test_ancestors(self) -> None:
        ancestors = self.backend.ancestors("SO:0001217")
        ids = {a.id for a in ancestors}
        assert "SO:0000704" in ids
        assert "SO:0000110" in ids

    def test_descendants(self) -> None:
        descendants = self.backend.descendants("SO:0000110")
        assert len(descendants) >= 5

    def test_siblings(self) -> None:
        siblings = self.backend.siblings("SO:0000704")
        ids = {s.id for s in siblings}
        assert "SO:0000001" in ids

    def test_roots(self) -> None:
        roots = self.backend.roots()
        ids = {r.id for r in roots}
        assert "SO:0000110" in ids

    def test_relationships(self) -> None:
        rels = self.backend.relationships("SO:0000316")
        assert "part_of" in rels
        assert "SO:0000234" in rels["part_of"]
        assert "is_a" in rels

    def test_related(self) -> None:
        related = self.backend.related("SO:0000316", "part_of")
        assert len(related) == 1
        assert related[0].id == "SO:0000234"

    def test_subtree(self) -> None:
        subtree = self.backend.subtree("SO:0001059")
        ids = {t.id for t in subtree}
        assert "SO:0001059" in ids
        assert "SO:0001483" in ids

    def test_search_by_synonym(self) -> None:
        results = self.backend.search("SNP")
        assert len(results) >= 1
        assert results[0].id == "SO:0001483"

    def test_validate(self) -> None:
        is_valid, _ = self.backend.validate("SO:0000704")
        assert is_valid is True

    def test_info(self) -> None:
        info = self.backend.info()
        assert info.strategy == VocabularyStrategy.TREE
        assert info.term_count == 19
        assert "part_of" in info.relation_types


class TestRegistry(unittest.TestCase):

    def setUp(self) -> None:
        reset()

    def test_register_and_get(self) -> None:
        backend = StrategyEnum("test", get_toy_enum_terms())
        register_vocabulary("test", backend)
        assert get_vocabulary("test") is backend

    def test_get_missing_raises(self) -> None:
        with self.assertRaises(KeyError):
            get_vocabulary("nonexistent")

    def test_list_vocabularies(self) -> None:
        register_vocabulary("a", StrategyEnum("a", get_toy_enum_terms()))
        register_vocabulary("b", StrategyTree("b", get_toy_tree_terms()))
        infos = list_vocabularies()
        assert len(infos) == 2


class TestVocabularyConnector(unittest.TestCase):

    def setUp(self) -> None:
        reset()
        register_vocabulary("biotypes", StrategyEnum("biotypes", get_toy_enum_terms()))
        register_vocabulary("so", StrategyTree("so", get_toy_tree_terms()))

    def test_lookup(self) -> None:
        result = VocabularyConnector.lookup("biotypes", "protein_coding")
        assert "Protein coding" in result

    def test_search(self) -> None:
        result = VocabularyConnector.search("so", "gene")
        assert "gene" in result

    def test_children(self) -> None:
        result = VocabularyConnector.children("so", "SO:0000704")
        assert "protein_coding_gene" in result

    def test_validate_valid(self) -> None:
        result = VocabularyConnector.validate("biotypes", "miRNA")
        assert "Valid" in result

    def test_validate_invalid(self) -> None:
        result = VocabularyConnector.validate("biotypes", "nonexistent")
        assert "Invalid" in result

    def test_list_vocabularies(self) -> None:
        result = VocabularyConnector.list_vocabularies()
        assert "biotypes" in result
        assert "so" in result

    def test_info(self) -> None:
        result = VocabularyConnector.info("biotypes")
        assert "enum" in result

    def test_error_on_missing_vocab(self) -> None:
        result = VocabularyConnector.lookup("nonexistent", "x")
        assert "[Error]" in result

    def test_relationships(self) -> None:
        result = VocabularyConnector.relationships("so", "SO:0000316")
        assert "part_of" in result

    def test_ancestors(self) -> None:
        result = VocabularyConnector.ancestors("so", "SO:0001217")
        assert "gene" in result

    def test_roots(self) -> None:
        result = VocabularyConnector.roots("so")
        assert "sequence_feature" in result


if __name__ == "__main__":
    unittest.main()
