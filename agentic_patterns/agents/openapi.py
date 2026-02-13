"""OpenAPI agent -- local equivalent of the A2A openapi server."""

from pydantic_ai import Agent

from agentic_patterns.core.agents import AgentSpec, get_agent
from agentic_patterns.core.config.config import PROMPTS_DIR
from agentic_patterns.core.prompt import load_prompt
from agentic_patterns.tools import openapi

DESCRIPTION = (
    "Delegates API exploration and execution tasks across configured REST APIs."
)


def create_agent() -> Agent:
    """Create an OpenAPI agent with tools connected directly."""
    spec = get_spec()
    return get_agent(tools=spec.tools, system_prompt=spec.system_prompt)


def get_spec() -> AgentSpec:
    """Return an AgentSpec for the OpenAPI agent."""
    prompt = load_prompt(PROMPTS_DIR / "a2a" / "openapi" / "system_prompt.md")
    return AgentSpec(
        name="api_specialist",
        description=DESCRIPTION,
        system_prompt=prompt,
        tools=openapi.get_all_tools(),
    )
