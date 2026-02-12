"""Vocabulary A2A server -- resolves terms across controlled vocabularies.

Connects to the Vocabulary MCP server, which provides tools for listing
vocabularies, looking up terms, searching, validating codes, and navigating
hierarchies.

Run with: uvicorn agentic_patterns.a2a.vocabulary.server:app --port 8202
"""

from agentic_patterns.core.a2a import AuthSessionMiddleware, mcp_to_skills_sync
from agentic_patterns.core.agents import get_agent
from agentic_patterns.core.config.config import PROMPTS_DIR
from agentic_patterns.core.mcp import get_mcp_client
from agentic_patterns.core.prompt import load_prompt

system_prompt = load_prompt(PROMPTS_DIR / "a2a" / "vocabulary" / "system_prompt.md")

mcp_client = get_mcp_client("vocabulary")
skills = mcp_to_skills_sync("vocabulary")

agent = get_agent(toolsets=[mcp_client], instructions=system_prompt)
app = agent.to_a2a(
    name="VocabularyExpert",
    description="Resolves terms, validates codes, navigates hierarchies, and explores relationships across controlled vocabularies and ontologies.",
    skills=skills,
)
app.add_middleware(AuthSessionMiddleware)
