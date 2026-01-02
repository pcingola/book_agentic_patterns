"""Prompt building utilities for Pydantic AI agent, including file handling and context management."""

import mimetypes
import re
import logging
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Optional

from agentic_patterns.core.config.config import PROMPTS_DIR


logger = logging.getLogger(__name__)


def load_prompt(prompt_path: Path, **kwargs) -> str:
    """Load a specific prompt file from the prompts directory.

    Args:
        prompt_path: Path to the markdown file (e.g., PROMPTS_DIR / 'system_prompt.md')
        **kwargs: Variables to substitute in the prompt template

    Returns:
        Content of the prompt file as a string, with variables substituted

    Raises:
        ValueError: If template has variables not provided in kwargs, or kwargs has unused variables
    """
    template = prompt_path.read_text(encoding="utf-8")

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
        raise ValueError(f"Template '{prompt_path.name}' received unused variables: {sorted(unused_vars)}")

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
