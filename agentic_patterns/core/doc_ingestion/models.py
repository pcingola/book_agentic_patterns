"""Provenance model for document ingestion."""

from pathlib import Path

from pydantic import BaseModel


class DocumentProvenance(BaseModel):
    """Captures reference information at three levels for a document."""

    original_file: Path | None = None
    markdown_file: Path | None = None
    source: str | None = None

    def __str__(self) -> str:
        return self.source or str(self.original_file or self.markdown_file or "unknown")
