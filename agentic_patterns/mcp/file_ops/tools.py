"""MCP file operations tools wrapping FileConnector, CsvConnector, and JsonConnector.

Connectors raise standard Python exceptions. The _call() wrapper converts them
to ToolRetryError (user-correctable) or ToolFatalError (infrastructure).
"""

from fastmcp import Context, FastMCP

from agentic_patterns.core.connectors.csv import CsvConnector
from agentic_patterns.core.connectors.file import FileConnector
from agentic_patterns.core.connectors.json import JsonConnector
from agentic_patterns.core.mcp import ToolFatalError, ToolRetryError
from agentic_patterns.core.tools.permissions import ToolPermission, tool_permission
from agentic_patterns.core.workspace import WorkspaceError

_file = FileConnector()
_csv = CsvConnector()
_json = JsonConnector()

_RETRYABLE = (WorkspaceError, FileNotFoundError, IsADirectoryError, NotADirectoryError, ValueError, KeyError, TypeError, IndexError)


def _call(fn: callable, *args, **kwargs) -> str:
    """Call a connector method, converting exceptions to MCP errors."""
    try:
        return fn(*args, **kwargs)
    except _RETRYABLE as e:
        raise ToolRetryError(str(e)) from e
    except OSError as e:
        raise ToolFatalError(str(e)) from e


def register_tools(mcp: FastMCP) -> None:
    """Register all file operation tools on the given MCP server instance."""

    # -- Text / code file tools -------------------------------------------

    @mcp.tool()
    @tool_permission(ToolPermission.READ)
    async def file_read(path: str, ctx: Context) -> str:
        """Read a text/code file. Returns full content with automatic truncation for large files."""
        await ctx.info(f"file_read: {path}")
        return _call(_file.read, path)

    @mcp.tool()
    @tool_permission(ToolPermission.WRITE)
    async def file_write(path: str, content: str, ctx: Context) -> str:
        """Write or overwrite a text/code file. Creates parent directories if needed."""
        await ctx.info(f"file_write: {path} ({len(content)} bytes)")
        return _call(_file.write, path, content)

    @mcp.tool()
    @tool_permission(ToolPermission.WRITE)
    async def file_append(path: str, content: str, ctx: Context) -> str:
        """Append content to the end of a text file."""
        await ctx.info(f"file_append: {path}")
        return _call(_file.append, path, content)

    @mcp.tool()
    @tool_permission(ToolPermission.WRITE)
    async def file_delete(path: str, ctx: Context) -> str:
        """Delete a file."""
        await ctx.info(f"file_delete: {path}")
        return _call(_file.delete, path)

    @mcp.tool()
    @tool_permission(ToolPermission.WRITE)
    async def file_edit(path: str, start_line: int, end_line: int, new_content: str, ctx: Context) -> str:
        """Replace lines start_line to end_line (1-indexed, inclusive) with new_content."""
        await ctx.info(f"file_edit: {path} lines {start_line}-{end_line}")
        return _call(_file.edit, path, start_line, end_line, new_content)

    @mcp.tool()
    @tool_permission(ToolPermission.READ)
    async def file_find(path: str, query: str, ctx: Context) -> str:
        """Search file contents for a string, returning matching lines with line numbers."""
        await ctx.info(f"file_find: {path} query={query!r}")
        return _call(_file.find, path, query)

    @mcp.tool()
    @tool_permission(ToolPermission.READ)
    async def file_head(path: str, n: int = 10, ctx: Context = None) -> str:
        """Read the first N lines of a text file."""
        await ctx.info(f"file_head: {path} n={n}")
        return _call(_file.head, path, n)

    @mcp.tool()
    @tool_permission(ToolPermission.READ)
    async def file_tail(path: str, n: int = 10, ctx: Context = None) -> str:
        """Read the last N lines of a text file."""
        await ctx.info(f"file_tail: {path} n={n}")
        return _call(_file.tail, path, n)

    @mcp.tool()
    @tool_permission(ToolPermission.READ)
    async def file_list(path: str, pattern: str = "*", ctx: Context = None) -> str:
        """List files matching a glob pattern in a directory."""
        await ctx.info(f"file_list: {path} pattern={pattern!r}")
        return _call(_file.list, path, pattern)

    # -- CSV tools --------------------------------------------------------

    @mcp.tool()
    @tool_permission(ToolPermission.READ)
    async def csv_headers(path: str, ctx: Context) -> str:
        """Get column headers of a CSV file."""
        await ctx.info(f"csv_headers: {path}")
        return _call(_csv.headers, path)

    @mcp.tool()
    @tool_permission(ToolPermission.READ)
    async def csv_head(path: str, n: int = 10, ctx: Context = None) -> str:
        """Read first N rows of a CSV file with column/cell truncation."""
        await ctx.info(f"csv_head: {path} n={n}")
        return _call(_csv.head, path, n)

    @mcp.tool()
    @tool_permission(ToolPermission.READ)
    async def csv_tail(path: str, n: int = 10, ctx: Context = None) -> str:
        """Read last N rows of a CSV file with column/cell truncation."""
        await ctx.info(f"csv_tail: {path} n={n}")
        return _call(_csv.tail, path, n)

    @mcp.tool()
    @tool_permission(ToolPermission.READ)
    async def csv_read_row(path: str, row_number: int, ctx: Context) -> str:
        """Read a specific row by 1-indexed row number."""
        await ctx.info(f"csv_read_row: {path} row={row_number}")
        return _call(_csv.read_row, path, row_number)

    @mcp.tool()
    @tool_permission(ToolPermission.READ)
    async def csv_find_rows(path: str, column: str, value: str, limit: int = 10, ctx: Context = None) -> str:
        """Find rows where a column matches a value. Returns up to `limit` rows."""
        await ctx.info(f"csv_find_rows: {path} {column}={value!r} limit={limit}")
        return _call(_csv.find_rows, path, column, value, limit)

    @mcp.tool()
    @tool_permission(ToolPermission.WRITE)
    async def csv_append(path: str, values: dict[str, str] | list[str], ctx: Context = None) -> str:
        """Append a row to a CSV file. Pass a dict keyed by column name or a list of values."""
        await ctx.info(f"csv_append: {path}")
        return _call(_csv.append, path, values)

    @mcp.tool()
    @tool_permission(ToolPermission.WRITE)
    async def csv_delete_rows(path: str, column: str, value: str, ctx: Context = None) -> str:
        """Delete all rows where a column matches a value."""
        await ctx.info(f"csv_delete_rows: {path} {column}={value!r}")
        return _call(_csv.delete_rows, path, column, value)

    @mcp.tool()
    @tool_permission(ToolPermission.WRITE)
    async def csv_update_cell(path: str, row_number: int, column: str, value: str, ctx: Context = None) -> str:
        """Update a single cell in a CSV file."""
        await ctx.info(f"csv_update_cell: {path} row={row_number} col={column!r}")
        return _call(_csv.update_cell, path, row_number, column, value)

    @mcp.tool()
    @tool_permission(ToolPermission.WRITE)
    async def csv_update_row(path: str, key_column: str, key_value: str, updates: dict[str, str], ctx: Context = None) -> str:
        """Update all rows matching key_column=key_value with the given column updates."""
        await ctx.info(f"csv_update_row: {path} {key_column}={key_value!r}")
        return _call(_csv.update_row, path, key_column, key_value, updates)

    # -- JSON tools -------------------------------------------------------

    @mcp.tool()
    @tool_permission(ToolPermission.READ)
    async def json_get(path: str, json_path: str, ctx: Context) -> str:
        """Get a value or subtree from a JSON file using JSONPath (e.g. '$.users[0].name')."""
        await ctx.info(f"json_get: {path} {json_path}")
        return _call(_json.get, path, json_path)

    @mcp.tool()
    @tool_permission(ToolPermission.WRITE)
    async def json_set(path: str, json_path: str, value: str, ctx: Context) -> str:
        """Set a value at a JSONPath. Value must be valid JSON (e.g. '"hello"', '42', '{"a":1}')."""
        await ctx.info(f"json_set: {path} {json_path}")
        return _call(_json.set, path, json_path, value)

    @mcp.tool()
    @tool_permission(ToolPermission.READ)
    async def json_keys(path: str, json_path: str = "$", ctx: Context = None) -> str:
        """List keys with type info at a JSONPath."""
        await ctx.info(f"json_keys: {path} {json_path}")
        return _call(_json.keys, path, json_path)

    @mcp.tool()
    @tool_permission(ToolPermission.READ)
    async def json_schema(path: str, json_path: str = "$", max_depth: int = 4, ctx: Context = None) -> str:
        """Show JSON structure: keys, types, nesting depths, and array sizes."""
        await ctx.info(f"json_schema: {path} {json_path}")
        return _call(_json.schema, path, json_path, max_depth)

    @mcp.tool()
    @tool_permission(ToolPermission.READ)
    async def json_query(path: str, json_path: str, max_results: int = 20, ctx: Context = None) -> str:
        """Query JSON with extended JSONPath filters (e.g. '$.items[?(@.age > 30)]')."""
        await ctx.info(f"json_query: {path} {json_path}")
        return _call(_json.query, path, json_path, max_results)

    @mcp.tool()
    @tool_permission(ToolPermission.READ)
    async def json_head(path: str, json_path: str = "$", n: int = 10, ctx: Context = None) -> str:
        """Return the first N keys or array elements at a JSONPath."""
        await ctx.info(f"json_head: {path} {json_path} n={n}")
        return _call(_json.head, path, json_path, n)

    @mcp.tool()
    @tool_permission(ToolPermission.READ)
    async def json_tail(path: str, json_path: str = "$", n: int = 10, ctx: Context = None) -> str:
        """Return the last N keys or array elements at a JSONPath."""
        await ctx.info(f"json_tail: {path} {json_path} n={n}")
        return _call(_json.tail, path, json_path, n)

    @mcp.tool()
    @tool_permission(ToolPermission.READ)
    async def json_validate(path: str, ctx: Context) -> str:
        """Validate JSON syntax and report structure summary."""
        await ctx.info(f"json_validate: {path}")
        return _call(_json.validate, path)

    @mcp.tool()
    @tool_permission(ToolPermission.WRITE)
    async def json_append(path: str, json_path: str, value: str, ctx: Context) -> str:
        """Append a value to a JSON array at a JSONPath. Value must be valid JSON."""
        await ctx.info(f"json_append: {path} {json_path}")
        return _call(_json.append, path, json_path, value)

    @mcp.tool()
    @tool_permission(ToolPermission.WRITE)
    async def json_delete_key(path: str, json_path: str, ctx: Context) -> str:
        """Delete a key at a JSONPath."""
        await ctx.info(f"json_delete_key: {path} {json_path}")
        return _call(_json.delete_key, path, json_path)

    @mcp.tool()
    @tool_permission(ToolPermission.WRITE)
    async def json_merge(path: str, json_path: str, updates: str, ctx: Context) -> str:
        """Merge a JSON object into an object at a JSONPath. Updates must be a JSON object string."""
        await ctx.info(f"json_merge: {path} {json_path}")
        return _call(_json.merge, path, json_path, updates)
