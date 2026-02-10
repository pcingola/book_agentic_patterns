"""Agent tools for file operations -- wraps FileConnector."""

from agentic_patterns.core.connectors.file import FileConnector
from agentic_patterns.core.tools.permissions import ToolPermission, tool_permission


def get_all_tools() -> list:
    """Get all file operation tools."""
    connector = FileConnector()

    @tool_permission(ToolPermission.READ)
    def file_read(path: str) -> str:
        """Read entire file contents. Large files are automatically truncated."""
        return connector.read(path)

    @tool_permission(ToolPermission.READ)
    def file_head(path: str, n: int = 10) -> str:
        """Read the first N lines of a file."""
        return connector.head(path, n)

    @tool_permission(ToolPermission.READ)
    def file_tail(path: str, n: int = 10) -> str:
        """Read the last N lines of a file."""
        return connector.tail(path, n)

    @tool_permission(ToolPermission.READ)
    def file_find(path: str, query: str) -> str:
        """Search file for a string, returning matching lines with line numbers."""
        return connector.find(path, query)

    @tool_permission(ToolPermission.READ)
    def file_list(path: str, pattern: str = "*") -> str:
        """List files in a directory matching a glob pattern."""
        return connector.list(path, pattern)

    @tool_permission(ToolPermission.WRITE)
    def file_write(path: str, content: str) -> str:
        """Write or overwrite a file. Creates parent directories if needed."""
        return connector.write(path, content)

    @tool_permission(ToolPermission.WRITE)
    def file_append(path: str, content: str) -> str:
        """Append content to the end of an existing file."""
        return connector.append(path, content)

    @tool_permission(ToolPermission.WRITE)
    def file_edit(path: str, start_line: int, end_line: int, new_content: str) -> str:
        """Replace lines start_line to end_line (1-indexed, inclusive) with new_content."""
        return connector.edit(path, start_line, end_line, new_content)

    @tool_permission(ToolPermission.WRITE)
    def file_delete(path: str) -> str:
        """Delete a file."""
        return connector.delete(path)

    return [file_read, file_head, file_tail, file_find, file_list, file_write, file_append, file_edit, file_delete]
