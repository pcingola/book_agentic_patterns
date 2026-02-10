# Refactor: Extract MCP Business Logic into Toolkits

## Goal

Enable MCP server tools to be used directly by PydanticAI agents without running the MCP server.

## Architecture

Three top-level peer directories, each with a single responsibility:

```
toolkits/*            Business logic. No framework dependency.
                      Pure Python: models, operations, I/O, config.
    |
    +-------> tools/*               PydanticAI agent tool wrappers.
    |                               Plain functions passed to Agent(tools=[...]).
    |
    +-------> mcp/*/tools.py        MCP server tool wrappers.
                                    Adds ctx: Context, @mcp.tool(), error conversion.
```

This is the same pattern already working for data connectors:

```
core/connectors/*  -->  tools/*             (file.py, csv.py, json.py, sql.py, openapi.py)
                   -->  mcp/*/tools.py      (file_ops, sql)
```

Connectors (`core/connectors/`) are for data source access. Toolkits are for everything else: domain logic, operations, services.

Tool infrastructure (permissions, selection, `func_to_description`) stays in `core/tools/` -- that is framework plumbing, not wrappers.

## Directory Layout (after refactor)

```
agentic_patterns/
|
+-- toolkits/                              <-- business logic lives here
|   +-- todo/
|   |   +-- models.py
|   |   +-- operations.py
|   |
|   +-- data_analysis/
|   |   +-- config.py
|   |   +-- enums.py
|   |   +-- models.py
|   |   +-- display.py
|   |   +-- io.py
|   |   +-- ml_helpers.py
|   |   +-- executor.py
|   |   +-- ops_eda.py
|   |   +-- ops_stats.py
|   |   +-- ops_transform.py
|   |   +-- ops_classification.py
|   |   +-- ops_regression.py
|   |   +-- ops_feature_importance.py
|   |
|   +-- data_viz/
|   |   +-- config.py
|   |   +-- enums.py
|   |   +-- models.py
|   |   +-- io.py
|   |   +-- executor.py
|   |   +-- ops_basic.py
|   |   +-- ops_distribution.py
|   |   +-- ops_categorical.py
|   |   +-- ops_matrix.py
|   |
|   +-- format_conversion/
|       +-- enums.py
|       +-- ingest.py
|       +-- export.py
|       +-- converter.py
|
+-- tools/                                 <-- PydanticAI wrappers (top-level peer)
|   +-- file.py                            wraps core/connectors/file.py
|   +-- csv.py                             wraps core/connectors/csv.py
|   +-- json.py                            wraps core/connectors/json.py
|   +-- sql.py                             wraps core/connectors/sql/
|   +-- nl2sql.py                          wraps core/connectors/sql/ (NL2SQL-specific)
|   +-- openapi.py                         wraps core/connectors/openapi/
|   +-- todo.py                            wraps toolkits/todo/
|   +-- data_analysis.py                   wraps toolkits/data_analysis/
|   +-- data_viz.py                        wraps toolkits/data_viz/
|   +-- format_conversion.py               wraps toolkits/format_conversion/
|   +-- dynamic.py                         shared dynamic tool generation helpers
|
+-- core/
|   +-- tools/                             <-- infrastructure only (no wrappers)
|   |   +-- permissions.py                 ToolPermission, @tool_permission, filtering
|   |   +-- selection.py                   ToolSelector (AI-driven tool selection)
|   |   +-- utils.py                       func_to_description
|   +-- connectors/                        unchanged (data sources only)
|   ...
|
+-- mcp/                                   <-- thin wrappers only
|   +-- file_ops/
|   |   +-- server.py
|   |   +-- tools.py                       delegates to core/connectors/
|   +-- sql/
|   |   +-- server.py
|   |   +-- tools.py                       delegates to core/connectors/sql/
|   +-- todo/
|   |   +-- server.py
|   |   +-- tools.py                       delegates to toolkits/todo/
|   +-- data_analysis/
|   |   +-- server.py
|   |   +-- tools.py                       delegates to toolkits/data_analysis/
|   +-- data_viz/
|   |   +-- server.py
|   |   +-- tools.py                       delegates to toolkits/data_viz/
|   +-- format_conversion/
|   |   +-- server.py
|   |   +-- tools.py                       delegates to toolkits/format_conversion/
|   +-- template/                          unchanged (teaching example)
|   ...
```

## What Changes per Module

### todo

`toolkits/todo/models.py` -- move from `mcp/todo/models.py` as-is.

`toolkits/todo/operations.py` -- extract from `mcp/todo/tools.py`: the cache (`_cache`), `_cache_key()`, `_get_task_list()`, `_new_task_list()`, `_save()`, `_add_one()`. Expose as plain functions: `add_task()`, `add_tasks()`, `create_task_list()`, `delete_task()`, `show_task_list()`, `update_task_status()`. No MCP imports, raise `ValueError`/`KeyError`.

`tools/todo.py` -- `get_all_tools()` returning plain functions that call `toolkits.todo.operations`.

`mcp/todo/tools.py` -- thin wrapper: import from `toolkits.todo.operations`, add `ctx.info()`, convert exceptions to `ToolRetryError`.

### data_analysis

Move all files except `server.py` and `tools.py` from `mcp/data_analysis/` to `toolkits/data_analysis/`.

In `toolkits/data_analysis/executor.py`, replace `ToolRetryError`/`ToolFatalError` with plain exceptions (`ValueError`, `RuntimeError`).

`tools/data_analysis.py` -- `get_all_tools()` generating PydanticAI tool functions from the operation registry. Uses shared helpers from `tools/dynamic.py`.

`mcp/data_analysis/tools.py` -- thin wrapper: imports from `toolkits.data_analysis`, adds `ctx: Context`, `@mcp.tool()`, exception conversion.

### data_viz

Same pattern as data_analysis. Move all files except `server.py`, `tools.py`, `__init__.py`.

In `toolkits/data_viz/executor.py`, replace MCP errors with plain exceptions.

`tools/data_viz.py` -- `get_all_tools()` from plot operation registry.

`mcp/data_viz/tools.py` -- thin wrapper.

### Shared: dynamic tool generation

`_get_param_signature()`, `_generate_param_docs()`, `_generate_tool_function()` are duplicated between `mcp/data_analysis/tools.py` and `mcp/data_viz/tools.py`. Extract into `tools/dynamic.py`. Both MCP wrappers and PydanticAI wrappers import from there.

### Promote existing connector wrappers

Move existing PydanticAI wrapper files from `core/tools/` to `tools/`: file.py, csv.py, json.py, sql.py, nl2sql.py, openapi.py. Update imports project-wide.

`core/tools/` retains only infrastructure: permissions.py, selection.py, utils.py.

### template (no change)

Teaching example. Leave as-is.

## Execution Order

1. `todo` -- simplest, fewest files
2. `data_analysis` -- mostly file moves, then rewire imports
3. `data_viz` -- mirrors data_analysis
4. `dynamic.py` -- deduplicate shared helpers
5. Promote existing connector wrappers from `core/tools/` to `tools/`
6. Fix imports project-wide, lint, test

## Tests

Existing tests keep passing (MCP public API unchanged). New unit tests for toolkits can be added later.
