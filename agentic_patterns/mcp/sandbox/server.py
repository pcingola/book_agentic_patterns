"""MCP Sandbox server for Docker-based code execution with network isolation.

Run with: fastmcp run agentic_patterns/mcp/sandbox/server.py:mcp --transport http
"""

from agentic_patterns.core.mcp import create_mcp_server
from agentic_patterns.mcp.sandbox.tools import register_tools

mcp = create_mcp_server(
    "sandbox",
    instructions=(
        "A sandbox server for executing shell commands in Docker containers. "
        "Each user/session gets an isolated container with its own workspace. "
        "Sessions with private data automatically run with network isolation."
    ),
)
register_tools(mcp)
