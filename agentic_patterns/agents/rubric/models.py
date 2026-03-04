"""Data models for the rubric pipeline."""

import uuid
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class RequirementLevel(str, Enum):
    MUST = "MUST"
    SHOULD = "SHOULD"
    MAY = "MAY"


class VerdictStatus(str, Enum):
    PASS = "PASS"
    RISK = "RISK"
    FAIL = "FAIL"


class SourceRef(BaseModel):
    """Reference to a source document in a named collection."""

    doc_id: str
    collection_name: str
    source_text: str = ""  # original chunk text for audit trail

    def __str__(self) -> str:
        return f"{self.doc_id} ({self.collection_name})"


class PoolItem(BaseModel):
    """An item flowing through the build pipeline.

    For requirements: structured fields (requirement_level, title, requirement_text,
    evidence_required) carry the extraction data. After merge passes these are cleared
    since the merged text may combine multiple items.
    The text field is always set as the pipeline representation for LLM prompts and embedding.
    """

    text: str
    sources: list[SourceRef]
    label: str = ""  # short human-readable description for logging
    requirement_level: RequirementLevel | None = None
    title: str = ""
    requirement_text: str = ""
    evidence_required: list[str] = Field(default_factory=list)


class RubricItem(BaseModel):
    """A single evaluable compliance requirement."""

    item_id: str
    title: str
    requirement_level: RequirementLevel
    requirement_text: str
    evidence_required: list[str]
    sources: list[SourceRef] = Field(default_factory=list)
    framework_mappings: dict[str, list[str]] = Field(default_factory=dict)
    tags: set[str] = Field(default_factory=set)

    def __str__(self) -> str:
        return f"[{self.requirement_level.value}] {self.item_id}: {self.title}"


class Rubric(BaseModel):
    """A versioned collection of rubric items."""

    rubric_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str
    items: list[RubricItem] = Field(default_factory=list)
    provenance: dict = Field(default_factory=dict)

    def __str__(self) -> str:
        header = f"Rubric({self.rubric_id!r}, name={self.name!r}, {len(self.items)} items)"
        if not self.items:
            return header
        items_str = "\n".join(f"  {item}" for item in self.items)
        return f"{header}\n{items_str}"

    def save(self, path: Path) -> None:
        """Save rubric to a JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "Rubric":
        """Load rubric from a JSON file."""
        return cls.model_validate_json(Path(path).read_text(encoding="utf-8"))


class SpanRef(BaseModel):
    """Document span reference for evidence citations."""

    index_name: str
    doc_id: str
    start: int
    end: int


class RubricVerdict(BaseModel):
    """Per-item assessment result."""

    item_id: str
    status: VerdictStatus
    rationale: str
    citations: list[SpanRef] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)

    def __str__(self) -> str:
        return f"RubricVerdict({self.item_id}, {self.status.value})"
