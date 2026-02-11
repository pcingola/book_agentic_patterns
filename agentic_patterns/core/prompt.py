"""Prompt building utilities for Pydantic AI agent, including file handling and context management."""

import re
import logging
from pathlib import Path

from agentic_patterns.core.config.config import PROMPTS_DIR


logger = logging.getLogger(__name__)


def _resolve_includes(text: str, base_dir: Path) -> str:
    """Resolve {% include 'path.md' %} directives relative to PROMPTS_DIR."""
    include_re = re.compile(r"\{%\s*include\s+['\"](.+?)['\"]\s*%\}")
    while True:
        match = include_re.search(text)
        if not match:
            break
        include_path = PROMPTS_DIR / match.group(1)
        if not include_path.exists():
            raise FileNotFoundError(f"Include file not found: {include_path}")
        included = include_path.read_text(encoding="utf-8")
        text = text[:match.start()] + included + text[match.end():]
    return text


def load_prompt(prompt_path: Path, **kwargs) -> str:
    """Load a prompt file, resolve includes, and substitute variables.

    Supports {% include 'relative/path.md' %} directives resolved relative to PROMPTS_DIR.
    """
    template = prompt_path.read_text(encoding="utf-8")
    template = _resolve_includes(template, prompt_path.parent)

    # Extract all variables from the template using regex
    template_vars = set(re.findall(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", template))
    provided_vars = set(kwargs.keys())

    # Check for missing variables
    missing_vars = template_vars - provided_vars
    if missing_vars:
        raise ValueError(
            f"Template '{prompt_path.name}' requires variables that were not provided: {sorted(missing_vars)}"
        )

    # Check for unused variables
    unused_vars = provided_vars - template_vars
    if unused_vars:
        raise ValueError(
            f"Template '{prompt_path.name}' received unused variables: {sorted(unused_vars)}"
        )

    if kwargs:
        return template.format(**kwargs)
    return template


def get_system_prompt(**kwargs) -> str:
    """Load the system prompt from prompts/system_prompt.md."""
    return load_prompt(PROMPTS_DIR / "system_prompt.md", **kwargs)


def get_prompt(prompt_name: str, **kwargs) -> str:
    """Load a prompt from prompts/{prompt_name}.md."""
    return load_prompt(PROMPTS_DIR / f"{prompt_name}.md", **kwargs)


def get_instructions(**kwargs) -> str:
    """Load the instructions from prompts/instructions.md."""
    return load_prompt(PROMPTS_DIR / "instructions.md", **kwargs)
