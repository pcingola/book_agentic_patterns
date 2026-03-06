"""Coordinator agent that delegates to local sub-agents."""

from agentic_patterns.core.agents import AgentSpec, OrchestratorAgent
from agentic_patterns.core.prompt import load_prompt
from agentic_patterns.agents.data_analysis import get_spec as get_data_analysis_spec
from agentic_patterns.agents.sql import get_spec as get_sql_spec
from agentic_patterns.agents.vocabulary import get_spec as get_vocabulary_spec


def create_agent(tools: list | None = None) -> OrchestratorAgent:
    """Create a coordinator agent that delegates to sub-agents."""
    spec = AgentSpec(
        name="coordinator",
        system_prompt=load_prompt("the_complete_agent/agent_coordinator"),
        tools=tools or [],
        sub_agents=[
            get_data_analysis_spec(),
            get_sql_spec(),
            get_vocabulary_spec(),
        ],
    )
    return OrchestratorAgent(spec)
