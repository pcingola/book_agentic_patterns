"""PydanticAI tool functions for agent integration with skills."""

from agentic_patterns.core.skills.registry import SkillRegistry


def list_available_skills(registry: SkillRegistry) -> str:
    """Returns a compact one-liner per skill (name + description)."""
    skills = registry.list_all()
    if not skills:
        return "No skills available."
    return "\n".join(str(skill) for skill in skills)


def get_skill_instructions(registry: SkillRegistry, name: str) -> str | None:
    """Returns full SKILL.md body and reference file paths for activation."""
    skill = registry.get(name)
    if not skill:
        return None
    lines = [skill.body]
    if skill.reference_paths:
        lines.append("\n## References")
        for ref_path in skill.reference_paths:
            lines.append(f"- {ref_path}")
    if skill.script_paths:
        lines.append("\n## Scripts")
        for script_path in skill.script_paths:
            lines.append(f"- {script_path}")
    return "\n".join(lines)
