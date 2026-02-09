"""Data visualization MCP server.

Provides plot and chart creation from CSV files using matplotlib and seaborn.

Run with: fastmcp run agentic_patterns/mcp/data_viz/server.py:mcp --transport http
"""

from agentic_patterns.core.mcp import create_mcp_server
from agentic_patterns.mcp.data_viz.tools import register_tools

mcp = create_mcp_server(
    "data_viz",
    instructions=(
        "Data visualization server providing line, bar, scatter, area, histogram, box, violin, "
        "kde, count, pie, heatmap, and pair plots from CSV files. "
        "All input files must be workspace paths (e.g. /workspace/data.csv). "
        "Output images are saved as PNG by default."
    ),
)
register_tools(mcp)
