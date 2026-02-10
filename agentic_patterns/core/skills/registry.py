"""Skill registry for discovering and loading skills."""

from pathlib import Path

import yaml

from agentic_patterns.core.skills.models import Skill, SkillMetadata


def _parse_frontmatter(content: str) -> tuple[dict | None, str]:
    """Parse SKILL.md into frontmatter dict and body content."""
    if not content.startswith("---"):
        return None, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return None, content
    try:
        frontmatter = yaml.safe_load(parts[1])
        body = parts[2].strip()
        return frontmatter, body
    except yaml.YAMLError:
        return None, content


def _collect_paths(directory: Path) -> list[Path]:
    """Collect all file paths in a directory."""
    if not directory.exists():
        return []
    return sorted(p for p in directory.iterdir() if p.is_file())


class SkillRegistry:
    """Registry for discovering and loading skills with progressive disclosure."""

    def __init__(self) -> None:
        self._metadata_cache: list[SkillMetadata] = []
        self._discovered = False

    def discover(self, roots: list[Path]) -> list[SkillMetadata]:
        """Scan skill directories and cache metadata (cheap operation)."""
        self._metadata_cache = []
        for root in roots:
            if not root.exists():
                continue
            for skill_dir in sorted(root.iterdir()):
                if not skill_dir.is_dir() or skill_dir.name.startswith("."):
                    continue
                skill_md = skill_dir / "SKILL.md"
                if not skill_md.exists():
                    continue
                try:
                    content = skill_md.read_text(encoding="utf-8")
                    frontmatter, _ = _parse_frontmatter(content)
                    if (
                        frontmatter
                        and "name" in frontmatter
                        and "description" in frontmatter
                    ):
                        self._metadata_cache.append(
                            SkillMetadata(
                                name=frontmatter["name"],
                                description=frontmatter["description"],
                                path=skill_dir,
                            )
                        )
                except (OSError, UnicodeDecodeError):
                    continue
        self._discovered = True
        return self._metadata_cache

    def get(self, name: str) -> Skill | None:
        """Load and return full Skill by name (expensive operation)."""
        for meta in self._metadata_cache:
            if meta.name == name:
                return self._load_skill(meta.path)
        return None

    def list_all(self) -> list[SkillMetadata]:
        """Return cached metadata list."""
        return self._metadata_cache

    def _load_skill(self, skill_dir: Path) -> Skill | None:
        """Load full skill from directory."""
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            return None
        try:
            content = skill_md.read_text(encoding="utf-8")
            frontmatter, body = _parse_frontmatter(content)
            if (
                not frontmatter
                or "name" not in frontmatter
                or "description" not in frontmatter
            ):
                return None
            return Skill(
                name=frontmatter["name"],
                description=frontmatter["description"],
                path=skill_dir,
                frontmatter=frontmatter,
                body=body,
                script_paths=_collect_paths(skill_dir / "scripts"),
                reference_paths=_collect_paths(skill_dir / "references"),
                asset_paths=_collect_paths(skill_dir / "assets"),
            )
        except (OSError, UnicodeDecodeError):
            return None
