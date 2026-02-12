"""Agent tools for SQL database operations -- wraps SqlConnector."""

from pydantic_ai import ModelRetry

from agentic_patterns.core.connectors.sql.connector import SqlConnector
from agentic_patterns.core.connectors.sql.query_validation import QueryValidationError
from agentic_patterns.core.tools.permissions import ToolPermission, tool_permission

_RETRYABLE = (QueryValidationError, ValueError, KeyError)


def get_all_tools() -> list:
    """Get all SQL operation tools (not bound to a specific database)."""
    connector = SqlConnector()

    @tool_permission(ToolPermission.CONNECT)
    async def sql_list_databases() -> str:
        """List all available databases with descriptions and table counts."""
        try:
            return await connector.list_databases()
        except _RETRYABLE as e:
            raise ModelRetry(str(e)) from e

    @tool_permission(ToolPermission.CONNECT)
    async def sql_list_tables(db_id: str) -> str:
        """List all tables in a database with descriptions."""
        try:
            return await connector.list_tables(db_id)
        except _RETRYABLE as e:
            raise ModelRetry(str(e)) from e

    @tool_permission(ToolPermission.READ)
    async def sql_show_schema(db_id: str) -> str:
        """Show full database schema (CREATE TABLE statements and example queries)."""
        try:
            return await connector.show_schema(db_id)
        except _RETRYABLE as e:
            raise ModelRetry(str(e)) from e

    @tool_permission(ToolPermission.READ)
    async def sql_show_table_details(db_id: str, table_name: str) -> str:
        """Show detailed schema for a specific table."""
        try:
            return await connector.show_table_details(db_id, table_name)
        except _RETRYABLE as e:
            raise ModelRetry(str(e)) from e

    @tool_permission(ToolPermission.READ)
    async def sql_execute(
        db_id: str,
        query: str,
        output_file: str | None = None,
        nl_query: str | None = None,
    ) -> str:
        """Execute a SELECT query. Large results are saved to CSV automatically."""
        try:
            return await connector.execute_sql(db_id, query, output_file, nl_query)
        except _RETRYABLE as e:
            raise ModelRetry(str(e)) from e

    @tool_permission(ToolPermission.READ)
    async def sql_get_row_by_id(
        db_id: str, table_name: str, row_id: str, fetch_related: bool = False
    ) -> str:
        """Fetch a row by primary key, optionally including related rows via foreign keys."""
        try:
            return await connector.get_row_by_id(
                db_id, table_name, row_id, fetch_related
            )
        except _RETRYABLE as e:
            raise ModelRetry(str(e)) from e

    return [
        sql_list_databases,
        sql_list_tables,
        sql_show_schema,
        sql_show_table_details,
        sql_execute,
        sql_get_row_by_id,
    ]
