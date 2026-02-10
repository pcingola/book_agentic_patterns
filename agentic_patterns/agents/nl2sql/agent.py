"""Natural language to SQL agent."""

from pydantic_ai import Agent

from agentic_patterns.core.agents import get_agent
from agentic_patterns.agents.nl2sql.prompts import get_instructions, get_system_prompt
from agentic_patterns.core.connectors.sql.db_infos import DbInfos
from agentic_patterns.tools.nl2sql import get_all_tools


def create_agent(db_id: str) -> Agent:
    """Create a natural language to SQL agent for a specific database."""
    db_infos = DbInfos.get()
    db_info = db_infos.get_db_info(db_id)
    system_prompt = get_system_prompt()
    instructions = get_instructions(db_info)
    tools = get_all_tools(db_id)
    return get_agent(
        system_prompt=system_prompt, instructions=instructions, tools=tools
    )
