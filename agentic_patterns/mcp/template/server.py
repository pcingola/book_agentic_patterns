"""Template MCP server demonstrating production requirements.

Uses create_mcp_server() which pre-wires AuthSessionMiddleware for JWT-based
identity propagation. Tools are registered from a separate module.

Run with: fastmcp run agentic_patterns/mcp/template/server.py:mcp --transport http
"""

from agentic_patterns.core.mcp import create_mcp_server
from agentic_patterns.mcp.template.tools import register_tools

mcp = create_mcp_server(
    "template",
    instructions="Template MCP server with workspace, permissions, and compliance.",
)
register_tools(mcp)
