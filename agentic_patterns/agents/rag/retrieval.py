"""LLM-based query expansion for improved retrieval recall."""

from pydantic import BaseModel
from pydantic_ai import Agent

from agentic_patterns.core.agents import get_agent
from agentic_patterns.core.config.config import PROMPTS_DIR
from agentic_patterns.core.prompt import load_prompt


class _QueryVariants(BaseModel):
    queries: list[str]


async def expand_query(query: str, agent: Agent | None = None) -> list[str]:
    """Reformulate a query into multiple variants for broader retrieval coverage."""
    if agent is None:
        agent = get_agent(output_type=_QueryVariants)

    prompt_path = PROMPTS_DIR / "rag" / "expand_query.md"
    prompt = load_prompt(prompt_path, query=query)
    result = await agent.run(prompt)
    return result.output.queries
