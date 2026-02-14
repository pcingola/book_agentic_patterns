# Connectors

Connectors are framework-agnostic abstractions that define what operations an agent can perform against a data source. They are plain Python classes with typed methods -- no dependency on PydanticAI, MCP, or any agent runtime. Tools are thin wrappers that register connector methods so a specific framework can discover and invoke them. This separation keeps connector logic testable without an LLM, portable across frameworks, and free from lock-in.

All connectors live in `agentic_patterns.core.connectors`. PydanticAI tool wrappers live in `agentic_patterns.tools`. MCP server wrappers live in `agentic_patterns.mcp`.


## Connector Base

All connectors extend a minimal base class:

```python
from agentic_patterns.core.connectors.base import Connector
```

`Connector` is an abstract base class with no methods. It serves as a type marker for the connector layer.


## FileConnector

`FileConnector` provides file operations with workspace sandbox isolation. The agent sees sandbox paths like `/workspace/notes.md`; the connector translates them to host filesystem paths via `workspace_to_host_path()`. User and session context is resolved from Python contextvars, not passed as arguments.

```python
from agentic_patterns.core.connectors.file import FileConnector

connector = FileConnector()
```

### Binding as tools

Connector methods are bound directly as agent tools without wrapper functions:

```python
from agentic_patterns.core.agents import get_agent

tools = [connector.read, connector.write, connector.edit, connector.head,
         connector.tail, connector.find, connector.list, connector.append, connector.delete]

agent = get_agent(tools=tools)
```

### Operations

**Read operations** (decorated with `@tool_permission(ToolPermission.READ)`):

`read(path)` -- read entire file with automatic truncation for large files. Uses `@context_result()` to save full content to workspace and return a truncated preview when the result exceeds size limits.

`head(path, n=10)` -- first N lines. Returns content with a line range indicator when the file is longer.

`tail(path, n=10)` -- last N lines.

`find(path, query)` -- search file contents for a string, returning matching lines with line numbers. Capped at 100 matches.

`list(path, pattern="*")` -- list files matching a glob pattern. Capped at 200 entries.

**Write operations** (decorated with `@tool_permission(ToolPermission.WRITE)`):

`write(path, content)` -- write or overwrite a file. Creates parent directories automatically.

`append(path, content)` -- append content to an existing file.

`edit(path, start_line, end_line, new_content)` -- replace lines start_line to end_line (1-indexed, inclusive) with new content. Validates line bounds.

`delete(path)` -- delete a file.

All operations return strings (content or status messages). Recoverable errors are caught and re-raised as `ModelRetry`, which PydanticAI presents to the model as a retryable tool error.


## CsvConnector

`CsvConnector` extends `FileConnector` with CSV-aware operations. It inherits generic file operations (delete, edit, find, list, read, write) and adds or overrides CSV-specific methods. Delimiter detection is automatic.

```python
from agentic_patterns.core.connectors.csv import CsvConnector

connector = CsvConnector()
```

**Read operations:**

`headers(path)` -- column names with count, truncated for wide tables.

`head(path, n=10)` -- first N rows with automatic column/cell truncation via the CSV processor.

`tail(path, n=10)` -- last N rows.

`read_row(path, row_number)` -- single row by 1-indexed number.

`find_rows(path, column, value, limit=10)` -- rows where a column matches a value. Column can be a name (str) or index (int).

**Write operations:**

`append(path, values)` -- append a row. Values can be a `dict[str, str]` keyed by column name or a `list[str]` matching column order.

`delete_rows(path, column, value)` -- delete all rows where column matches value.

`update_cell(path, row_number, column, value)` -- update a single cell.

`update_row(path, key_column, key_value, updates)` -- update all columns in rows matching a key, where `updates` is a `dict[str, str]`.


## JsonConnector

`JsonConnector` extends `FileConnector` with JSONPath-based navigation. It inherits generic file operations and adds or overrides JSON-specific methods.

```python
from agentic_patterns.core.connectors.json import JsonConnector

connector = JsonConnector()
```

**Read operations:**

`schema(path, json_path="$", max_depth=4)` -- show the structure of a JSON file: keys, types, nesting, array sizes. Walks the structure up to `max_depth` levels.

`get(path, json_path)` -- get a value or subtree at a JSONPath. Scalar values return directly; complex values are processed through the JSON truncation pipeline.

`keys(path, json_path="$")` -- list keys at a path with type annotations (e.g., "name (str)", "items (array, 42 items)").

`head(path, json_path="$", n=10)` -- first N keys or elements at a path.

`tail(path, json_path="$", n=10)` -- last N keys or elements at a path.

`query(path, json_path, max_results=20)` -- extended JSONPath with filters. Supports expressions like `$.body[?name =~ "breast"]` and `$.items[?(@.age > 30)]`.

`validate(path)` -- validate JSON syntax. Returns structure summary (root type, key count or array length, file size).

**Write operations:**

`set(path, json_path, value)` -- set a value at a specific path. Rejects root-level replacements and wildcard paths. Value must be a JSON string under 10 KB.

`delete_key(path, json_path)` -- delete a key at a path. Rejects root and wildcard paths.

`merge(path, json_path, updates)` -- merge a JSON object into an existing object at a path without replacing it entirely.

`append(path, json_path, value)` -- append a value to an array at a path.


## Connector Chaining

Connectors compose through the workspace filesystem. One agent writes a file as output; another reads it as input. The agents have no knowledge of each other.

A typical chain: an NL2SQL agent executes a query and saves results to `/workspace/results.csv`. A second agent equipped with `CsvConnector` picks up that file and inspects, filters, or transforms it. A third agent could produce a chart from the same CSV. Each operates through its own connector, and the workspace provides shared persistent storage.

```python
# Agent 1: SQL -> CSV
nl2sql_agent = create_agent(db_id="bookstore")
await run_agent(nl2sql_agent, "List all books... Save to /workspace/books.csv")

# Agent 2: CSV inspection
csv_connector = CsvConnector()
csv_agent = get_agent(tools=[csv_connector.head, csv_connector.find_rows, csv_connector.headers])
await run_agent(csv_agent, "Show headers and first 5 rows of /workspace/books.csv")
```
