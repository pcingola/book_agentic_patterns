"""Data models for the rubric pipeline."""

import uuid
from enum import Enum

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

    def __str__(self) -> str:
        return f"{self.doc_id} ({self.collection_name})"


class PoolItem(BaseModel):
    """An item flowing through the build pipeline (text + accumulated sources)."""

    text: str
    sources: list[SourceRef]


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
        return f"Rubric({self.rubric_id!r}, name={self.name!r}, {len(self.items)} items)"


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
