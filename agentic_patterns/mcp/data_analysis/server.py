"""Data analysis MCP server.

Provides DataFrame-based EDA, statistical tests, data transformations,
ML classification/regression, and feature importance analysis.

Run with: fastmcp run agentic_patterns/mcp/data_analysis/server.py:mcp --transport http
"""

from agentic_patterns.core.mcp import create_mcp_server
from agentic_patterns.mcp.data_analysis.tools import register_tools

mcp = create_mcp_server(
    "data_analysis",
    instructions=(
        "Data analysis server providing EDA, statistical tests, transformations, "
        "ML classification/regression, and feature importance analysis on DataFrame files."
    ),
)
register_tools(mcp)
