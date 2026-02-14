# Tools

Tools let agents perform actions beyond text generation -- calculations, file I/O, API calls, database queries. The library provides infrastructure for defining tools, selecting them dynamically, enforcing permissions, managing the workspace where agents store artifacts, and controlling context size when tools return large results.

All tool-related infrastructure lives in `agentic_patterns.core.tools`. PydanticAI tool wrappers (the actual tools agents use) live in `agentic_patterns.tools`.


## Defining Tools

A tool is a plain Python function with type hints and a docstring. The framework inspects the signature to generate the JSON schema the model needs to call the tool.

```python
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

def sub(a: int, b: int) -> int:
    """Subtract two numbers"""
    return a - b
```

Pass tools when creating an agent:

```python
from agentic_patterns.core.agents import get_agent, run_agent

agent = get_agent(tools=[add, sub])
result, nodes = await run_agent(agent, "What is 40123456789 + 2123456789?", verbose=True)
print(result.result.output)
```

The model decides which tool to call based on the task. `run_agent` executes the agent loop, invoking tools as the model requests them.


## Structured Output

Structured output constrains the model to return data conforming to a Pydantic schema instead of free-form text. Define a model and pass it as `output_type`:

```python
from pydantic import BaseModel, Field

class ProgrammingLanguage(BaseModel):
    name: str
    paradigm: str = Field(description="Primary paradigm: functional, OO, procedural, etc.")
    typed: bool = Field(description="Whether the language is statically typed")

agent = get_agent(output_type=list[ProgrammingLanguage])
result, _ = await run_agent(agent, "List 3 popular programming languages.")

for lang in result.result.output:
    print(f"{lang.name}: {lang.paradigm}, typed={lang.typed}")
```

The result is a typed Python object (here a `list[ProgrammingLanguage]`), not a string. The `Field(description=...)` annotations guide the model on what each field means.


## Tool Selection

When an agent has access to many tools, passing all of them at once wastes context and can confuse the model. Tool selection solves this with a two-stage architecture: a selection agent picks the relevant tools, then the task agent runs with only those tools.

### Manual approach

Build tool descriptions, ask a selection agent to pick tool names, then filter:

```python
from agentic_patterns.core.tools import func_to_description

# func_to_description generates a rich description from the function signature
print(func_to_description(add))
# Tool: add(a: int, b: int) -> int
# Description: Add two numbers
```

### ToolSelector

`ToolSelector` encapsulates the two-stage pattern:

```python
from agentic_patterns.core.tools import ToolSelector

selector = ToolSelector([add, sub, mul, div, sqrt, log, ...])
selected = await selector.select("What is 2 + 3?", verbose=True)

agent = get_agent(tools=selected)
result, _ = await run_agent(agent, "What is 2 + 3?")
```

Constructor parameters:

| Parameter | Type | Default | Description |
|---|---|---|---|
| `tools` | `list[Callable]` | required | All available tool functions |
| `prompt_template` | `str \| None` | `None` | Custom selection prompt (must contain `{query}` and `{tools_description}` placeholders) |
| `model` | model instance | `None` | Model override for the selection agent |
| `config_name` | `str` | `"default"` | Model config name from `config.yaml` |

The `select(query, verbose=False)` method returns a filtered `list[Callable]` of tools relevant to the query.


## Tool Permissions

Permissions define authority boundaries for tools. Three permission levels exist:

| Permission | Meaning |
|---|---|
| `ToolPermission.READ` | Observation without mutation |
| `ToolPermission.WRITE` | State mutation |
| `ToolPermission.CONNECT` | External system access |

### Annotating tools

Use the `@tool_permission` decorator. Tools without the decorator default to READ:

```python
from agentic_patterns.core.tools import ToolPermission, tool_permission

@tool_permission(ToolPermission.READ)
def get_balance(account_id: str) -> float:
    """Get account balance."""
    return 1500.00

@tool_permission(ToolPermission.WRITE)
def transfer_funds(from_acct: str, to_acct: str, amount: float) -> bool:
    """Transfer funds between accounts."""
    return True

@tool_permission(ToolPermission.WRITE, ToolPermission.CONNECT)
def send_notification(email: str, amount: float) -> bool:
    """Send payment notification to external email."""
    return True
```

A tool can require multiple permissions. CONNECT tools are automatically blocked when the session contains private data (see Compliance).

### Inspecting permissions

```python
from agentic_patterns.core.tools import get_permissions

get_permissions(transfer_funds)  # {ToolPermission.WRITE}
get_permissions(send_notification)  # {ToolPermission.WRITE, ToolPermission.CONNECT}
```

### Construction-time filtering

Filter tools before passing them to the agent. The agent never sees disallowed tools:

```python
from agentic_patterns.core.tools import filter_tools_by_permission

all_tools = [get_balance, transfer_funds, send_notification]

read_only = filter_tools_by_permission(all_tools, granted={ToolPermission.READ})
# [get_balance]

read_write = filter_tools_by_permission(all_tools, granted={ToolPermission.READ, ToolPermission.WRITE})
# [get_balance, transfer_funds]
```

### Runtime enforcement

The agent sees all tools, but execution raises `ToolPermissionError` if the permission is denied:

```python
from agentic_patterns.core.tools import enforce_tools_permissions

enforced = enforce_tools_permissions(all_tools, granted={ToolPermission.READ})
agent = get_agent(tools=enforced)
# Agent can attempt transfer_funds but it will raise ToolPermissionError
```

Construction-time filtering is cleaner (the agent cannot even attempt disallowed actions). Runtime enforcement lets the agent see the tool and explain why it cannot use it.


## The Workspace

The workspace is a shared file system where agents store artifacts too large for the context window. Agents see sandbox paths (`/workspace/...`) while actual files are stored in isolated directories per user and session.

### Path translation

```python
from pathlib import PurePosixPath
from agentic_patterns.core.workspace import workspace_to_host_path

host_path = workspace_to_host_path(PurePosixPath("/workspace/reports/analysis.json"))
# Resolves to: WORKSPACE_DIR / user_id / session_id / reports / analysis.json
```

User and session identity come from contextvars (set once at the request boundary via `set_user_session()`). All downstream code picks them up automatically.

### Reading and writing

```python
from agentic_patterns.core.workspace import write_to_workspace, read_from_workspace, list_workspace_files

write_to_workspace("/workspace/output.json", '{"key": "value"}')
content = read_from_workspace("/workspace/output.json")
files = list_workspace_files("*.json")
```

`write_to_workspace` creates parent directories automatically and accepts both `str` and `bytes`. `store_result(content, content_type)` is a convenience that generates a UUID filename and returns the sandbox path.

### Tool pattern: write large output, return summary

When a tool produces large output, write the full result to the workspace and return a concise summary with the file path:

```python
def analyze_dataset(query: str) -> str:
    """Analyze data and save results to workspace."""
    result = run_analysis(query)  # large result

    write_to_workspace("/workspace/analysis/result.json", json.dumps(result))

    return f"Analysis complete. Rows: {result['row_count']}, Mean: {result['mean']}\nFull results: /workspace/analysis/result.json"
```

### User isolation

Each (user_id, session_id) pair maps to an isolated directory. Path traversal attempts raise `WorkspaceError`:

```python
workspace_to_host_path(PurePosixPath("/workspace/../../../etc/passwd"))
# WorkspaceError: Path traversal not allowed
```


## Context Result Decorator

`@context_result()` automates the "save large result, return truncated preview" pattern. When a tool's return value exceeds a configurable threshold, the decorator:

1. Detects the content type (JSON, CSV, text)
2. Saves the full content to the workspace
3. Truncates according to content type (structural truncation for JSON, head/tail for CSV and text)
4. Returns the file path and a preview

```python
from agentic_patterns.core.context.decorators import context_result

@context_result()
async def sql_execute(db_id: str, query: str) -> str:
    # If this returns a large CSV string, the decorator saves it
    # and returns a preview with the workspace path
    return await run_query(db_id, query)

@context_result(save=False)
async def show_notebook() -> str:
    # save=False: truncate but don't persist (view-only operation)
    return format_notebook()

@context_result("sql_query")
async def run_sql(sql: str) -> str:
    # Use a named truncation config from config.yaml
    return await execute(sql)
```

Works with both sync and async functions. The truncation config controls thresholds, number of head/tail rows for CSV, array/key limits for JSON, and maximum preview size.


## Built-in Tool Wrappers

The library ships tool wrappers in `agentic_patterns.tools`. Each module exposes a `get_all_tools()` function returning a list of tool functions ready to pass to `Agent(tools=[...])`.

| Module | Wraps | Tools |
|---|---|---|
| `file` | `core.connectors.file` | file_read, file_head, file_tail, file_find, file_list, file_write, file_append, file_edit, file_delete |
| `csv` | `core.connectors.csv` | csv_headers, csv_head, csv_tail, csv_read_row, csv_find_rows, csv_append, csv_update_cell, csv_update_row, csv_delete_rows |
| `json` | `core.connectors.json` | json_get, json_keys, json_head, json_tail, json_validate, json_set, json_merge, json_append, json_delete_key |
| `sql` | `core.connectors.sql` | sql_list_databases, sql_list_tables, sql_show_schema, sql_show_table_details, sql_execute, sql_get_row_by_id |
| `openapi` | `core.connectors.openapi` | openapi_list_apis, openapi_list_endpoints, openapi_show_api_summary, openapi_show_endpoint_details, openapi_call_endpoint |
| `todo` | `toolkits.todo` | todo_add, todo_add_many, todo_create_list, todo_delete, todo_show, todo_update_status |
| `repl` | `core.repl` | repl_execute_cell, repl_rerun_cell, repl_show_notebook, repl_show_cell, repl_delete_cell, repl_clear_notebook, repl_export_ipynb |
| `sandbox` | `core.sandbox` | sandbox_execute |
| `data_analysis` | `toolkits.data_analysis` | list_dataframes + dynamically generated operation tools |
| `data_viz` | `toolkits.data_viz` | list_plots + dynamically generated plot tools |
| `format_conversion` | `toolkits.format_conversion` | convert_document |

All wrappers follow the same conventions: READ/WRITE/CONNECT permissions via `@tool_permission`, `@context_result()` for tools that may return large results, and `ModelRetry` exceptions for retryable errors.

Usage:

```python
from agentic_patterns.tools.file import get_all_tools as get_file_tools
from agentic_patterns.tools.sql import get_all_tools as get_sql_tools
from agentic_patterns.core.tools import filter_tools_by_permission, ToolPermission

# Combine tools from multiple modules
all_tools = get_file_tools() + get_sql_tools()

# Optionally filter by permission
read_tools = filter_tools_by_permission(all_tools, granted={ToolPermission.READ})

agent = get_agent(tools=read_tools)
```


## Dynamic Tool Generation

Some tool modules (data_analysis, data_viz) have large operation registries where each operation becomes a separate tool function. Instead of writing tool functions by hand, the `agentic_patterns.tools.dynamic` module generates them at import time from operation metadata.

### Helpers

`get_param_signature(param_name, param_default)` generates a parameter signature fragment for use in dynamically constructed function definitions. It handles type inference from default values: strings produce `param: str = 'value'`, type classes produce `param: type = None`, and `None` produces `param = None`.

`generate_param_docs(parameters)` generates an Args-style docstring section from a parameter dict. Each entry includes the parameter name, inferred type, and default value.

### How it works

Each operation registry (e.g., `toolkits.data_analysis.executor.get_all_operations()`) returns a dict mapping operation names to config objects with `description`, `parameters`, and other metadata. The tool wrapper module iterates over this dict, builds a function signature string using `get_param_signature()`, and uses `exec()` to create a callable with the correct signature and docstring. This ensures the LLM sees accurate parameter names, types, and descriptions in the tool schema.

Both the PydanticAI tool wrappers (`tools/data_analysis.py`, `tools/data_viz.py`) and MCP server wrappers (`mcp/data_analysis/tools.py`, `mcp/data_viz/tools.py`) use the same dynamic helpers, keeping tool definitions consistent across both interfaces.


## API Reference

### `agentic_patterns.core.tools`

| Name | Kind | Description |
|---|---|---|
| `ToolPermission` | Enum | READ, WRITE, CONNECT |
| `ToolPermissionError` | Exception | Raised when a tool lacks required permissions |
| `tool_permission(*permissions)` | Decorator | Attach permission requirements to a tool function |
| `get_permissions(func)` | Function | Get permissions for a tool (defaults to READ) |
| `filter_tools_by_permission(tools, granted)` | Function | Filter tools to those allowed by granted permissions |
| `enforce_tools_permissions(tools, granted)` | Function | Wrap tools with runtime permission checking |
| `ToolSelector(tools, ...)` | Class | LLM-driven tool selection from a large catalog |
| `func_to_description(func)` | Function | Generate human-readable description from function signature |

### `agentic_patterns.core.workspace`

| Name | Kind | Description |
|---|---|---|
| `WorkspaceError` | Exception | Invalid paths, missing files, traversal attempts |
| `workspace_to_host_path(sandbox_path)` | Function | Convert `/workspace/...` path to host filesystem path |
| `host_to_workspace_path(host_path)` | Function | Convert host path to `/workspace/...` path |
| `write_to_workspace(sandbox_path, content)` | Function | Write str or bytes to workspace |
| `read_from_workspace(sandbox_path)` | Function | Read text content from workspace |
| `list_workspace_files(pattern)` | Function | List files matching glob pattern |
| `store_result(content, content_type)` | Function | Store content with auto-generated filename |
| `clean_up_session()` | Function | Delete workspace files and reset compliance flags |

Async variants (`read_from_workspace_async`, `write_to_workspace_async`, `store_result_async`) are available for all I/O functions.

### `agentic_patterns.tools.dynamic`

| Name | Kind | Description |
|---|---|---|
| `get_param_signature(param_name, param_default)` | Function | Generate parameter signature string from name and default value |
| `generate_param_docs(parameters)` | Function | Generate Args-style docstring from parameter dict |

### `agentic_patterns.core.context.decorators`

| Name | Kind | Description |
|---|---|---|
| `context_result(config_name, save)` | Decorator | Auto-truncate and persist large tool results |

## Examples

See the notebooks in `agentic_patterns/examples/tools/`:

- `example_tools.ipynb` -- basic tool use with arithmetic functions
- `example_structured_outputs.ipynb` -- constraining output to Pydantic schemas
- `example_tool_selection.ipynb` -- manual selection and `ToolSelector`
- `example_tool_permissions.ipynb` -- construction-time filtering and runtime enforcement
- `example_workspace.ipynb` -- path translation, user isolation, write-and-summarize
