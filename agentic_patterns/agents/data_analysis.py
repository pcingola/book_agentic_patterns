"""Data Analysis agent -- local equivalent of the A2A data_analysis server."""

from pydantic_ai import Agent

from agentic_patterns.core.agents import AgentSpec, get_agent
from agentic_patterns.core.config.config import PROMPTS_DIR
from agentic_patterns.core.prompt import load_prompt
from agentic_patterns.tools.data_analysis import get_all_tools

DESCRIPTION = "Delegates data analysis tasks (EDA, statistics, transformations, ML) on DataFrames."


def create_agent() -> Agent:
    """Create a data analysis agent with tools connected directly."""
    spec = get_spec()
    return get_agent(tools=spec.tools, system_prompt=spec.system_prompt)


def get_spec() -> AgentSpec:
    """Return an AgentSpec for the data analysis agent."""
    prompt = load_prompt(PROMPTS_DIR / "a2a" / "data_analysis" / "system_prompt.md")
    return AgentSpec(name="data_analyst", description=DESCRIPTION, system_prompt=prompt, tools=get_all_tools())
