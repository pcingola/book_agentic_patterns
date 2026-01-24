"""Shared Pydantic models for doctor recommendations."""

from enum import Enum

from pydantic import BaseModel


class IssueLevel(str, Enum):
    """Severity level of an issue."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class IssueCategory(str, Enum):
    """Category of an issue."""
    AMBIGUITY = "ambiguity"
    ARGUMENTS = "arguments"
    CAPABILITIES = "capabilities"
    CLARITY = "clarity"
    COMPLETENESS = "completeness"
    CONSISTENCY = "consistency"
    DOCUMENTATION = "documentation"
    ENDPOINTS = "endpoints"
    NAMING = "naming"
    RETURN_TYPE = "return_type"
    SCRIPTS = "scripts"
    STRUCTURE = "structure"
    TYPES = "types"


class Issue(BaseModel):
    """A single issue found during analysis."""
    level: IssueLevel
    category: IssueCategory
    message: str
    suggestion: str | None = None

    def __str__(self) -> str:
        out = f"[{self.level.value}] {self.category.value}: {self.message}"
        if self.suggestion:
            out += f" -> {self.suggestion}"
        return out


class ArgumentRecommendation(BaseModel):
    """Recommendation for a function argument."""
    arg_name: str
    arg_type: str
    issues: list[Issue]

    def __str__(self) -> str:
        if not self.issues:
            return f"{self.arg_name}: {self.arg_type} - OK"
        issues_str = "; ".join(str(i) for i in self.issues)
        return f"{self.arg_name}: {self.arg_type} - {issues_str}"


class Recommendation(BaseModel):
    """Base recommendation for any analyzed artifact."""
    name: str
    needs_improvement: bool
    issues: list[Issue]

    def __str__(self) -> str:
        status = "NEEDS IMPROVEMENT" if self.needs_improvement else "OK"
        out = f"{self.name}: {status}"
        if self.issues:
            out += "\n  Issues:"
            for issue in self.issues:
                out += f"\n    - {issue}"
        return out


class ToolRecommendation(Recommendation):
    """Recommendation for a tool/function."""
    arguments: list[ArgumentRecommendation]
    return_type_issues: list[Issue]

    def __str__(self) -> str:
        status = "NEEDS IMPROVEMENT" if self.needs_improvement else "OK"
        out = f"Tool: {self.name} - {status}"
        if self.issues:
            out += "\n  General issues:"
            for issue in self.issues:
                out += f"\n    - {issue}"
        if self.return_type_issues:
            out += "\n  Return type issues:"
            for issue in self.return_type_issues:
                out += f"\n    - {issue}"
        args_with_issues = [a for a in self.arguments if a.issues]
        if args_with_issues:
            out += "\n  Argument issues:"
            for arg in args_with_issues:
                out += f"\n    - {arg}"
        return out


class PromptRecommendation(Recommendation):
    """Recommendation for a prompt."""
    placeholders_found: list[str]

    def __str__(self) -> str:
        status = "NEEDS IMPROVEMENT" if self.needs_improvement else "OK"
        out = f"Prompt: {self.name} - {status}"
        if self.placeholders_found:
            out += f"\n  Placeholders: {', '.join(self.placeholders_found)}"
        if self.issues:
            out += "\n  Issues:"
            for issue in self.issues:
                out += f"\n    - {issue}"
        return out


class SkillRecommendation(BaseModel):
    """Recommendation for an A2A skill."""
    skill_id: str
    issues: list[Issue]

    def __str__(self) -> str:
        if not self.issues:
            return f"{self.skill_id}: OK"
        issues_str = "; ".join(str(i) for i in self.issues)
        return f"{self.skill_id}: {issues_str}"


class A2ARecommendation(Recommendation):
    """Recommendation for an A2A agent card."""
    capabilities: list[str]
    skills: list[SkillRecommendation]

    def __str__(self) -> str:
        status = "NEEDS IMPROVEMENT" if self.needs_improvement else "OK"
        out = f"Agent: {self.name} - {status}"
        if self.capabilities:
            out += f"\n  Capabilities: {', '.join(self.capabilities)}"
        if self.issues:
            out += "\n  General issues:"
            for issue in self.issues:
                out += f"\n    - {issue}"
        skills_with_issues = [s for s in self.skills if s.issues]
        if skills_with_issues:
            out += "\n  Skill issues:"
            for skill in skills_with_issues:
                out += f"\n    - {skill}"
        return out


class ScriptRecommendation(BaseModel):
    """Recommendation for a script in a skill."""
    script_name: str
    issues: list[Issue]

    def __str__(self) -> str:
        if not self.issues:
            return f"{self.script_name}: OK"
        issues_str = "; ".join(str(i) for i in self.issues)
        return f"{self.script_name}: {issues_str}"


class AgentSkillRecommendation(Recommendation):
    """Recommendation for an Agent Skill (agentskills.io format)."""
    body_issues: list[Issue]
    consistency_issues: list[Issue]
    frontmatter_issues: list[Issue]
    references: list[Issue]
    scripts: list[ScriptRecommendation]
    structure_issues: list[Issue]

    def __str__(self) -> str:
        status = "NEEDS IMPROVEMENT" if self.needs_improvement else "OK"
        out = f"Skill: {self.name} - {status}"
        if self.issues:
            out += "\n  General issues:"
            for issue in self.issues:
                out += f"\n    - {issue}"
        if self.frontmatter_issues:
            out += "\n  Frontmatter issues:"
            for issue in self.frontmatter_issues:
                out += f"\n    - {issue}"
        if self.body_issues:
            out += "\n  Body issues:"
            for issue in self.body_issues:
                out += f"\n    - {issue}"
        scripts_with_issues = [s for s in self.scripts if s.issues]
        if scripts_with_issues:
            out += "\n  Script issues:"
            for script in scripts_with_issues:
                out += f"\n    - {script}"
        if self.consistency_issues:
            out += "\n  Consistency issues:"
            for issue in self.consistency_issues:
                out += f"\n    - {issue}"
        if self.references:
            out += "\n  Reference issues:"
            for issue in self.references:
                out += f"\n    - {issue}"
        if self.structure_issues:
            out += "\n  Structure issues:"
            for issue in self.structure_issues:
                out += f"\n    - {issue}"
        return out
