"""NL2SQL A2A server -- answers data questions by querying SQL databases.

Connects to the SQL MCP server, which provides tools for database discovery,
schema inspection, and query execution across all configured databases.

Run with: uvicorn agentic_patterns.a2a.nl2sql.server:app --port 8002
"""

import asyncio

from agentic_patterns.core.a2a import AuthSessionMiddleware, mcp_to_skills
from agentic_patterns.core.agents import get_agent
from agentic_patterns.core.config.config import PROMPTS_DIR
from agentic_patterns.core.mcp import get_mcp_client
from agentic_patterns.core.prompt import load_prompt

system_prompt = load_prompt(PROMPTS_DIR / "a2a" / "nl2sql" / "system_prompt.md")

mcp_sql = get_mcp_client("sql")
skills = asyncio.run(mcp_to_skills("sql"))

agent = get_agent(toolsets=[mcp_sql], instructions=system_prompt)
app = agent.to_a2a(
    name="NL2SQL",
    description="Answers data questions by finding the right database, generating SQL, executing queries, and interpreting results.",
    skills=skills,
)
app.add_middleware(AuthSessionMiddleware)
