"""Skill doctor: Analyze Agent Skills (agentskills.io) and provide recommendations."""

import re
from pathlib import Path

import yaml

from agentic_patterns.core.agents import get_agent, run_agent
from agentic_patterns.core.config.config import PROMPTS_DIR
from agentic_patterns.core.doctors.base import DoctorBase
from agentic_patterns.core.doctors.models import (
    AgentSkillRecommendation,
    Issue,
    IssueCategory,
    IssueLevel,
    ScriptRecommendation,
)
from agentic_patterns.core.prompt import load_prompt


SKILL_NAME_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MAX_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024
MAX_COMPATIBILITY_LENGTH = 500
MAX_SKILL_MD_LINES = 500


class ScriptAnalysisResult(ScriptRecommendation):
    """Extended script recommendation with description match info."""

    is_documented: bool = False
    description_accurate: bool = True


class ConsistencyAnalysisResult:
    """Result of consistency analysis between scripts and SKILL.md."""

    def __init__(self) -> None:
        self.undocumented_scripts: list[str] = []
        self.phantom_references: list[str] = []
        self.issues: list[Issue] = []


def _parse_skill_md(content: str) -> tuple[dict | None, str]:
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


def _validate_body(body: str) -> list[Issue]:
    """Validate the markdown body content."""
    issues = []
    lines = body.split("\n")
    if len(lines) > MAX_SKILL_MD_LINES:
        issues.append(
            Issue(
                level=IssueLevel.WARNING,
                category=IssueCategory.COMPLETENESS,
                message=f"SKILL.md body exceeds {MAX_SKILL_MD_LINES} lines",
                suggestion="Move detailed content to files in references/ directory",
            )
        )
    if not body.strip():
        issues.append(
            Issue(
                level=IssueLevel.WARNING,
                category=IssueCategory.COMPLETENESS,
                message="SKILL.md body is empty",
                suggestion="Add instructions for the agent",
            )
        )
    return issues


def _validate_compatibility(compatibility: str | None) -> list[Issue]:
    """Validate the optional compatibility field."""
    if not compatibility:
        return []
    issues = []
    if len(compatibility) > MAX_COMPATIBILITY_LENGTH:
        issues.append(
            Issue(
                level=IssueLevel.ERROR,
                category=IssueCategory.DOCUMENTATION,
                message=f"Compatibility exceeds {MAX_COMPATIBILITY_LENGTH} characters",
                suggestion=f"Shorten to {MAX_COMPATIBILITY_LENGTH} or fewer characters",
            )
        )
    return issues


def _validate_description(description: str | None) -> list[Issue]:
    """Validate the description field."""
    issues = []
    if not description:
        issues.append(
            Issue(
                level=IssueLevel.ERROR,
                category=IssueCategory.DOCUMENTATION,
                message="Missing required 'description' field in frontmatter",
            )
        )
        return issues
    if len(description) > MAX_DESCRIPTION_LENGTH:
        issues.append(
            Issue(
                level=IssueLevel.ERROR,
                category=IssueCategory.DOCUMENTATION,
                message=f"Description exceeds {MAX_DESCRIPTION_LENGTH} characters",
                suggestion=f"Shorten to {MAX_DESCRIPTION_LENGTH} or fewer characters",
            )
        )
    if len(description) < 20:
        issues.append(
            Issue(
                level=IssueLevel.WARNING,
                category=IssueCategory.DOCUMENTATION,
                message="Description is too short",
                suggestion="Add more detail about what the skill does and when to use it",
            )
        )
    return issues


def _validate_frontmatter(frontmatter: dict | None, dir_name: str) -> list[Issue]:
    """Validate all frontmatter fields."""
    if frontmatter is None:
        return [
            Issue(
                level=IssueLevel.ERROR,
                category=IssueCategory.COMPLETENESS,
                message="Missing or invalid YAML frontmatter in SKILL.md",
                suggestion="Add frontmatter with --- delimiters containing name and description",
            )
        ]
    issues = []
    issues.extend(_validate_name(frontmatter.get("name"), dir_name))
    issues.extend(_validate_description(frontmatter.get("description")))
    issues.extend(_validate_compatibility(frontmatter.get("compatibility")))
    return issues


def _validate_name(name: str | None, dir_name: str) -> list[Issue]:
    """Validate the name field per Agent Skills specification."""
    issues = []
    if not name:
        issues.append(
            Issue(
                level=IssueLevel.ERROR,
                category=IssueCategory.NAMING,
                message="Missing required 'name' field in frontmatter",
            )
        )
        return issues
    if len(name) > MAX_NAME_LENGTH:
        issues.append(
            Issue(
                level=IssueLevel.ERROR,
                category=IssueCategory.NAMING,
                message=f"Name exceeds {MAX_NAME_LENGTH} characters",
                suggestion=f"Shorten to {MAX_NAME_LENGTH} or fewer characters",
            )
        )
    if not SKILL_NAME_PATTERN.match(name):
        issues.append(
            Issue(
                level=IssueLevel.ERROR,
                category=IssueCategory.NAMING,
                message="Name must be lowercase alphanumeric with hyphens, no leading/trailing/consecutive hyphens",
                suggestion="Use format like 'my-skill-name'",
            )
        )
    if name != dir_name:
        issues.append(
            Issue(
                level=IssueLevel.ERROR,
                category=IssueCategory.NAMING,
                message=f"Name '{name}' does not match directory name '{dir_name}'",
                suggestion=f"Change name to '{dir_name}' or rename directory to '{name}'",
            )
        )
    return issues


def _validate_structure(skill_dir: Path) -> list[Issue]:
    """Validate the skill directory structure."""
    issues = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        issues.append(
            Issue(
                level=IssueLevel.ERROR,
                category=IssueCategory.COMPLETENESS,
                message="Missing required SKILL.md file",
            )
        )
    for item in skill_dir.iterdir():
        if item.is_file() and item.name not in (
            "SKILL.md",
            "LICENSE",
            "LICENSE.txt",
            "LICENSE.md",
        ):
            if not item.name.startswith("."):
                issues.append(
                    Issue(
                        level=IssueLevel.ERROR,
                        category=IssueCategory.STRUCTURE,
                        message=f"Unexpected file '{item.name}' in skill root",
                        suggestion="Move to scripts/, references/, or assets/ directory",
                    )
                )
        elif (
            item.is_dir()
            and item.name not in ("scripts", "references", "assets")
            and not item.name.startswith(".")
        ):
            issues.append(
                Issue(
                    level=IssueLevel.ERROR,
                    category=IssueCategory.STRUCTURE,
                    message=f"Unexpected directory '{item.name}'",
                    suggestion="Use scripts/, references/, or assets/ for organization",
                )
            )
    return issues


def _collect_references(skill_dir: Path) -> list[tuple[str, str]]:
    """Collect reference files with their content."""
    refs_dir = skill_dir / "references"
    if not refs_dir.exists():
        return []
    refs = []
    for ref_file in refs_dir.iterdir():
        if ref_file.is_file() and ref_file.suffix.lower() in (
            ".md",
            ".txt",
            ".yaml",
            ".yml",
            ".json",
        ):
            try:
                content = ref_file.read_text(encoding="utf-8")
                refs.append((ref_file.name, content[:2000]))
            except (OSError, UnicodeDecodeError):
                refs.append((ref_file.name, "(unable to read)"))
    return refs


def _collect_scripts(skill_dir: Path) -> list[tuple[str, str]]:
    """Collect script files with their content."""
    scripts_dir = skill_dir / "scripts"
    if not scripts_dir.exists():
        return []
    scripts = []
    for script_file in sorted(scripts_dir.iterdir()):
        if script_file.is_file():
            try:
                content = script_file.read_text(encoding="utf-8")
                scripts.append((script_file.name, content))
            except (OSError, UnicodeDecodeError):
                scripts.append((script_file.name, "(unable to read)"))
    return scripts


def _format_skill_for_analysis(skill_dir: Path) -> str:
    """Format a skill directory for overall analysis."""
    skill_md = skill_dir / "SKILL.md"
    content = (
        skill_md.read_text(encoding="utf-8")
        if skill_md.exists()
        else "(SKILL.md not found)"
    )
    frontmatter, body = _parse_skill_md(content)
    references = _collect_references(skill_dir)
    scripts = _collect_scripts(skill_dir)

    out = f"### Skill: {skill_dir.name}\n\n"
    out += f"**Frontmatter:**\n```yaml\n{yaml.dump(frontmatter, default_flow_style=False) if frontmatter else '(none)'}\n```\n\n"
    out += f"**Body ({len(body.split(chr(10)))} lines):**\n```markdown\n{body[:3000]}\n```\n\n"
    if scripts:
        out += f"**Scripts ({len(scripts)} total):** {', '.join(name for name, _ in scripts)}\n"
    if references:
        out += "\n**References:**\n"
        for name, ref_content in references:
            out += f"\n`references/{name}` ({len(ref_content)} chars preview)\n"
    dirs = [
        d.name for d in skill_dir.iterdir() if d.is_dir() and not d.name.startswith(".")
    ]
    out += f"\n**Directories present:** {', '.join(dirs) if dirs else '(none)'}\n"
    return out


class SkillDoctor(DoctorBase):
    """Analyzes Agent Skills (agentskills.io format) for compliance and quality."""

    async def analyze(
        self, skill_dir: Path, verbose: bool = False
    ) -> AgentSkillRecommendation:
        """Analyze a single skill directory."""
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            return AgentSkillRecommendation(
                name=skill_dir.name,
                needs_improvement=True,
                issues=[
                    Issue(
                        level=IssueLevel.ERROR,
                        category=IssueCategory.COMPLETENESS,
                        message="Missing required SKILL.md file",
                    )
                ],
                body_issues=[],
                consistency_issues=[],
                frontmatter_issues=[],
                references=[],
                scripts=[],
                structure_issues=[],
            )

        content = skill_md.read_text(encoding="utf-8")
        frontmatter, body = _parse_skill_md(content)

        frontmatter_issues = _validate_frontmatter(frontmatter, skill_dir.name)
        body_issues = _validate_body(body)
        structure_issues = _validate_structure(skill_dir)

        skill_content = _format_skill_for_analysis(skill_dir)
        analysis_prompt = load_prompt(
            PROMPTS_DIR / "doctors" / "skill_doctor.md", skill_content=skill_content
        )

        agent = get_agent(output_type=AgentSkillRecommendation)
        agent_run, _ = await run_agent(agent, analysis_prompt, verbose=verbose)
        result = (
            agent_run.result.output
            if agent_run
            else AgentSkillRecommendation(
                name=skill_dir.name,
                needs_improvement=False,
                issues=[],
                body_issues=[],
                consistency_issues=[],
                frontmatter_issues=[],
                references=[],
                scripts=[],
                structure_issues=[],
            )
        )

        scripts = _collect_scripts(skill_dir)
        script_recommendations = await self._analyze_scripts_individually(
            content, scripts, verbose=verbose
        )
        consistency_issues = await self._analyze_consistency(
            content, [name for name, _ in scripts], verbose=verbose
        )

        result.frontmatter_issues.extend(frontmatter_issues)
        result.body_issues.extend(body_issues)
        result.structure_issues.extend(structure_issues)
        result.scripts = script_recommendations
        result.consistency_issues = consistency_issues

        def has_problems(issues: list[Issue]) -> bool:
            return any(i.level != IssueLevel.INFO for i in issues)

        result.needs_improvement = (
            result.needs_improvement
            or has_problems(frontmatter_issues)
            or has_problems(body_issues)
            or has_problems(structure_issues)
            or has_problems(consistency_issues)
            or any(s.has_problems() for s in script_recommendations)
        )
        return result

    async def _analyze_batch_internal(
        self, batch: list[Path], verbose: bool = False
    ) -> list[AgentSkillRecommendation]:
        """Analyze skills one by one."""
        results = []
        for skill_dir in batch:
            result = await self.analyze(skill_dir, verbose=verbose)
            results.append(result)
        return results

    async def _analyze_consistency(
        self, skill_md_content: str, scripts_present: list[str], verbose: bool = False
    ) -> list[Issue]:
        """Analyze consistency between scripts and SKILL.md documentation."""
        if not scripts_present:
            return []

        prompt = load_prompt(
            PROMPTS_DIR / "doctors" / "skill_consistency_doctor.md",
            skill_md_content=skill_md_content,
            scripts_present="\n".join(f"- {name}" for name in scripts_present),
        )

        class ConsistencyResult:
            undocumented_scripts: list[str]
            phantom_references: list[str]
            needs_improvement: bool

        from pydantic import BaseModel

        class ConsistencyAnalysis(BaseModel):
            undocumented_scripts: list[str]
            phantom_references: list[str]
            needs_improvement: bool

        agent = get_agent(output_type=ConsistencyAnalysis)
        agent_run, _ = await run_agent(agent, prompt, verbose=verbose)

        issues = []
        if agent_run and agent_run.result.output:
            result = agent_run.result.output
            for script_name in result.undocumented_scripts:
                issues.append(
                    Issue(
                        level=IssueLevel.ERROR,
                        category=IssueCategory.DOCUMENTATION,
                        message=f"Script '{script_name}' exists but is not documented in SKILL.md",
                        suggestion=f"Add documentation for scripts/{script_name} in SKILL.md body",
                    )
                )
            for ref in result.phantom_references:
                issues.append(
                    Issue(
                        level=IssueLevel.ERROR,
                        category=IssueCategory.CONSISTENCY,
                        message=f"SKILL.md references '{ref}' but no such script exists",
                        suggestion=f"Remove reference to '{ref}' or create the script",
                    )
                )
        return issues

    async def _analyze_scripts_individually(
        self,
        skill_md_content: str,
        scripts: list[tuple[str, str]],
        verbose: bool = False,
    ) -> list[ScriptRecommendation]:
        """Analyze each script individually against SKILL.md."""
        if not scripts:
            return []

        recommendations = []
        for script_name, script_content in scripts:
            if verbose:
                print(f"  Analyzing script: {script_name}")

            prompt = load_prompt(
                PROMPTS_DIR / "doctors" / "skill_script_doctor.md",
                skill_md_content=skill_md_content,
                script_name=script_name,
                script_content=script_content[:5000],
            )

            agent = get_agent(output_type=ScriptRecommendation)
            agent_run, _ = await run_agent(agent, prompt, verbose=verbose)

            if agent_run and agent_run.result.output:
                recommendations.append(agent_run.result.output)
            else:
                recommendations.append(
                    ScriptRecommendation(script_name=script_name, issues=[])
                )

        return recommendations


async def skill_doctor(
    skill_dirs: list[Path],
    verbose: bool = False,
) -> list[AgentSkillRecommendation]:
    """Analyze Agent Skills and provide recommendations for improvement.

    Args:
        skill_dirs: List of skill directory paths to analyze.
        verbose: Enable verbose output.

    Returns:
        List of recommendations for each skill.
    """
    doctor = SkillDoctor()
    results = []
    for i, skill_dir in enumerate(skill_dirs):
        if verbose:
            print(f"Analyzing skill {i + 1}/{len(skill_dirs)}: {skill_dir.name}")
        result = await doctor.analyze(skill_dir, verbose=verbose)
        results.append(result)
    return results
