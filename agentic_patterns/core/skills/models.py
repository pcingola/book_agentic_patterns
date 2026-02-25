"""Data models for the skills library."""

import re
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


class SkillEventType(str, Enum):
    ACTIVATE = "activate"
    EXEC = "exec"
    READ = "read"


class SkillEvent(BaseModel):
    """Records skill lifecycle events for observation."""

    skill_name: str
    event_type: SkillEventType
    payload: dict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def _validate_skill_name(value: str) -> str:
    if not 1 <= len(value) <= 64:
        raise ValueError("name must be 1-64 characters")
    if not _NAME_RE.match(value):
        raise ValueError(
            "name must be lowercase alphanumeric with hyphens (no leading/trailing/consecutive hyphens)"
        )
    return value


def _validate_skill_description(value: str) -> str:
    if not 1 <= len(value) <= 1024:
        raise ValueError("description must be 1-1024 characters")
    return value


class SkillMetadata(BaseModel):
    """Lightweight skill info for catalog/discovery (one-line view)."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    description: str
    path: Path

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        return _validate_skill_name(v)

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        return _validate_skill_description(v)

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
    asset_paths: list[Path]

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        return _validate_skill_name(v)

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        return _validate_skill_description(v)

    def __str__(self) -> str:
        return f"Skill({self.name})"
