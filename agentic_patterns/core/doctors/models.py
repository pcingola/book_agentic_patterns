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
    NAMING = "naming"
    DOCUMENTATION = "documentation"
    TYPES = "types"
    ARGUMENTS = "arguments"
    RETURN_TYPE = "return_type"
    CLARITY = "clarity"
    COMPLETENESS = "completeness"
    AMBIGUITY = "ambiguity"
    CAPABILITIES = "capabilities"
    ENDPOINTS = "endpoints"


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
