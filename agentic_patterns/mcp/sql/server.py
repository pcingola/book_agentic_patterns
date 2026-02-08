"""MCP server for SQL database operations.

Run with: fastmcp run agentic_patterns/mcp/sql/server.py:mcp --transport http
"""

from agentic_patterns.core.mcp import create_mcp_server
from agentic_patterns.mcp.sql.tools import register_tools

mcp = create_mcp_server(
    "sql",
    instructions=(
        "SQL database operations server. "
        "Provides tools to list databases, inspect schemas, execute SELECT queries, "
        "and fetch rows by primary key. All queries are read-only."
    ),
)
register_tools(mcp)
