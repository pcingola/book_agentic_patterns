"""MCP server for format conversion (PDF/Word/PPT/Excel <-> Markdown/CSV/HTML).

Run with: fastmcp run agentic_patterns/mcp/format_conversion/server.py:mcp --transport http
"""

from agentic_patterns.core.mcp import create_mcp_server
from agentic_patterns.mcp.format_conversion.tools import register_tools

mcp = create_mcp_server(
    "format_conversion",
    instructions=(
        "Convert documents between formats for LLM consumption. "
        "Ingest: PDF, DOCX, PPTX, XLSX -> Markdown or CSV. "
        "Export: Markdown -> PDF, DOCX, HTML. "
        "All file paths must start with /workspace/."
    ),
)
register_tools(mcp)
