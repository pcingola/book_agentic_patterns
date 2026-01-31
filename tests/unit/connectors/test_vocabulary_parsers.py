"""Tests for vocabulary parsers and loader (Phase 2)."""

import json
import unittest
from pathlib import Path

from agentic_patterns.core.connectors.vocabulary.loader import load_vocabulary, _create_backend
from agentic_patterns.core.connectors.vocabulary.models import SourceFormat, VocabularyConfig, VocabularyStrategy
from agentic_patterns.core.connectors.vocabulary.parser_obo import parse_obo
from agentic_patterns.core.connectors.vocabulary.parser_owl import parse_owl
from agentic_patterns.core.connectors.vocabulary.parser_rf2 import parse_rf2
from agentic_patterns.core.connectors.vocabulary.parser_tabular import parse_csv, parse_json_flat
from agentic_patterns.core.connectors.vocabulary.registry import get_vocabulary, reset

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "vocabulary"


class TestParserObo(unittest.TestCase):

    def setUp(self) -> None:
        self.terms = parse_obo(DATA_DIR / "test.obo")

    def test_term_count_excludes_obsolete(self) -> None:
        assert len(self.terms) == 4

    def test_root_term(self) -> None:
        root = next(t for t in self.terms if t.id == "TEST:0001")
        assert root.label == "root_term"
        assert root.definition == "The root term of the test ontology."

    def test_parent_relationship(self) -> None:
        child = next(t for t in self.terms if t.id == "TEST:0002")
        assert "TEST:0001" in child.parents

    def test_children_resolved(self) -> None:
        root = next(t for t in self.terms if t.id == "TEST:0001")
        assert "TEST:0002" in root.children
        assert "TEST:0003" in root.children

    def test_synonym_parsed(self) -> None:
        child = next(t for t in self.terms if t.id == "TEST:0002")
        assert "kid one" in child.synonyms

    def test_typed_relationship(self) -> None:
        child_two = next(t for t in self.terms if t.id == "TEST:0003")
        assert "part_of" in child_two.relationships
        assert "TEST:0002" in child_two.relationships["part_of"]

    def test_xref_in_metadata(self) -> None:
        grandchild = next(t for t in self.terms if t.id == "TEST:0004")
        assert "XREF:001" in grandchild.metadata.get("xrefs", "")

    def test_namespace_in_metadata(self) -> None:
        root = next(t for t in self.terms if t.id == "TEST:0001")
        assert root.metadata["namespace"] == "test_namespace"


class TestParserOwl(unittest.TestCase):

    def setUp(self) -> None:
        self.terms = parse_owl(DATA_DIR / "test.owl")

    def test_term_count_excludes_deprecated(self) -> None:
        assert len(self.terms) == 3

    def test_label_and_definition(self) -> None:
        alpha = next(t for t in self.terms if t.id == "TEST:0001")
        assert alpha.label == "alpha"
        assert alpha.definition == "The alpha class."

    def test_subclass_parent(self) -> None:
        beta = next(t for t in self.terms if t.id == "TEST:0002")
        assert "TEST:0001" in beta.parents

    def test_synonym(self) -> None:
        beta = next(t for t in self.terms if t.id == "TEST:0002")
        assert "beta_syn" in beta.synonyms

    def test_restriction_relationship(self) -> None:
        gamma = next(t for t in self.terms if t.id == "TEST:0003")
        assert "BFO:0000050" in gamma.relationships
        assert "TEST:0002" in gamma.relationships["BFO:0000050"]

    def test_children_resolved(self) -> None:
        alpha = next(t for t in self.terms if t.id == "TEST:0001")
        assert "TEST:0002" in alpha.children
        assert "TEST:0003" in alpha.children


class TestParserJsonFlat(unittest.TestCase):

    def setUp(self) -> None:
        self.terms = parse_json_flat(DATA_DIR / "test.json")

    def test_term_count(self) -> None:
        assert len(self.terms) == 3

    def test_fields(self) -> None:
        t = next(t for t in self.terms if t.id == "BT001")
        assert t.label == "protein_coding"
        assert t.definition == "Codes for protein"


class TestParserCsv(unittest.TestCase):

    def setUp(self) -> None:
        self.terms = parse_csv(DATA_DIR / "test.tsv", parent_field="parent", synonym_fields=["synonyms"])

    def test_term_count(self) -> None:
        assert len(self.terms) == 4

    def test_parent(self) -> None:
        t2 = next(t for t in self.terms if t.id == "T002")
        assert "T001" in t2.parents

    def test_children_resolved(self) -> None:
        t1 = next(t for t in self.terms if t.id == "T001")
        assert "T002" in t1.children
        assert "T003" in t1.children

    def test_synonyms_parsed(self) -> None:
        t1 = next(t for t in self.terms if t.id == "T001")
        assert "syn1" in t1.synonyms
        assert "syn2" in t1.synonyms


class TestParserRf2(unittest.TestCase):

    def setUp(self) -> None:
        self.terms = parse_rf2(DATA_DIR / "rf2")

    def test_active_concepts_only(self) -> None:
        ids = {t.id for t in self.terms}
        assert "100" in ids
        assert "200" in ids
        assert "300" in ids
        assert "999" not in ids

    def test_label_from_fsn(self) -> None:
        root = next(t for t in self.terms if t.id == "100")
        assert root.label == "Root concept"

    def test_synonym(self) -> None:
        root = next(t for t in self.terms if t.id == "100")
        assert "Root" in root.synonyms

    def test_is_a_relationship(self) -> None:
        child = next(t for t in self.terms if t.id == "200")
        assert "100" in child.parents

    def test_children_resolved(self) -> None:
        root = next(t for t in self.terms if t.id == "100")
        assert "200" in root.children


class TestLoader(unittest.TestCase):

    def setUp(self) -> None:
        reset()

    def test_load_obo_as_tree(self) -> None:
        config = VocabularyConfig(name="test_obo", strategy=VocabularyStrategy.TREE, source=str(DATA_DIR / "test.obo"), source_format=SourceFormat.OBO)
        backend = load_vocabulary(config)
        term = backend.lookup("TEST:0001")
        assert term is not None
        assert term.label == "root_term"

    def test_load_json_as_enum(self) -> None:
        config = VocabularyConfig(name="test_json", strategy=VocabularyStrategy.ENUM, source=str(DATA_DIR / "test.json"), source_format=SourceFormat.JSON_FLAT)
        backend = load_vocabulary(config)
        term = backend.lookup("BT001")
        assert term is not None

    def test_loaded_vocab_registered(self) -> None:
        config = VocabularyConfig(name="test_reg", strategy=VocabularyStrategy.ENUM, source=str(DATA_DIR / "test.json"), source_format=SourceFormat.JSON_FLAT)
        load_vocabulary(config)
        backend = get_vocabulary("test_reg")
        assert backend is not None

    def test_load_owl_as_tree(self) -> None:
        config = VocabularyConfig(name="test_owl", strategy=VocabularyStrategy.TREE, source=str(DATA_DIR / "test.owl"), source_format=SourceFormat.OWL)
        backend = load_vocabulary(config)
        assert backend.lookup("TEST:0001") is not None

    def test_load_rf2_as_tree(self) -> None:
        config = VocabularyConfig(name="test_rf2", strategy=VocabularyStrategy.TREE, source=str(DATA_DIR / "rf2"), source_format=SourceFormat.RF2)
        backend = load_vocabulary(config)
        assert backend.lookup("100") is not None


if __name__ == "__main__":
    unittest.main()
