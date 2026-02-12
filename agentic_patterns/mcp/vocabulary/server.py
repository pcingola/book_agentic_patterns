"""MCP Vocabulary server for term resolution across controlled vocabularies.

Run with: fastmcp run agentic_patterns/mcp/vocabulary/server.py:mcp --transport http
"""

from agentic_patterns.core.mcp import create_mcp_server
from agentic_patterns.mcp.vocabulary.tools import register_tools

mcp = create_mcp_server(
    "vocabulary",
    instructions=(
        "Vocabulary and ontology server for resolving terms, validating codes, "
        "browsing hierarchies, and exploring relationships across controlled "
        "vocabularies (biomedical, scientific, etc.)."
    ),
)
register_tools(mcp)
