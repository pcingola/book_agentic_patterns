"""Template MCP server tools demonstrating requirements 1-8 and 11.

Each tool shows a different requirement:
- read_file: @tool_permission(READ), @context_result(), workspace path translation, ctx.info()
- write_file: @tool_permission(WRITE), workspace path translation, ctx.info()
- search_records: @tool_permission(READ), ToolRetryError for bad input, ctx.info()
- load_sensitive_dataset: @tool_permission(READ), PrivateData flagging, ToolFatalError, ctx.info()
"""

from fastmcp import Context, FastMCP

from agentic_patterns.core.compliance.private_data import DataSensitivity, PrivateData
from agentic_patterns.core.context.decorators import context_result
from agentic_patterns.core.mcp import ToolFatalError, ToolRetryError
from agentic_patterns.core.tools.permissions import ToolPermission, tool_permission
from agentic_patterns.core.workspace import read_from_workspace, write_to_workspace


def register_tools(mcp: FastMCP) -> None:
    """Register all tools on the given MCP server instance."""

    @mcp.tool()
    @tool_permission(ToolPermission.READ)
    @context_result()
    async def read_file(path: str, ctx: Context) -> str:
        """Read a file from the workspace. Path must start with /workspace/."""
        await ctx.info(f"Reading file: {path}")
        return read_from_workspace(path)

    @mcp.tool()
    @tool_permission(ToolPermission.WRITE)
    async def write_file(path: str, content: str, ctx: Context) -> str:
        """Write content to a file in the workspace. Path must start with /workspace/."""
        await ctx.info(f"Writing {len(content)} bytes to {path}")
        write_to_workspace(path, content)
        return f"Written {len(content)} bytes to {path}"

    @mcp.tool()
    @tool_permission(ToolPermission.READ)
    async def search_records(query: str, ctx: Context) -> str:
        """Search records by keyword. Demonstrates retryable error for bad input."""
        await ctx.info(f"search_records called with query={query!r}")
        if not query.strip():
            await ctx.warning("Empty query rejected -- raising ToolRetryError (client sees ModelRetry)")
            raise ToolRetryError("Query cannot be empty -- provide a search term")
        # Placeholder: a real implementation would query a database or index
        return f"Found 3 records matching '{query}': [record_1, record_2, record_3]"

    @mcp.tool()
    @tool_permission(ToolPermission.READ)
    async def load_sensitive_dataset(dataset_name: str, ctx: Context) -> str:
        """Load a sensitive dataset and flag the session as containing private data.

        Demonstrates PrivateData compliance flagging and ToolFatalError for
        infrastructure failures.
        """
        if not dataset_name.strip():
            raise ToolRetryError("Dataset name cannot be empty")

        # Flag the session as containing private data
        try:
            pd = PrivateData()
            pd.add_private_dataset(dataset_name, DataSensitivity.CONFIDENTIAL)
        except Exception as e:
            raise ToolFatalError(f"Compliance system unavailable: {e}") from e

        await ctx.warning(f"Session flagged as containing private data (dataset: {dataset_name}, sensitivity: CONFIDENTIAL)")
        # Placeholder: a real implementation would load from a data source
        return f"Loaded dataset '{dataset_name}' (3 rows). Session marked as containing private data."
