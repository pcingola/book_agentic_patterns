"""Data models for the skills library."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict


class SkillMetadata(BaseModel):
    """Lightweight skill info for catalog/discovery (one-line view)."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    description: str
    path: Path

    def __str__(self) -> str:
        return f"{self.name}: {self.description}"


class Skill(BaseModel):
    """Full parsed skill with frontmatter, body, and file paths."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    description: str
    path: Path
    frontmatter: dict
    body: str
    script_paths: list[Path]
    reference_paths: list[Path]

    def __str__(self) -> str:
        return f"Skill({self.name})"
