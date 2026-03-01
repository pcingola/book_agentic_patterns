"""Data models for deep research agent output."""

from pydantic import BaseModel


class Reference(BaseModel):
    """A cited source from the research."""

    url: str
    title: str
    snippet: str
    source_type: str  # "web" or "vectordb"

    def __str__(self) -> str:
        return f"Reference({self.title!r}, {self.source_type})"


class ResearchReport(BaseModel):
    """Final research output with inline citation markers [1], [2], etc."""

    content: str
    references: list[Reference]

    def __str__(self) -> str:
        return f"ResearchReport(refs={len(self.references)}, len={len(self.content)})"


# Internal LLM output models (not exported)


class _SubQuestions(BaseModel):
    questions: list[str]


class _GapAssessment(BaseModel):
    gaps: list[str]
    sufficient: bool


class _ConflictReport(BaseModel):
    conflicts: list[str]


class _SynthesisOutput(BaseModel):
    content: str
    references: list[Reference]
