"""Coordinator agent that delegates to local sub-agents."""

from pydantic_ai import RunContext

from agentic_patterns.core.agents import (
    get_model,
    run_agent,
    AgentSpec,
    OrchestratorAgent,
)
from agentic_patterns.agents.data_analysis import (
    create_agent as create_data_analysis_agent,
)
from agentic_patterns.agents.sql import create_agent as create_sql_agent

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
    """Delegate a SQL query task to the SQL sub-agent."""
    agent = create_sql_agent()
    agent_run, _ = await run_agent(agent, prompt)
    ctx.usage.incr(agent_run.result.usage())
    return agent_run.result.output


def create_coordinator() -> OrchestratorAgent:
    """Create a coordinator agent with delegation tools for both sub-agents."""
    spec = AgentSpec(
        name="coordinator",
        model=get_model(),
        system_prompt=SYSTEM_PROMPT,
        tools=[ask_data_analyst, ask_sql_analyst],
    )
    return OrchestratorAgent(spec)
