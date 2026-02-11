"""Data Analysis agent -- local equivalent of the A2A data_analysis server."""

from pydantic_ai import Agent

from agentic_patterns.core.agents import AgentSpec, get_agent
from agentic_patterns.core.config.config import PROMPTS_DIR
from agentic_patterns.core.prompt import load_prompt
from agentic_patterns.tools import csv, data_analysis, data_viz, file, json, repl

DESCRIPTION = "Delegates data analysis and visualization tasks (EDA, statistics, transformations, ML, charts) on DataFrames."


def create_agent() -> Agent:
    """Create a data analysis agent with tools connected directly."""
    spec = get_spec()
    return get_agent(tools=spec.tools, system_prompt=spec.system_prompt)


def get_spec() -> AgentSpec:
    """Return an AgentSpec for the data analysis agent."""
    prompt = load_prompt(PROMPTS_DIR / "a2a" / "data_analysis" / "system_prompt.md")
    tools = (
        file.get_all_tools()
        + csv.get_all_tools()
        + json.get_all_tools()
        + data_analysis.get_all_tools()
        + data_viz.get_all_tools()
        + repl.get_all_tools()
    )
    return AgentSpec(
        name="data_analyst", description=DESCRIPTION, system_prompt=prompt, tools=tools
    )
