"""MCP Todo server for managing hierarchical task lists per user/session.

Run with: fastmcp run agentic_patterns/mcp/todo/server.py:mcp --transport http
"""

from agentic_patterns.core.mcp import create_mcp_server
from agentic_patterns.mcp.todo.tools import register_tools

mcp = create_mcp_server(
    "todo",
    instructions=(
        "A 'to do' server for managing todo lists. "
        "The todo lists are shown as Markdown checklists. "
        "Item IDs are hierarchical (e.g. '1.3.2' means item 2 under item 3 under item 1). "
        "All todo lists are private to the user/session."
    ),
)
register_tools(mcp)
