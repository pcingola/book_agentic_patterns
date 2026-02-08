"""MCP server for file operations using connectors (text, CSV, JSON).

Run with: fastmcp run agentic_patterns/mcp/file_ops/server.py:mcp --transport http
"""

from agentic_patterns.core.mcp import create_mcp_server
from agentic_patterns.mcp.file_ops.tools import register_tools

mcp = create_mcp_server(
    "file_ops",
    instructions=(
        "File operations server for reading and writing files in the workspace. "
        "Supports text/code files, CSV files, and JSON files. "
        "All paths must start with /workspace/. "
        "Use file_* tools for generic text/code files, csv_* tools for CSV files, "
        "and json_* tools for JSON files."
    ),
)
register_tools(mcp)
