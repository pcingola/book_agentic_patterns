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


def _parse_jsonpath(json_path: str) -> tuple[Any, str]:
    """Parse JSONPath expression, returning (parsed_path, error_string)."""
    try:
        parsed = jsonpath_parse(json_path)
        return parsed, None
    except (JsonPathParserError, Exception) as e:
        return None, f"[Error] Invalid JSONPath expression '{json_path}': {e}"


def _is_wildcard_path(json_path: str) -> bool:
    """Check if JSONPath contains wildcards or filters that could match multiple locations."""
    wildcard_indicators = ["*", "..", "[?", "[*"]
    return any(indicator in json_path for indicator in wildcard_indicators)


def _get_value_at_path(data: dict | list, json_path: str) -> tuple[Any, str]:
    """Get value at JSONPath, returning (value, error_string)."""
    parsed, error = _parse_jsonpath(json_path)
    if error:
        return None, error

    matches = parsed.find(data)
    if not matches:
        return None, f"[Error] Path '{json_path}' not found in JSON"

    if len(matches) > 1:
        return None, f"[Error] Path '{json_path}' matches {len(matches)} locations (must be unique)"

    return matches[0].value, None


def _set_value_at_path(data: dict | list, json_path: str, value: Any) -> tuple[bool, str]:
    """Set value at JSONPath. Modifies data in place."""
    parsed, error = _parse_jsonpath(json_path)
    if error:
        return False, error

    matches = parsed.find(data)

    if len(matches) > 1:
        return False, f"[Error] Path '{json_path}' matches {len(matches)} locations (must be unique for writes)"

    if len(matches) == 1:
        match = matches[0]
        if isinstance(match.context.value, dict):
            match.context.value[str(match.path.fields[0])] = value
        elif isinstance(match.context.value, list):
            match.context.value[match.path.index] = value
        else:
            return False, "[Error] Cannot set value: parent is not a dict or list"
        return True, None

    path_parts = json_path.split(".")
    if len(path_parts) < 2:
        return False, f"[Error] Path '{json_path}' not found in JSON"

    parent_path = ".".join(path_parts[:-1])
    new_key = path_parts[-1].strip("'\"[]")

    parent_parsed, parent_error = _parse_jsonpath(parent_path)
    if parent_error:
        return False, f"[Error] Path '{json_path}' not found in JSON"

    parent_matches = parent_parsed.find(data)
    if len(parent_matches) != 1:
        return False, f"[Error] Path '{json_path}' not found in JSON"

    parent = parent_matches[0].value
    if not isinstance(parent, dict):
        return False, f"[Error] Cannot create key '{new_key}': parent is not an object"

    parent[new_key] = value
    return True, None


def _delete_at_path(data: dict | list, json_path: str) -> tuple[bool, str]:
    """Delete key at JSONPath. Modifies data in place."""
    parsed, error = _parse_jsonpath(json_path)
    if error:
        return False, error

    matches = parsed.find(data)
    if len(matches) == 0:
        return False, f"[Error] Path '{json_path}' not found in JSON"

    if len(matches) > 1:
        return False, f"[Error] Path '{json_path}' matches {len(matches)} locations (must be unique)"

    match = matches[0]

    if isinstance(match.context.value, dict):
        key = str(match.path.fields[0])
        if key in match.context.value:
            del match.context.value[key]
        else:
            return False, f"[Error] Key '{key}' not found"
    elif isinstance(match.context.value, list):
        del match.context.value[match.path.index]
    else:
        return False, "[Error] Cannot delete: parent is not a dict or list"

    return True, None


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


def _format_sliced(sliced: Any, n: int, total: int, from_end: bool, json_path: str) -> str:
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
    Added: delete_key, get, keys, merge, set, validate.
    """

    def append(self, path: str, json_path: str, value: str) -> str:
        """Append a value to an array at a specific JSONPath."""
        host_path = self._translate_path(path)
        if isinstance(host_path, str):
            return host_path

        if not host_path.exists():
            return f"[Error] File not found: {path}"

        try:
            parsed_value = json.loads(value)
        except json.JSONDecodeError as e:
            return f"[Error] Invalid JSON value: {e}"

        try:
            with open(host_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            return f"[Error] Invalid JSON in file: {e}"
        except Exception as e:
            return f"[Error] Failed to read file: {e}"

        target, error = _get_value_at_path(data, json_path)
        if error:
            return error

        if not isinstance(target, list):
            return f"[Error] Target at {json_path} is not an array (type: {type(target).__name__})"

        target.append(parsed_value)

        try:
            with open(host_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.write("\n")
        except Exception as e:
            return f"[Error] Failed to write file: {e}"

        return f"Appended value to {json_path} in {path} (now {len(target)} items)"

    def delete_key(self, path: str, json_path: str) -> str:
        """Delete a key at a specific JSONPath."""
        host_path = self._translate_path(path)
        if isinstance(host_path, str):
            return host_path

        if not host_path.exists():
            return f"[Error] File not found: {path}"

        if json_path == "$":
            return "[Error] Cannot delete entire document (root path not allowed)"

        if _is_wildcard_path(json_path):
            return f"[Error] Wildcard paths not allowed for deletes: {json_path}"

        try:
            with open(host_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            return f"[Error] Invalid JSON in file: {e}"
        except Exception as e:
            return f"[Error] Failed to read file: {e}"

        success, error = _delete_at_path(data, json_path)
        if not success:
            return error

        try:
            with open(host_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.write("\n")
        except Exception as e:
            return f"[Error] Failed to write file: {e}"

        return f"Deleted {json_path} from {path}"

    @context_result()
    def get(self, path: str, json_path: str) -> str:
        """Get a value or subtree using JSONPath syntax."""
        host_path = self._translate_path(path)
        if isinstance(host_path, str):
            return host_path

        if not host_path.exists():
            return f"[Error] File not found: {path}"

        try:
            with open(host_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            return f"[Error] Invalid JSON: {e}"
        except Exception as e:
            return f"[Error] Failed to read file: {e}"

        value, error = _get_value_at_path(data, json_path)
        if error:
            return error

        if isinstance(value, (str, int, float, bool, type(None))):
            return json.dumps(value, ensure_ascii=False)

        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as tmp:
            json.dump(value, tmp, ensure_ascii=False, indent=2)
            tmp_path = Path(tmp.name)

        try:
            result = process_json(tmp_path)
            if not result.success:
                return f"[Error] Failed to process result: {result.content}"
            return result.content
        finally:
            tmp_path.unlink()

    @context_result()
    def head(self, path: str, json_path: str = "$", n: int = 10) -> str:
        """Return the first N keys or elements at a JSONPath."""
        host_path = self._translate_path(path)
        if isinstance(host_path, str):
            return host_path

        if not host_path.exists():
            return f"[Error] File not found: {path}"

        if n <= 0:
            return "[Error] Count must be positive"

        try:
            with open(host_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            return f"[Error] Invalid JSON: {e}"
        except Exception as e:
            return f"[Error] Failed to read file: {e}"

        value, error = _get_value_at_path(data, json_path)
        if error:
            return error

        sliced, total = _slice_value(value, n, from_end=False)
        return _format_sliced(sliced, n, total, from_end=False, json_path=json_path)

    @context_result()
    def keys(self, path: str, json_path: str = "$") -> str:
        """List keys at a specific path in the JSON structure."""
        host_path = self._translate_path(path)
        if isinstance(host_path, str):
            return host_path

        if not host_path.exists():
            return f"[Error] File not found: {path}"

        try:
            with open(host_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            return f"[Error] Invalid JSON: {e}"
        except Exception as e:
            return f"[Error] Failed to read file: {e}"

        value, error = _get_value_at_path(data, json_path)
        if error:
            return error

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
        host_path = self._translate_path(path)
        if isinstance(host_path, str):
            return host_path

        if not host_path.exists():
            return f"[Error] File not found: {path}"

        try:
            parsed_updates = json.loads(updates)
        except json.JSONDecodeError as e:
            return f"[Error] Invalid JSON updates: {e}"

        if not isinstance(parsed_updates, dict):
            return f"[Error] Updates must be a JSON object, not {type(parsed_updates).__name__}"

        try:
            with open(host_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            return f"[Error] Invalid JSON in file: {e}"
        except Exception as e:
            return f"[Error] Failed to read file: {e}"

        target, error = _get_value_at_path(data, json_path)
        if error:
            return error

        if not isinstance(target, dict):
            return f"[Error] Target at {json_path} is not an object (type: {type(target).__name__})"

        target.update(parsed_updates)

        try:
            with open(host_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.write("\n")
        except Exception as e:
            return f"[Error] Failed to write file: {e}"

        return f"Merged {len(parsed_updates)} keys into {json_path} in {path}"

    def set(self, path: str, json_path: str, value: str) -> str:
        """Set a value at a specific JSONPath, preserving the rest of the file."""
        host_path = self._translate_path(path)
        if isinstance(host_path, str):
            return host_path

        if not host_path.exists():
            return f"[Error] File not found: {path}"

        if json_path == "$":
            return "[Error] Cannot replace entire document (root path not allowed)"

        if _is_wildcard_path(json_path):
            return f"[Error] Wildcard paths not allowed for writes: {json_path}"

        try:
            parsed_value = json.loads(value)
        except json.JSONDecodeError as e:
            return f"[Error] Invalid JSON value: {e}"

        value_size = len(value)
        if value_size > 10 * 1024:
            return f"[Warning] Value is very large ({value_size / 1024:.1f} KB). Consider breaking into smaller updates."

        try:
            with open(host_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            return f"[Error] Invalid JSON in file: {e}"
        except Exception as e:
            return f"[Error] Failed to read file: {e}"

        success, error = _set_value_at_path(data, json_path, parsed_value)
        if not success:
            return error

        try:
            with open(host_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.write("\n")
        except Exception as e:
            return f"[Error] Failed to write file: {e}"

        value_preview = value if len(value) <= 50 else f"{value[:47]}..."
        return f"Updated {json_path} = {value_preview} in {path}"

    @context_result()
    def tail(self, path: str, json_path: str = "$", n: int = 10) -> str:
        """Return the last N keys or elements at a JSONPath."""
        host_path = self._translate_path(path)
        if isinstance(host_path, str):
            return host_path

        if not host_path.exists():
            return f"[Error] File not found: {path}"

        if n <= 0:
            return "[Error] Count must be positive"

        try:
            with open(host_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            return f"[Error] Invalid JSON: {e}"
        except Exception as e:
            return f"[Error] Failed to read file: {e}"

        value, error = _get_value_at_path(data, json_path)
        if error:
            return error

        sliced, total = _slice_value(value, n, from_end=True)
        return _format_sliced(sliced, n, total, from_end=True, json_path=json_path)

    def validate(self, path: str) -> str:
        """Validate JSON syntax and structure."""
        host_path = self._translate_path(path)
        if isinstance(host_path, str):
            return host_path

        if not host_path.exists():
            return f"[Error] File not found: {path}"

        try:
            with open(host_path, "r", encoding="utf-8") as f:
                data = json.load(f)

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

        except json.JSONDecodeError as e:
            return f"[Error] Invalid JSON at line {e.lineno}, column {e.colno}: {e.msg}"
        except Exception as e:
            return f"[Error] Failed to read file: {e}"
