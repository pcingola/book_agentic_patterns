"""MCP REPL server for stateful notebook-style Python execution.

Run with: fastmcp run agentic_patterns/mcp/repl/server.py:mcp --transport http
"""

from agentic_patterns.core.mcp import create_mcp_server
from agentic_patterns.mcp.repl.tools import register_tools

mcp = create_mcp_server(
    "repl",
    instructions=(
        "A REPL server for stateful, notebook-style Python execution. "
        "Cells share a namespace across executions -- variables, imports, and function definitions persist. "
        "Cell numbers are 0-based. "
        "All notebooks are private to the user/session."
    ),
)
register_tools(mcp)
