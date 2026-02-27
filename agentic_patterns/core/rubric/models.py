"""Data models for rubric-based evaluation."""

from enum import Enum

from pydantic import BaseModel


class RequirementLevel(str, Enum):
    MUST = "MUST"
    SHOULD = "SHOULD"
    MAY = "MAY"


class VerdictStatus(str, Enum):
    PASS = "PASS"
    RISK = "RISK"
    FAIL = "FAIL"


class RubricItem(BaseModel):
    """A single evaluable requirement extracted from policy."""

    item_id: str
    title: str
    requirement_level: RequirementLevel
    requirement_text: str
    evidence_required: list[str]
    framework_mappings: dict[str, list[str]] = {}
    weight: float = 1.0
    tags: set[str] = set()

    def __str__(self) -> str:
        return (
            f"RubricItem({self.item_id}, {self.requirement_level.value}: {self.title})"
        )


class Rubric(BaseModel):
    """Versioned collection of rubric items with provenance tracking."""

    rubric_id: str
    provenance: dict
    items: list[RubricItem]

    def __str__(self) -> str:
        return f"Rubric({self.rubric_id}, items={len(self.items)})"


class SpanRef(BaseModel):
    """Pointer to a span within a retrieved document."""

    index_name: str
    doc_id: str
    start: int
    end: int

    def __str__(self) -> str:
        return f"SpanRef({self.index_name}:{self.doc_id}[{self.start}:{self.end}])"


class RubricVerdict(BaseModel):
    """Assessment result for a single rubric item."""

    item_id: str
    status: VerdictStatus
    rationale: str
    citations: list[SpanRef]
    missing_evidence: list[str] = []

    def __str__(self) -> str:
        return f"RubricVerdict({self.item_id}, {self.status.value}, citations={len(self.citations)})"
