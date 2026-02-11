"""SQL agent -- local equivalent of the A2A nl2sql server."""

from pydantic_ai import Agent

from agentic_patterns.core.agents import AgentSpec, get_agent
from agentic_patterns.core.config.config import PROMPTS_DIR
from agentic_patterns.core.prompt import load_prompt
from agentic_patterns.tools import csv, file, sql

DESCRIPTION = (
    "Delegates SQL database queries, schema inspection, and data source questions."
)


def create_agent() -> Agent:
    """Create an SQL agent with tools connected directly."""
    spec = get_spec()
    return get_agent(tools=spec.tools, system_prompt=spec.system_prompt)


def get_spec() -> AgentSpec:
    """Return an AgentSpec for the SQL agent."""
    prompt = load_prompt(PROMPTS_DIR / "a2a" / "nl2sql" / "system_prompt.md")
    tools = file.get_all_tools() + csv.get_all_tools() + sql.get_all_tools()
    return AgentSpec(
        name="sql_analyst", description=DESCRIPTION, system_prompt=prompt, tools=tools
    )
