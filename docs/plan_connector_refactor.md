# Plan: Make file connector API consistent across FileConnector, CsvConnector, and JsonConnector

**Files:**
- `chapters/data_sources_and_connectors/connectors.md` (already done)
- `agentic_patterns/core/connectors/file.py`
- `agentic_patterns/core/connectors/csv.py`
- `agentic_patterns/core/connectors/json.py`
- `agentic_patterns/core/connectors/__init__.py`
- `tests/unit/connectors/test_csv.py`
- `tests/unit/connectors/test_json.py`
- `agentic_patterns/examples/connectors/json_connector_example.py`

**Problem:** The chapter describes connectors using `connector.method()` style (e.g. `file.read()`, `csv.head()`, `json.get()`), but the code uses standalone functions (`read_file()`, `head_csv()`, `get_json()`). The code should use classes to match the chapter's API. Additionally, three file operations documented in the chapter are not implemented: `list`, `find`, `delete`.

**Principles:**

1. Same concept uses the same verb across all three connectors
2. All use classes with methods matching `connector.method()` style from the chapter
3. No redundant suffixes when the connector context already implies the unit
4. `head`/`tail` everywhere for bounded reads, defaulting to `n=10`
5. Each class in its own file, named after the class (e.g. `file.py` has `FileConnector`)
6. `@tool_permission` decorators stay on each method
7. `ctx` parameter stays on each method (workspace isolation)

## Chapter changes (already applied)

The chapter (`connectors.md`) is already consistent. No changes needed.

## Code changes to FileConnector (`file.py`)

Wrap existing functions as methods on a `FileConnector` class. Add the three missing operations.

| Current function | New method | Notes |
|---|---|---|
| `read_file(path, ctx)` | `FileConnector.read(path, ctx)` | Rename |
| `write_file(path, content, ctx)` | `FileConnector.write(path, content, ctx)` | Rename |
| `append_file(path, content, ctx)` | `FileConnector.append(path, content, ctx)` | Rename |
| `head_file(path, n, ctx)` | `FileConnector.head(path, n, ctx)` | Rename |
| `tail_file(path, n, ctx)` | `FileConnector.tail(path, n, ctx)` | Rename |
| `edit_file(path, start_line, end_line, new_content, ctx)` | `FileConnector.edit(path, start_line, end_line, new_content, ctx)` | Rename |
| -- | `FileConnector.list(path, pattern, ctx)` | New: list files matching glob pattern |
| -- | `FileConnector.find(path, query, ctx)` | New: search file contents for a string |
| -- | `FileConnector.delete(path, ctx)` | New: delete a file |

Keep `_translate_path` as a module-level helper (or static method).

## Code changes to CsvConnector (`csv.py`)

Wrap existing functions as methods on a `CsvConnector` class.

| Current function | New method | Notes |
|---|---|---|
| `get_csv_headers(path, ctx)` | `CsvConnector.headers(path, ctx)` | Rename |
| `head_csv(path, n, ctx)` | `CsvConnector.head(path, n, ctx)` | Rename |
| `tail_csv(path, n, ctx)` | `CsvConnector.tail(path, n, ctx)` | Rename |
| `read_csv_row(path, row_number, ctx)` | `CsvConnector.read_row(path, row_number, ctx)` | Rename |
| `find_csv(path, column, value, limit, ctx)` | `CsvConnector.find(path, column, value, limit, ctx)` | Rename |
| `update_csv_cell(path, row_number, column, value, ctx)` | `CsvConnector.update_cell(path, row_number, column, value, ctx)` | Rename |
| `update_csv_row(path, key_column, key_value, updates, ctx)` | `CsvConnector.update_row(path, key_column, key_value, updates, ctx)` | Rename |
| `append_csv(path, values, ctx)` | `CsvConnector.append(path, values, ctx)` | Rename |
| `delete_csv(path, column, value, ctx)` | `CsvConnector.delete(path, column, value, ctx)` | Rename |

## Code changes to JsonConnector (`json.py`)

Wrap existing functions as methods on a `JsonConnector` class. Internal helpers (`_parse_jsonpath`, `_is_wildcard_path`, `_get_value_at_path`, `_set_value_at_path`, `_delete_at_path`, `_slice_value`, `_format_sliced`) stay as module-level private functions.

| Current function | New method | Notes |
|---|---|---|
| `validate_json(path, ctx)` | `JsonConnector.validate(path, ctx)` | Rename |
| `head_json(path, json_path, n, ctx)` | `JsonConnector.head(path, json_path, n, ctx)` | Rename |
| `tail_json(path, json_path, n, ctx)` | `JsonConnector.tail(path, json_path, n, ctx)` | Rename |
| `keys_json(path, json_path, ctx)` | `JsonConnector.keys(path, json_path, ctx)` | Rename |
| `get_json(path, json_path, ctx)` | `JsonConnector.get(path, json_path, ctx)` | Rename |
| `set_json(path, json_path, value, ctx)` | `JsonConnector.set(path, json_path, value, ctx)` | Rename |
| `delete_json(path, json_path, ctx)` | `JsonConnector.delete(path, json_path, ctx)` | Rename |
| `merge_json(path, json_path, updates, ctx)` | `JsonConnector.merge(path, json_path, updates, ctx)` | Rename |
| `append_json(path, json_path, value, ctx)` | `JsonConnector.append(path, json_path, value, ctx)` | Rename |

## Changes to `__init__.py`

Export the three classes instead of individual functions:

```python
from agentic_patterns.core.connectors.csv import CsvConnector
from agentic_patterns.core.connectors.file import FileConnector
from agentic_patterns.core.connectors.json import JsonConnector
```

## Changes to tests

Update imports and calls in:
- `tests/unit/connectors/test_csv.py`: use `CsvConnector.method()` instead of `function_name()`
- `tests/unit/connectors/test_json.py`: use `JsonConnector.method()` instead of `function_name()`

## Changes to examples

Update `agentic_patterns/examples/connectors/json_connector_example.py`: use `JsonConnector.method()` instead of `function_name()`.

## Resulting consistency (chapter = code)

| Concept | FileConnector | CsvConnector | JsonConnector |
|---|---|---|---|
| Schema | -- | `headers` | `keys` |
| Head | `head(n=10)` | `head(n=10)` | `head(json_path, n=10)` |
| Tail | `tail(n=10)` | `tail(n=10)` | `tail(json_path, n=10)` |
| Point read | `read` | `read_row` | `get` |
| Search | `find` | `find` | -- |
| Full write | `write` | -- | -- |
| Append | `append` | `append` | `append` |
| Point write | `edit` | `update_cell` | `set` |
| Row/object write | -- | `update_row` | `merge` |
| Delete | `delete` | `delete` | `delete` |
| Validate | -- | -- | `validate` |
| List | `list` | -- | -- |
