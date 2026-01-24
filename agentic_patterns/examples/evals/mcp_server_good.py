"""MCP server with well-defined tools for doctor analysis."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("CalculatorServer")


@mcp.tool()
def add_numbers(a: int, b: int) -> int:
    """Add two integers and return the sum."""
    return a + b


@mcp.tool()
def multiply_numbers(a: float, b: float) -> float:
    """Multiply two numbers and return the product."""
    return a * b
