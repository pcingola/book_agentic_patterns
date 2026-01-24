"""Data models for the skills library."""

from pathlib import Path

from pydantic import BaseModel


class SkillMetadata(BaseModel):
    """Lightweight skill info for catalog/discovery (one-line view)."""
    name: str
    description: str
    path: Path

    class Config:
        arbitrary_types_allowed = True

    def __str__(self) -> str:
        return f"{self.name}: {self.description}"


class Skill(BaseModel):
    """Full parsed skill with frontmatter, body, and file paths."""
    name: str
    description: str
    path: Path
    frontmatter: dict
    body: str
    script_paths: list[Path]
    reference_paths: list[Path]

    class Config:
        arbitrary_types_allowed = True

    def __str__(self) -> str:
        return f"Skill({self.name})"
