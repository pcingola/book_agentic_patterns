"""MCP Todo server for managing hierarchical task lists per user/session.

Run with: fastmcp run agentic_patterns/mcp/todo/server.py:mcp --transport http
"""

from agentic_patterns.core.mcp import create_mcp_server
from agentic_patterns.mcp.todo.tools import register_tools

mcp = create_mcp_server(
    "todo",
    instructions=(
        "A 'to do' server for managing task lists (i.e. 'to do' lists). "
        "The 'to do' lists are shown as Markdown checklists. "
        "Task IDs are hierarchical (e.g. '1.3.2' means task 2 under task 3 under task 1). "
        "All task lists are private to the user/session."
    ),
)
register_tools(mcp)
