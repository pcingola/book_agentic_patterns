"""Data Analysis sub-agent -- local equivalent of the A2A data_analysis server."""

from pydantic_ai import Agent

from agentic_patterns.core.agents import get_agent
from agentic_patterns.core.config.config import PROMPTS_DIR
from agentic_patterns.core.prompt import load_prompt
from agentic_patterns.tools.data_analysis import get_all_tools


def create_agent() -> Agent:
    """Create a data analysis agent with tools connected directly."""
    prompt = load_prompt(PROMPTS_DIR / "a2a" / "data_analysis" / "system_prompt.md")
    return get_agent(tools=get_all_tools(), system_prompt=prompt)
