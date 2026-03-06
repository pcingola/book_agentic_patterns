"""Prompt building utilities for Pydantic AI agent, including file handling and context management."""

import re
import logging
from pathlib import Path

from agentic_patterns.core.config.config import PACKAGE_PROMPTS_DIR, PROJECT_PROMPTS_DIR


logger = logging.getLogger(__name__)


def _resolve_prompt_path(name: str) -> Path:
    """Resolve a relative prompt name to an absolute path (project overrides package)."""
    if not name.endswith(".md"):
        name = f"{name}.md"
    project_path = PROJECT_PROMPTS_DIR / name
    if project_path.exists():
        return project_path
    package_path = PACKAGE_PROMPTS_DIR / name
    if package_path.exists():
        return package_path
    raise FileNotFoundError(f"Prompt not found: {name} (searched {PROJECT_PROMPTS_DIR}, {PACKAGE_PROMPTS_DIR})")


def _resolve_includes(text: str) -> str:
    """Resolve {% include 'path.md' %} directives."""
    include_re = re.compile(r"\{%\s*include\s+['\"](.+?)['\"]\s*%\}")
    while True:
        match = include_re.search(text)
        if not match:
            break
        include_path = _resolve_prompt_path(match.group(1))
        included = include_path.read_text(encoding="utf-8")
        text = text[: match.start()] + included + text[match.end() :]
    return text


def load_prompt(prompt: str | Path, **kwargs) -> str:
    """Load a prompt, resolve includes, and substitute variables.

    prompt can be a relative name (e.g. "anonymization/audit") resolved via
    project-then-package fallback, or an absolute Path for backward compatibility.
    """
    if isinstance(prompt, Path):
        prompt_path = prompt
    else:
        prompt_path = _resolve_prompt_path(prompt)

    template = prompt_path.read_text(encoding="utf-8")
    template = _resolve_includes(template)

    template_vars = set(re.findall(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", template))
    provided_vars = set(kwargs.keys())

    missing_vars = template_vars - provided_vars
    if missing_vars:
        raise ValueError(f"Template '{prompt_path.name}' requires variables that were not provided: {sorted(missing_vars)}")

    unused_vars = provided_vars - template_vars
    if unused_vars:
        raise ValueError(f"Template '{prompt_path.name}' received unused variables: {sorted(unused_vars)}")

    if kwargs:
        return template.format(**kwargs)
    return template


def get_system_prompt(**kwargs) -> str:
    """Load the system prompt from prompts/system_prompt.md."""
    return load_prompt("system_prompt", **kwargs)


def get_prompt(prompt_name: str, **kwargs) -> str:
    """Load a prompt from prompts/{prompt_name}.md."""
    return load_prompt(prompt_name, **kwargs)


def get_instructions(**kwargs) -> str:
    """Load the instructions from prompts/instructions.md."""
    return load_prompt("instructions", **kwargs)
