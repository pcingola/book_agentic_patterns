"""Skill registry for discovering and loading skills."""

import logging
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from agentic_patterns.core.prompt import get_prompt
from agentic_patterns.core.skills.models import Skill, SkillEvent, SkillEventType, SkillMetadata

if TYPE_CHECKING:
    from agentic_patterns.core.sandbox.manager import SandboxManager

logger = logging.getLogger(__name__)


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


def _run_script_sandboxed(
    sandbox: "SandboxManager",
    registry: "SkillRegistry",
    skill_name: str,
    script_name: str,
    args: str,
) -> tuple[int, str]:
    """Execute a skill script inside the Docker sandbox."""
    from agentic_patterns.core.skills.tools import run_skill_script_sandboxed
    from agentic_patterns.core.user_session import get_session_id, get_user_id

    return run_skill_script_sandboxed(
        sandbox, registry, get_user_id(), get_session_id(),
        skill_name, script_name, args,
    )


def _run_script_local(
    registry: "SkillRegistry",
    skill_name: str,
    script_name: str,
    args: str,
) -> tuple[int, str]:
    """Execute a skill script locally via subprocess (notebooks/demos only)."""
    skill = registry.get(skill_name)
    if skill is None:
        return 1, f"Skill '{skill_name}' not found."
    matching = [p for p in skill.script_paths if p.name == script_name]
    if not matching:
        return 1, f"Script '{script_name}' not found in skill '{skill_name}'."
    interpreter = "python" if script_name.endswith(".py") else "bash"
    cmd = [interpreter, str(matching[0])] + (args.split() if args else [])
    result = subprocess.run(cmd, capture_output=True, text=True)
    output = result.stdout.strip() if result.returncode == 0 else result.stderr.strip()
    return result.returncode, output


class SkillRegistry:
    """Registry for discovering and loading skills with progressive disclosure."""

    def __init__(self) -> None:
        self._metadata_cache: list[SkillMetadata] = []
        self._discovered = False
        self.on_event: Callable[[SkillEvent], Any] | None = None

    def _fire(self, event: SkillEvent) -> None:
        if self.on_event is None:
            return
        try:
            self.on_event(event)
        except Exception:
            logger.exception("on_event callback error for %s", event.event_type.value)

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
                        and frontmatter["name"] == skill_dir.name
                    ):
                        self._metadata_cache.append(
                            SkillMetadata(
                                name=frontmatter["name"],
                                description=frontmatter["description"],
                                path=skill_dir,
                            )
                        )
                except (OSError, UnicodeDecodeError, ValueError):
                    continue
        self._discovered = True
        return self._metadata_cache

    def get(self, name: str) -> Skill | None:
        """Load and return full Skill by name (expensive operation)."""
        for meta in self._metadata_cache:
            if meta.name == name:
                return self._load_skill(meta.path)
        return None

    def get_all_tools(
        self,
        sandbox: "SandboxManager | None" = None,
        *,
        allow_local: bool = False,
    ) -> list:
        """Return PydanticAI tools: activate_skill (Tier 2), run_skill_script and read_skill_resource (Tier 3).

        sandbox is required for script execution. Pass allow_local=True only in
        notebooks/demos where Docker is unavailable.
        """
        if sandbox is None and not allow_local:
            raise ValueError(
                "A SandboxManager is required for skill script execution. "
                "Pass allow_local=True only in notebooks/demos."
            )
        activated: set[str] = set()
        registry = self

        def activate_skill(skill_name: str) -> str:
            """Activate a skill by name to load its full instructions into context."""
            skill = registry.get(skill_name)
            if skill is None:
                return f"Skill '{skill_name}' not found. Use the skill catalog to see available skills."
            activated.add(skill_name)
            registry._fire(SkillEvent(skill_name=skill_name, event_type=SkillEventType.ACTIVATE))
            parts = [f"[SKILL ACTIVATED] {skill_name}", "", skill.body]
            if skill.script_paths:
                scripts = ", ".join(p.name for p in skill.script_paths)
                parts.append(f"\nAvailable scripts: {scripts}")
            if skill.reference_paths:
                refs = ", ".join(p.name for p in skill.reference_paths)
                parts.append(f"\nAvailable references: {refs}")
            if skill.asset_paths:
                assets = ", ".join(p.name for p in skill.asset_paths)
                parts.append(f"\nAvailable assets: {assets}")
            return "\n".join(parts)

        def read_skill_resource(
            skill_name: str, resource_type: str, file_name: str
        ) -> str:
            """Read a reference or asset file from an activated skill.
            resource_type must be 'reference' or 'asset'."""
            if skill_name not in activated:
                return f"Error: activate the '{skill_name}' skill first."
            skill = registry.get(skill_name)
            if skill is None:
                return f"Skill '{skill_name}' not found."
            if resource_type == "reference":
                paths = skill.reference_paths
            elif resource_type == "asset":
                paths = skill.asset_paths
            else:
                return f"Error: resource_type must be 'reference' or 'asset', got '{resource_type}'."
            matching = [p for p in paths if p.name == file_name]
            if not matching:
                available = ", ".join(p.name for p in paths) or "(none)"
                return f"File '{file_name}' not found in {resource_type}s for '{skill_name}'. Available: {available}"
            try:
                content = matching[0].read_text(encoding="utf-8")
                registry._fire(SkillEvent(
                    skill_name=skill_name, event_type=SkillEventType.READ,
                    payload={"resource_type": resource_type, "file_name": file_name},
                ))
                return content
            except UnicodeDecodeError:
                return (
                    f"Error: '{file_name}' is a binary file and cannot be read as text."
                )
            except OSError as e:
                return f"Error reading '{file_name}': {e}"

        def run_skill_script(skill_name: str, script_name: str, args: str = "") -> str:
            """Run a script bundled with an activated skill."""
            if skill_name not in activated:
                return f"Error: activate the '{skill_name}' skill first."
            if sandbox is not None:
                exit_code, output = _run_script_sandboxed(sandbox, registry, skill_name, script_name, args)
            else:
                exit_code, output = _run_script_local(registry, skill_name, script_name, args)
            registry._fire(SkillEvent(
                skill_name=skill_name, event_type=SkillEventType.EXEC,
                payload={"script": script_name, "exit_code": exit_code},
            ))
            header = f"[EXECUTE] {skill_name}/{script_name}"
            return (
                f"{header}\nExit code: {exit_code}\n{output}"
                if output
                else f"{header}\nScript produced no output."
            )

        return [activate_skill, run_skill_script, read_skill_resource]

    def catalog(self) -> str:
        """Return just the skill catalog listing (for use inside prompt templates)."""
        return "\n".join(str(s) for s in self._metadata_cache)

    def list_all(self) -> list[SkillMetadata]:
        """Return cached metadata list."""
        return self._metadata_cache

    def system_prompt(self) -> str:
        """Return the skills prompt block ready to inject into a system prompt."""
        cat = self.catalog()
        if not cat:
            return ""
        return get_prompt("shared/skills", skills_catalog=cat)

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
                or frontmatter["name"] != skill_dir.name
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
