"""Agent tools for CSV operations -- wraps CsvConnector."""

from agentic_patterns.core.connectors.csv import CsvConnector
from agentic_patterns.core.tools.permissions import ToolPermission, tool_permission


def get_all_tools() -> list:
    """Get all CSV operation tools."""
    connector = CsvConnector()

    @tool_permission(ToolPermission.READ)
    def csv_headers(path: str) -> str:
        """Get column names from a CSV file."""
        return connector.headers(path)

    @tool_permission(ToolPermission.READ)
    def csv_head(path: str, n: int = 10) -> str:
        """Read the first N rows of a CSV file."""
        return connector.head(path, n)

    @tool_permission(ToolPermission.READ)
    def csv_tail(path: str, n: int = 10) -> str:
        """Read the last N rows of a CSV file."""
        return connector.tail(path, n)

    @tool_permission(ToolPermission.READ)
    def csv_read_row(path: str, row_number: int) -> str:
        """Read a single row by its 1-indexed row number."""
        return connector.read_row(path, row_number)

    @tool_permission(ToolPermission.READ)
    def csv_find_rows(path: str, column: str | int, value: str, limit: int = 10) -> str:
        """Find rows where a column matches a value."""
        return connector.find_rows(path, column, value, limit)

    @tool_permission(ToolPermission.WRITE)
    def csv_append(path: str, values: dict[str, str] | list[str]) -> str:
        """Append a new row. Pass a {column: value} dict or a list of values in column order."""
        return connector.append(path, values)

    @tool_permission(ToolPermission.WRITE)
    def csv_update_cell(
        path: str, row_number: int, column: str | int, value: str
    ) -> str:
        """Update a single cell by row number (1-indexed) and column name or index."""
        return connector.update_cell(path, row_number, column, value)

    @tool_permission(ToolPermission.WRITE)
    def csv_update_row(
        path: str, key_column: str | int, key_value: str, updates: dict[str, str]
    ) -> str:
        """Update columns in all rows where key_column equals key_value."""
        return connector.update_row(path, key_column, key_value, updates)

    @tool_permission(ToolPermission.WRITE)
    def csv_delete_rows(path: str, column: str | int, value: str) -> str:
        """Delete all rows where a column matches a value."""
        return connector.delete_rows(path, column, value)

    return [
        csv_headers,
        csv_head,
        csv_tail,
        csv_read_row,
        csv_find_rows,
        csv_append,
        csv_update_cell,
        csv_update_row,
        csv_delete_rows,
    ]
