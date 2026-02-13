"""MCP server for OpenAPI operations.

Run with: fastmcp run agentic_patterns/mcp/openapi/server.py:mcp --transport http
"""

from agentic_patterns.core.mcp import create_mcp_server
from agentic_patterns.mcp.openapi.tools import register_tools

mcp = create_mcp_server(
    "openapi",
    instructions=(
        "OpenAPI operations server. "
        "Provides tools to list APIs, inspect endpoints, show summaries, "
        "view endpoint details, and call REST API endpoints."
    ),
)
register_tools(mcp)
