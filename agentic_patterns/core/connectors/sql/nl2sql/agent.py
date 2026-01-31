"""Natural language to SQL agent."""

from typing import Any

from pydantic_ai import Agent

from agentic_patterns.core.agents.agents import get_agent, run_agent
from agentic_patterns.core.connectors.sql.db_infos import DbInfos
from agentic_patterns.core.connectors.sql.nl2sql.prompts import get_instructions, get_system_prompt
from agentic_patterns.core.connectors.sql.nl2sql.tools import get_all_tools


def create_nl2sql_agent(db_id: str) -> Agent:
    """Create a natural language to SQL agent for a specific database."""
    db_infos = DbInfos.get()
    db_info = db_infos.get_db_info(db_id)
    system_prompt = get_system_prompt()
    instructions = get_instructions(db_info)
    tools = get_all_tools(db_id)
    return get_agent(system_prompt=system_prompt, instructions=instructions, tools=tools)


async def run_nl2sql_query(db_id: str, query: str, verbose: bool = False) -> tuple[Any, list]:
    """Run a natural language query against a specific database."""
    agent = create_nl2sql_agent(db_id=db_id)
    return await run_agent(agent, query, verbose=verbose)
