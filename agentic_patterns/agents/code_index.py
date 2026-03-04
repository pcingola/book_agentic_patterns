"""Code Indexing and Search agent -- structure-aware code search using tree-sitter and vector embeddings."""

from pydantic_ai import Agent

from agentic_patterns.core.agents import AgentSpec, get_agent
from agentic_patterns.core.config.config import PROMPTS_DIR
from agentic_patterns.core.prompt import load_prompt
from agentic_patterns.tools import code_index

DESCRIPTION = "Indexes code repositories with syntax-aware chunking and provides semantic and lexical code search."


def create_agent() -> Agent:
    """Create a code index agent with tools connected directly."""
    spec = get_spec()
    return get_agent(tools=spec.tools, system_prompt=spec.system_prompt)


def get_spec() -> AgentSpec:
    """Return an AgentSpec for the code index agent."""
    prompt = load_prompt(PROMPTS_DIR / "code_index" / "system_prompt.md")
    tools = code_index.get_all_tools()
    return AgentSpec(
        name="code_index", description=DESCRIPTION, system_prompt=prompt, tools=tools
    )
