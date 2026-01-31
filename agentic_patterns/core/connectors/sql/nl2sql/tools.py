"""Agent tools for NL2SQL -- wraps operations with db_id bound via closure."""

from agentic_patterns.core.connectors.sql.operations import db_execute_sql_op, db_get_row_by_id_op


def get_all_tools(db_id: str) -> list:
    """Get all agent tools bound to a specific database."""

    async def db_execute_sql_tool(query: str, output_file: str, nl_query: str | None = None) -> str:
        """Execute SQL query against the database and return results.

        Args:
            query: SQL query to execute
            output_file: Save results to this CSV file
            nl_query: Natural language query description (optional)
        """
        return await db_execute_sql_op(db_id, query, output_file, nl_query)

    async def db_get_row_by_id_tool(table_name: str, row_id: str, fetch_related: bool = False) -> dict:
        """Fetch a row by ID from the database.

        Args:
            table_name: Name of table
            row_id: ID value
            fetch_related: Whether to fetch data from tables referenced via foreign keys
        """
        return await db_get_row_by_id_op(db_id=db_id, table_name=table_name, row_id=row_id, fetch_related=fetch_related)

    return [db_execute_sql_tool, db_get_row_by_id_tool]
