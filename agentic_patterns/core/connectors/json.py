"""JSON connector for reading and writing JSON files in the workspace sandbox.

Inherits generic file operations from FileConnector and overrides/adds
JSON-aware methods. Read operations use the JSON processor for automatic
structure truncation to handle deeply nested structures.
"""

import json
from pathlib import Path
from typing import Any

from jsonpath_ng import parse as jsonpath_parse
from jsonpath_ng.exceptions import JsonPathParserError

from agentic_patterns.core.connectors.file import FileConnector
from agentic_patterns.core.context.decorators import context_result
from agentic_patterns.core.context.processors.json_processor import process_json


def _parse_jsonpath(json_path: str) -> Any:
    """Parse JSONPath expression."""
    try:
        return jsonpath_parse(json_path)
    except (JsonPathParserError, Exception) as e:
        raise ValueError(f"Invalid JSONPath expression '{json_path}': {e}") from e


def _is_wildcard_path(json_path: str) -> bool:
    """Check if JSONPath contains wildcards or filters that could match multiple locations."""
    wildcard_indicators = ["*", "..", "[?", "[*"]
    return any(indicator in json_path for indicator in wildcard_indicators)


def _get_value_at_path(data: dict | list, json_path: str) -> Any:
    """Get value at JSONPath."""
    parsed = _parse_jsonpath(json_path)
    matches = parsed.find(data)
    if not matches:
        raise KeyError(f"Path '{json_path}' not found in JSON")
    if len(matches) > 1:
        raise ValueError(
            f"Path '{json_path}' matches {len(matches)} locations (must be unique)"
        )
    return matches[0].value


def _set_value_at_path(data: dict | list, json_path: str, value: Any) -> None:
    """Set value at JSONPath. Modifies data in place."""
    parsed = _parse_jsonpath(json_path)
    matches = parsed.find(data)

    if len(matches) > 1:
        raise ValueError(
            f"Path '{json_path}' matches {len(matches)} locations (must be unique for writes)"
        )

    if len(matches) == 1:
        match = matches[0]
        if isinstance(match.context.value, dict):
            match.context.value[str(match.path.fields[0])] = value
        elif isinstance(match.context.value, list):
            match.context.value[match.path.index] = value
        else:
            raise TypeError("Cannot set value: parent is not a dict or list")
        return

    path_parts = json_path.split(".")
    if len(path_parts) < 2:
        raise KeyError(f"Path '{json_path}' not found in JSON")

    parent_path = ".".join(path_parts[:-1])
    new_key = path_parts[-1].strip("'\"[]")

    parent_parsed = _parse_jsonpath(parent_path)
    parent_matches = parent_parsed.find(data)
    if len(parent_matches) != 1:
        raise KeyError(f"Path '{json_path}' not found in JSON")

    parent = parent_matches[0].value
    if not isinstance(parent, dict):
        raise TypeError(f"Cannot create key '{new_key}': parent is not an object")

    parent[new_key] = value


def _delete_at_path(data: dict | list, json_path: str) -> None:
    """Delete key at JSONPath. Modifies data in place."""
    parsed = _parse_jsonpath(json_path)
    matches = parsed.find(data)
    if not matches:
        raise KeyError(f"Path '{json_path}' not found in JSON")
    if len(matches) > 1:
        raise ValueError(
            f"Path '{json_path}' matches {len(matches)} locations (must be unique)"
        )

    match = matches[0]
    if isinstance(match.context.value, dict):
        key = str(match.path.fields[0])
        if key in match.context.value:
            del match.context.value[key]
        else:
            raise KeyError(f"Key '{key}' not found")
    elif isinstance(match.context.value, list):
        del match.context.value[match.path.index]
    else:
        raise TypeError("Cannot delete: parent is not a dict or list")


def _describe_schema(
    value: Any, path: str = "$", max_depth: int = 4, _depth: int = 0
) -> list[str]:
    """Walk JSON structure and return type descriptions per path."""
    lines = []
    indent = "  " * _depth
    if isinstance(value, dict):
        lines.append(f"{indent}{path} (object, {len(value)} keys)")
        if _depth < max_depth:
            for key in list(value.keys())[:30]:
                child_path = f"{path}.{key}"
                lines.extend(
                    _describe_schema(value[key], child_path, max_depth, _depth + 1)
                )
            if len(value) > 30:
                lines.append(f"{indent}  ... and {len(value) - 30} more keys")
    elif isinstance(value, list):
        lines.append(f"{indent}{path} (array, {len(value)} items)")
        if _depth < max_depth and len(value) > 0:
            lines.extend(
                _describe_schema(value[0], f"{path}[0]", max_depth, _depth + 1)
            )
    else:
        type_name = type(value).__name__ if value is not None else "null"
        lines.append(f"{indent}{path} ({type_name})")
    return lines


def _slice_value(value: Any, n: int, from_end: bool = False) -> tuple[Any, int]:
    """Slice first/last N keys or elements from a dict or list."""
    if isinstance(value, dict):
        keys = list(value.keys())
        total = len(keys)
        selected = keys[-n:] if from_end else keys[:n]
        return {k: value[k] for k in selected}, total
    elif isinstance(value, list):
        total = len(value)
        sliced = value[-n:] if from_end else value[:n]
        return sliced, total
    return value, 1


def _format_sliced(
    sliced: Any, n: int, total: int, from_end: bool, json_path: str
) -> str:
    """Format sliced JSON value with truncation info."""
    formatted = json.dumps(sliced, ensure_ascii=False, indent=2)
    if total > n:
        direction = "last" if from_end else "first"
        return f"[Showing {direction} {n} of {total} at {json_path}]\n{formatted}"
    return formatted


class JsonConnector(FileConnector):
    """JSON operations with workspace sandbox isolation.

    Inherited from FileConnector: delete (file), edit, find, list, read (raw), write.
    Overridden: append, head, tail.
    Added: delete_key, get, keys, merge, query, schema, set, validate.
    """

    def _read_json(self, path: str) -> tuple[Path, dict | list]:
        """Read and parse JSON file, returning (host_path, data)."""
        host_path = self._translate_path(path)
        if not host_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        with open(host_path, "r", encoding="utf-8") as f:
            return host_path, json.load(f)

    @staticmethod
    def _write_json(host_path: Path, data: dict | list) -> None:
        """Write JSON data to file."""
        with open(host_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")

    def append(self, path: str, json_path: str, value: str) -> str:
        """Append a value to an array at a specific JSONPath."""
        parsed_value = json.loads(value)
        host_path, data = self._read_json(path)

        target = _get_value_at_path(data, json_path)
        if not isinstance(target, list):
            raise TypeError(
                f"Target at {json_path} is not an array (type: {type(target).__name__})"
            )

        target.append(parsed_value)
        self._write_json(host_path, data)
        return f"Appended value to {json_path} in {path} (now {len(target)} items)"

    def delete_key(self, path: str, json_path: str) -> str:
        """Delete a key at a specific JSONPath."""
        if json_path == "$":
            raise ValueError("Cannot delete entire document (root path not allowed)")
        if _is_wildcard_path(json_path):
            raise ValueError(f"Wildcard paths not allowed for deletes: {json_path}")

        host_path, data = self._read_json(path)
        _delete_at_path(data, json_path)
        self._write_json(host_path, data)
        return f"Deleted {json_path} from {path}"

    @context_result()
    def get(self, path: str, json_path: str) -> str:
        """Get a value or subtree using JSONPath syntax."""
        host_path, data = self._read_json(path)
        value = _get_value_at_path(data, json_path)

        if isinstance(value, (str, int, float, bool, type(None))):
            return json.dumps(value, ensure_ascii=False)

        import tempfile

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as tmp:
            json.dump(value, tmp, ensure_ascii=False, indent=2)
            tmp_path = Path(tmp.name)

        try:
            result = process_json(tmp_path)
            if not result.success:
                raise ValueError(f"Failed to process result: {result.content}")
            return result.content
        finally:
            tmp_path.unlink()

    @context_result()
    def head(self, path: str, json_path: str = "$", n: int = 10) -> str:
        """Return the first N keys or elements at a JSONPath."""
        _, data = self._read_json(path)
        if n <= 0:
            raise ValueError("Count must be positive")
        value = _get_value_at_path(data, json_path)
        sliced, total = _slice_value(value, n, from_end=False)
        return _format_sliced(sliced, n, total, from_end=False, json_path=json_path)

    @context_result()
    def keys(self, path: str, json_path: str = "$") -> str:
        """List keys at a specific path in the JSON structure."""
        _, data = self._read_json(path)
        value = _get_value_at_path(data, json_path)

        if isinstance(value, dict):
            key_info = []
            for key, val in value.items():
                type_name = type(val).__name__
                if isinstance(val, dict):
                    type_name = f"object ({len(val)} keys)"
                elif isinstance(val, list):
                    type_name = f"array ({len(val)} items)"
                key_info.append(f"{key} ({type_name})")
            return f"Keys at {json_path}: {', '.join(key_info)}"

        elif isinstance(value, list):
            return f"[Array with {len(value)} items at {json_path}]"

        else:
            type_name = type(value).__name__
            return f"[Value at {json_path} is type: {type_name}]"

    def merge(self, path: str, json_path: str, updates: str) -> str:
        """Merge updates into an object at a specific JSONPath without replacing it entirely."""
        parsed_updates = json.loads(updates)
        if not isinstance(parsed_updates, dict):
            raise TypeError(
                f"Updates must be a JSON object, not {type(parsed_updates).__name__}"
            )

        host_path, data = self._read_json(path)
        target = _get_value_at_path(data, json_path)
        if not isinstance(target, dict):
            raise TypeError(
                f"Target at {json_path} is not an object (type: {type(target).__name__})"
            )

        target.update(parsed_updates)
        self._write_json(host_path, data)
        return f"Merged {len(parsed_updates)} keys into {json_path} in {path}"

    @context_result()
    def query(self, path: str, json_path: str, max_results: int = 20) -> str:
        """Query JSON using extended JSONPath with filters. Examples: $.body[?name =~ "breast"], $.items[?(@.age > 30)]."""
        _, data = self._read_json(path)

        from jsonpath_ng.ext import parse as ext_parse

        try:
            parsed = ext_parse(json_path)
        except Exception as e:
            raise ValueError(f"Invalid JSONPath expression '{json_path}': {e}") from e

        matches = parsed.find(data)
        if not matches:
            return f"No matches found for: {json_path}"

        total = len(matches)
        values = [m.value for m in matches[:max_results]]
        result = json.dumps(values, ensure_ascii=False, indent=2)
        if total > max_results:
            result += f"\n\n[Showing {max_results} of {total} matches]"
        else:
            result = f"[{total} match{'es' if total != 1 else ''}]\n{result}"
        return result

    def schema(self, path: str, json_path: str = "$", max_depth: int = 4) -> str:
        """Show the structure of a JSON file: keys, types, nesting, and array sizes."""
        _, data = self._read_json(path)
        value = _get_value_at_path(data, json_path)
        lines = _describe_schema(value, json_path, max_depth)
        return "\n".join(lines)

    def set(self, path: str, json_path: str, value: str) -> str:
        """Set a value at a specific JSONPath, preserving the rest of the file."""
        if json_path == "$":
            raise ValueError("Cannot replace entire document (root path not allowed)")
        if _is_wildcard_path(json_path):
            raise ValueError(f"Wildcard paths not allowed for writes: {json_path}")

        parsed_value = json.loads(value)
        if len(value) > 10 * 1024:
            raise ValueError(
                f"Value is very large ({len(value) / 1024:.1f} KB). Consider breaking into smaller updates."
            )

        host_path, data = self._read_json(path)
        _set_value_at_path(data, json_path, parsed_value)
        self._write_json(host_path, data)

        value_preview = value if len(value) <= 50 else f"{value[:47]}..."
        return f"Updated {json_path} = {value_preview} in {path}"

    @context_result()
    def tail(self, path: str, json_path: str = "$", n: int = 10) -> str:
        """Return the last N keys or elements at a JSONPath."""
        _, data = self._read_json(path)
        if n <= 0:
            raise ValueError("Count must be positive")
        value = _get_value_at_path(data, json_path)
        sliced, total = _slice_value(value, n, from_end=True)
        return _format_sliced(sliced, n, total, from_end=True, json_path=json_path)

    def validate(self, path: str) -> str:
        """Validate JSON syntax and structure."""
        host_path = self._translate_path(path)
        if not host_path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        try:
            with open(host_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            return f"Invalid JSON at line {e.lineno}, column {e.colno}: {e.msg}"

        size_bytes = host_path.stat().st_size
        size_kb = size_bytes / 1024

        if isinstance(data, dict):
            keys = list(data.keys())
            if len(keys) <= 10:
                key_list = ", ".join(keys)
                return f"Valid JSON: {len(keys)} keys at root ({key_list}), size: {size_kb:.1f} KB"
            else:
                key_list = ", ".join(keys[:10])
                return f"Valid JSON: {len(keys)} keys at root ({key_list}, ...), size: {size_kb:.1f} KB"
        elif isinstance(data, list):
            return f"Valid JSON: array with {len(data)} items at root, size: {size_kb:.1f} KB"
        else:
            type_name = type(data).__name__
            return f"Valid JSON: {type_name} at root, size: {size_kb:.1f} KB"
