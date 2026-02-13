"""OpenAPI A2A server -- explores and calls REST APIs via OpenAPI specs.

Connects to the OpenAPI MCP server, which provides tools for listing APIs,
inspecting endpoints, and making HTTP requests.

Run with: uvicorn agentic_patterns.a2a.openapi.server:app --port 8203
"""

from agentic_patterns.core.a2a import AuthSessionMiddleware, mcp_to_skills_sync
from agentic_patterns.core.agents import get_agent
from agentic_patterns.core.config.config import PROMPTS_DIR
from agentic_patterns.core.mcp import get_mcp_client
from agentic_patterns.core.prompt import load_prompt

system_prompt = load_prompt(PROMPTS_DIR / "a2a" / "openapi" / "system_prompt.md")

mcp_client = get_mcp_client("openapi")
skills = mcp_to_skills_sync("openapi")

agent = get_agent(toolsets=[mcp_client], instructions=system_prompt)
app = agent.to_a2a(
    name="ApiSpecialist",
    description="Explores and calls REST API endpoints across configured OpenAPI services.",
    skills=skills,
)
app.add_middleware(AuthSessionMiddleware)
