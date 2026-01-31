"""Data models for vocabularies and ontologies."""

from enum import Enum

from pydantic import BaseModel


class VocabularyStrategy(str, Enum):
    ENUM = "enum"
    TREE = "tree"
    RAG = "rag"


class VocabularyTerm(BaseModel):
    """A single term in a vocabulary."""
    id: str
    label: str
    synonyms: list[str] = []
    definition: str | None = None
    parents: list[str] = []
    children: list[str] = []
    relationships: dict[str, list[str]] = {}
    metadata: dict[str, str] = {}

    def __str__(self) -> str:
        parts = [f"{self.id}: {self.label}"]
        if self.synonyms:
            parts.append(f"  synonyms: {', '.join(self.synonyms)}")
        if self.definition:
            parts.append(f"  definition: {self.definition}")
        if self.parents:
            parts.append(f"  parents: {', '.join(self.parents)}")
        if self.children:
            parts.append(f"  children: {', '.join(self.children)}")
        for rel_type, targets in self.relationships.items():
            parts.append(f"  {rel_type}: {', '.join(targets)}")
        return "\n".join(parts)


class VocabularyInfo(BaseModel):
    """Metadata about a loaded vocabulary."""
    name: str
    strategy: VocabularyStrategy
    source_format: str
    version: str | None = None
    term_count: int = 0
    relation_types: list[str] = []

    def __str__(self) -> str:
        return f"{self.name} ({self.strategy.value}, {self.term_count} terms, {self.source_format})"


class SourceFormat(str, Enum):
    OBO = "obo"
    OWL = "owl"
    JSON_FLAT = "json_flat"
    JSON_HIERARCHICAL = "json_hierarchical"
    CSV = "csv"
    TSV = "tsv"
    MESH_XML = "mesh_xml"
    GMT = "gmt"
    RF2 = "rf2"


class VocabularyConfig(BaseModel):
    """Configuration entry for a single vocabulary in vocabularies.yaml."""
    name: str
    strategy: VocabularyStrategy
    source: str | None = None
    source_format: SourceFormat | None = None
    collection: str | None = None
    embedding_config: str | None = None
    parser_options: dict[str, str] = {}
