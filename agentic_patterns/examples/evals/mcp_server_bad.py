"""MCP server with poorly defined tools for doctor analysis."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("BadServer")


@mcp.tool()
def do_thing(x):
    """Does thing."""
    return x


@mcp.tool()
def proc(a, b):
    """Process."""
    return a + b
