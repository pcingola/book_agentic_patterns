"""NL2SQL sub-agent -- local equivalent of the A2A nl2sql server."""

from pydantic_ai import Agent

from agentic_patterns.core.agents import get_agent
from agentic_patterns.core.config.config import PROMPTS_DIR
from agentic_patterns.core.prompt import load_prompt
from agentic_patterns.tools.sql import get_all_tools


def create_agent() -> Agent:
    """Create an NL2SQL agent with tools connected directly."""
    prompt = load_prompt(PROMPTS_DIR / "a2a" / "nl2sql" / "system_prompt.md")
    return get_agent(tools=get_all_tools(), system_prompt=prompt)
