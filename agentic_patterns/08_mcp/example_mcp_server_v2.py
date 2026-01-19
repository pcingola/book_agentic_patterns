
"""
A simple example of using FastMCP to create a server with tools and resources
"""

from mcp.server.fastmcp import FastMCP

# Create an MCP server
mcp = FastMCP("Demo")

# Add an 'add' tool
@mcp.tool()
def add(a: int, b: int) -> int:
    """ Add two numbers """
    return a + b


# A resource shows a table's schema
@mcp.resource("postgres://{database}/{table_name}/schema")
def table_schema(database: str, table_name: str) -> str:
    """Get a table's schema"""
    return f"""
        -- This is the schema for the {table_name} table
        -- in the {database} database
        CREATE TABLE {table_name} (id INT, name VARCHAR(255));
        """

# A prompt
@mcp.prompt()
def hello_prompt(name: str) -> str:
    """Get a personalized greeting"""
    return f"Your name is {name} and you are a helpful assistant."

