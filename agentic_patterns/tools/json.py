"""Agent tools for JSON file operations -- wraps JsonConnector."""

from agentic_patterns.core.connectors.json import JsonConnector
from agentic_patterns.core.tools.permissions import ToolPermission, tool_permission


def get_all_tools() -> list:
    """Get all JSON operation tools."""
    connector = JsonConnector()

    @tool_permission(ToolPermission.READ)
    def json_get(path: str, json_path: str) -> str:
        """Get a value or subtree using JSONPath (e.g. "$.users[0].name")."""
        return connector.get(path, json_path)

    @tool_permission(ToolPermission.READ)
    def json_keys(path: str, json_path: str = "$") -> str:
        """List keys with their types at a JSONPath."""
        return connector.keys(path, json_path)

    @tool_permission(ToolPermission.READ)
    def json_head(path: str, json_path: str = "$", n: int = 10) -> str:
        """Return the first N keys or array elements at a JSONPath."""
        return connector.head(path, json_path, n)

    @tool_permission(ToolPermission.READ)
    def json_tail(path: str, json_path: str = "$", n: int = 10) -> str:
        """Return the last N keys or array elements at a JSONPath."""
        return connector.tail(path, json_path, n)

    @tool_permission(ToolPermission.READ)
    def json_validate(path: str) -> str:
        """Validate JSON syntax and report structure summary."""
        return connector.validate(path)

    @tool_permission(ToolPermission.WRITE)
    def json_set(path: str, json_path: str, value: str) -> str:
        """Set a JSON-encoded value at a JSONPath (e.g. value='"hello"' or '42')."""
        return connector.set(path, json_path, value)

    @tool_permission(ToolPermission.WRITE)
    def json_merge(path: str, json_path: str, updates: str) -> str:
        """Merge a JSON object into the object at a JSONPath without replacing it."""
        return connector.merge(path, json_path, updates)

    @tool_permission(ToolPermission.WRITE)
    def json_append(path: str, json_path: str, value: str) -> str:
        """Append a JSON-encoded value to an array at a JSONPath."""
        return connector.append(path, json_path, value)

    @tool_permission(ToolPermission.WRITE)
    def json_delete_key(path: str, json_path: str) -> str:
        """Delete a key or array element at a JSONPath."""
        return connector.delete_key(path, json_path)

    return [json_get, json_keys, json_head, json_tail, json_validate, json_set, json_merge, json_append, json_delete_key]
