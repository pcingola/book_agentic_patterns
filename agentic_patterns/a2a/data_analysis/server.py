"""Data Analysis A2A server.

Exposes a data analysis agent with DataFrame-based EDA, statistical tests,
transformations, ML classification/regression, and feature importance via
the Data Analysis MCP server.

Run with: uvicorn agentic_patterns.a2a.data_analysis.server:app --port 8003
"""

import asyncio

from agentic_patterns.core.a2a import AuthSessionMiddleware, mcp_to_skills
from agentic_patterns.core.agents import get_agent
from agentic_patterns.core.config.config import PROMPTS_DIR
from agentic_patterns.core.mcp import get_mcp_client
from agentic_patterns.core.prompt import load_prompt

MCP_NAME = "data_analysis"

system_prompt = load_prompt(PROMPTS_DIR / "a2a" / "data_analysis" / "system_prompt.md")
mcp_client = get_mcp_client(MCP_NAME)
skills = asyncio.run(mcp_to_skills(MCP_NAME))

agent = get_agent(toolsets=[mcp_client], instructions=system_prompt)
app = agent.to_a2a(
    name="DataAnalyst",
    description="An agent that performs DataFrame-based data analysis including EDA, statistical tests, transformations, and ML modeling.",
    skills=skills,
)
app.add_middleware(AuthSessionMiddleware)
