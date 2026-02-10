"""MCP SQL tools wrapping SqlConnector.

Connector methods are async and raise standard Python exceptions. The _call()
wrapper converts them to ToolRetryError (user-correctable) or ToolFatalError
(infrastructure).
"""

from fastmcp import Context, FastMCP

from agentic_patterns.core.connectors.sql.connector import SqlConnector
from agentic_patterns.core.connectors.sql.query_validation import QueryValidationError
from agentic_patterns.core.mcp import ToolFatalError, ToolRetryError
from agentic_patterns.core.tools.permissions import ToolPermission, tool_permission

_sql = SqlConnector()

_RETRYABLE = (QueryValidationError, ValueError, KeyError)


async def _call(coro) -> str:
    """Await a connector coroutine, converting exceptions to MCP errors."""
    try:
        return await coro
    except _RETRYABLE as e:
        raise ToolRetryError(str(e)) from e
    except OSError as e:
        raise ToolFatalError(str(e)) from e


def register_tools(mcp: FastMCP) -> None:
    """Register all SQL tools on the given MCP server instance."""

    @mcp.tool()
    @tool_permission(ToolPermission.CONNECT)
    async def sql_list_databases(ctx: Context) -> str:
        """List all available databases with descriptions and table counts."""
        await ctx.info("sql_list_databases")
        return await _call(_sql.list_databases())

    @mcp.tool()
    @tool_permission(ToolPermission.CONNECT)
    async def sql_list_tables(db_id: str, ctx: Context) -> str:
        """List all tables in a database with descriptions."""
        await ctx.info(f"sql_list_tables: {db_id}")
        return await _call(_sql.list_tables(db_id))

    @mcp.tool()
    @tool_permission(ToolPermission.READ)
    async def sql_show_schema(db_id: str, ctx: Context) -> str:
        """Show full database schema (CREATE TABLE statements and example queries)."""
        await ctx.info(f"sql_show_schema: {db_id}")
        return await _call(_sql.show_schema(db_id))

    @mcp.tool()
    @tool_permission(ToolPermission.READ)
    async def sql_show_table_details(db_id: str, table_name: str, ctx: Context) -> str:
        """Show detailed schema for a specific table."""
        await ctx.info(f"sql_show_table_details: {db_id}/{table_name}")
        return await _call(_sql.show_table_details(db_id, table_name))

    @mcp.tool()
    @tool_permission(ToolPermission.READ)
    async def sql_execute(
        db_id: str,
        query: str,
        output_file: str | None = None,
        nl_query: str | None = None,
        ctx: Context = None,
    ) -> str:
        """Execute a SELECT query. Large results are saved to CSV automatically."""
        await ctx.info(f"sql_execute: {db_id}")
        return await _call(_sql.execute_sql(db_id, query, output_file, nl_query))

    @mcp.tool()
    @tool_permission(ToolPermission.READ)
    async def sql_get_row_by_id(
        db_id: str,
        table_name: str,
        row_id: str,
        fetch_related: bool = False,
        ctx: Context = None,
    ) -> str:
        """Fetch a row by primary key, optionally including related rows via foreign keys."""
        await ctx.info(f"sql_get_row_by_id: {db_id}/{table_name}/{row_id}")
        return await _call(_sql.get_row_by_id(db_id, table_name, row_id, fetch_related))
