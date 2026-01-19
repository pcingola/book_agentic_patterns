"""
A simple example of using FastMCP to create a server with only one tool.
"""

from mcp.server.fastmcp import FastMCP

# Create an MCP server
mcp = FastMCP("Demo")

# Add tool
@mcp.tool()
def add(a: int, b: int) -> int:
    """ Add two numbers """
    return a + b
