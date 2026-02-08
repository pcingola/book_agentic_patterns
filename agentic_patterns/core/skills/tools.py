"""PydanticAI tool functions for agent integration with skills."""

from agentic_patterns.core.sandbox.manager import SandboxManager
from agentic_patterns.core.skills.registry import SkillRegistry


SKILLS_CONTAINER_ROOT = "/skills"


def create_skill_sandbox_manager(registry: SkillRegistry) -> SandboxManager:
    """Create a SandboxManager with read-only mounts for all discovered skills."""
    read_only_mounts = {}
    for meta in registry.list_all():
        scripts_dir = meta.path / "scripts"
        if scripts_dir.exists():
            read_only_mounts[str(scripts_dir)] = f"{SKILLS_CONTAINER_ROOT}/{meta.path.name}/scripts"
    return SandboxManager(read_only_mounts=read_only_mounts)


def get_skill_instructions(registry: SkillRegistry, name: str) -> str | None:
    """Returns full SKILL.md body for activation (second tier of progressive disclosure)."""
    skill = registry.get(name)
    if not skill:
        return None
    return skill.body


def list_available_skills(registry: SkillRegistry) -> str:
    """Returns a compact one-liner per skill (name + description)."""
    skills = registry.list_all()
    if not skills:
        return "No skills available."
    return "\n".join(str(skill) for skill in skills)


def run_skill_script(manager: SandboxManager, registry: SkillRegistry, user_id: str, session_id: str, skill_name: str, script_name: str, args: str = "") -> tuple[int, str]:
    """Execute a skill script inside the sandbox container."""
    skill = registry.get(skill_name)
    if not skill:
        return 1, f"Skill '{skill_name}' not found."

    matching = [p for p in skill.script_paths if p.name == script_name]
    if not matching:
        return 1, f"Script '{script_name}' not found in skill '{skill_name}'."

    container_path = f"{SKILLS_CONTAINER_ROOT}/{skill.path.name}/scripts/{script_name}"
    command = f"python {container_path} {args}".strip() if script_name.endswith(".py") else f"bash {container_path} {args}".strip()
    return manager.execute_command(user_id, session_id, command)
