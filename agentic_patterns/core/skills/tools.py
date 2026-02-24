"""PydanticAI tool functions for agent integration with skills."""

import subprocess

from agentic_patterns.core.sandbox.manager import SandboxManager
from agentic_patterns.core.skills.registry import SkillRegistry


SKILLS_CONTAINER_ROOT = "/skills"


def create_skill_sandbox_manager(registry: SkillRegistry) -> SandboxManager:
    """Create a SandboxManager with read-only mounts for all discovered skills."""
    read_only_mounts = {}
    for meta in registry.list_all():
        scripts_dir = meta.path / "scripts"
        if scripts_dir.exists():
            read_only_mounts[str(scripts_dir)] = (
                f"{SKILLS_CONTAINER_ROOT}/{meta.path.name}/scripts"
            )
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


def get_all_tools(registry: SkillRegistry) -> list:
    """Get skill tools for use with PydanticAI agents.

    Returns activate_skill (Tier 2) and run_skill_script (Tier 3).
    Scripts run locally via subprocess. For sandboxed execution see
    run_skill_script_sandboxed().
    """
    activated: set[str] = set()

    def activate_skill(skill_name: str) -> str:
        """Activate a skill by name to load its full instructions into context."""
        skill = registry.get(skill_name)
        if skill is None:
            return f"Skill '{skill_name}' not found. Use the skill catalog to see available skills."
        activated.add(skill_name)
        parts = [skill.body]
        if skill.script_paths:
            scripts = ", ".join(p.name for p in skill.script_paths)
            parts.append(f"\nAvailable scripts: {scripts}")
        return "\n".join(parts)

    def run_skill_script(skill_name: str, script_name: str, args: str = "") -> str:
        """Run a script bundled with an activated skill."""
        if skill_name not in activated:
            return f"Error: activate the '{skill_name}' skill first."
        skill = registry.get(skill_name)
        if skill is None:
            return f"Skill '{skill_name}' not found."
        matching = [p for p in skill.script_paths if p.name == script_name]
        if not matching:
            return f"Script '{script_name}' not found in skill '{skill_name}'."
        interpreter = "python" if script_name.endswith(".py") else "bash"
        cmd = [interpreter, str(matching[0])] + (args.split() if args else [])
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stdout.strip() if result.returncode == 0 else result.stderr.strip()
        return f"Exit code: {result.returncode}\n{output}" if output else "Script produced no output."

    return [activate_skill, run_skill_script]


def run_skill_script_sandboxed(
    manager: SandboxManager,
    registry: SkillRegistry,
    user_id: str,
    session_id: str,
    skill_name: str,
    script_name: str,
    args: str = "",
) -> tuple[int, str]:
    """Execute a skill script inside the sandbox container."""
    skill = registry.get(skill_name)
    if not skill:
        return 1, f"Skill '{skill_name}' not found."

    matching = [p for p in skill.script_paths if p.name == script_name]
    if not matching:
        return 1, f"Script '{script_name}' not found in skill '{skill_name}'."

    container_path = f"{SKILLS_CONTAINER_ROOT}/{skill.path.name}/scripts/{script_name}"
    command = (
        f"python {container_path} {args}".strip()
        if script_name.endswith(".py")
        else f"bash {container_path} {args}".strip()
    )
    return manager.execute_command(user_id, session_id, command)
