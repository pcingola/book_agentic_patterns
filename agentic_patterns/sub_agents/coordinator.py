"""Coordinator agent that delegates to local sub-agents."""

from pydantic_ai import Agent, RunContext

from agentic_patterns.core.agents import get_agent, run_agent
from agentic_patterns.sub_agents.data_analysis import create_agent as create_data_analysis_agent
from agentic_patterns.sub_agents.nl2sql import create_agent as create_nl2sql_agent

SYSTEM_PROMPT = """You coordinate tasks between specialized agents.

Available agents:

- ask_data_analyst: Delegates data analysis tasks (EDA, statistics, transformations, ML) on DataFrames. Use this when the user wants to analyze, transform, or model tabular data files.

- ask_sql_analyst: Delegates SQL database queries. Use this when the user wants to query databases, inspect schemas, or answer questions from SQL data sources.

Break the user's request into sub-tasks, delegate each to the appropriate agent, and synthesize their responses into a final answer."""


async def ask_data_analyst(ctx: RunContext, prompt: str) -> str:
    """Delegate a data analysis task to the Data Analysis sub-agent."""
    agent = create_data_analysis_agent()
    agent_run, _ = await run_agent(agent, prompt)
    ctx.usage.incr(agent_run.result.usage())
    return agent_run.result.output


async def ask_sql_analyst(ctx: RunContext, prompt: str) -> str:
    """Delegate a SQL query task to the NL2SQL sub-agent."""
    agent = create_nl2sql_agent()
    agent_run, _ = await run_agent(agent, prompt)
    ctx.usage.incr(agent_run.result.usage())
    return agent_run.result.output


def create_coordinator() -> Agent:
    """Create a coordinator agent with delegation tools for both sub-agents."""
    return get_agent(
        system_prompt=SYSTEM_PROMPT,
        tools=[ask_data_analyst, ask_sql_analyst],
    )
