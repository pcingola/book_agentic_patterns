# Refactor: Extract MCP Business Logic into Toolkits

## Goal

Enable MCP server tools to be used directly by PydanticAI agents without running the MCP server.

## Architecture

Three layers, each with a single responsibility:

```
toolkits/*            Business logic. No framework dependency.
                      Pure Python: models, operations, I/O, config.
        |
        +-------> core/tools/*        PydanticAI agent tool wrappers.
        |                             Plain functions passed to Agent(tools=[...]).
        |
        +-------> mcp/*/tools.py      MCP server tool wrappers.
                                      Adds ctx: Context, @mcp.tool(), error conversion.
```

This is the same pattern already working for data connectors:

```
core/connectors/*  -->  core/tools/*        (file.py, csv.py, json.py, sql.py, openapi.py)
                   -->  mcp/*/tools.py      (file_ops, sql)
```

Connectors are specifically for data source access. Toolkits are for everything else: domain logic, operations, services.

## Directory Layout (after refactor)

```
agentic_patterns/
|
+-- toolkits/                              <-- NEW: business logic lives here
|   +-- todo/
|   |   +-- models.py                      <-- from mcp/todo/models.py
|   |   +-- operations.py                  <-- extracted from mcp/todo/tools.py
|   |
|   +-- data_analysis/
|   |   +-- config.py                      <-- from mcp/data_analysis/config.py
|   |   +-- enums.py                       <-- from mcp/data_analysis/enums.py
|   |   +-- models.py                      <-- from mcp/data_analysis/models.py
|   |   +-- display.py                     <-- from mcp/data_analysis/display.py
|   |   +-- io.py                          <-- from mcp/data_analysis/io.py
|   |   +-- ml_helpers.py                  <-- from mcp/data_analysis/ml_helpers.py
|   |   +-- executor.py                    <-- from mcp/data_analysis/executor.py (remove MCP error imports)
|   |   +-- ops_eda.py                     <-- from mcp/data_analysis/ops_eda.py
|   |   +-- ops_stats.py                   <-- from mcp/data_analysis/ops_stats.py
|   |   +-- ops_transform.py              <-- from mcp/data_analysis/ops_transform.py
|   |   +-- ops_classification.py          <-- from mcp/data_analysis/ops_classification.py
|   |   +-- ops_regression.py              <-- from mcp/data_analysis/ops_regression.py
|   |   +-- ops_feature_importance.py      <-- from mcp/data_analysis/ops_feature_importance.py
|   |
|   +-- data_viz/
|       +-- config.py                      <-- from mcp/data_viz/config.py
|       +-- enums.py                       <-- from mcp/data_viz/enums.py
|       +-- models.py                      <-- from mcp/data_viz/models.py
|       +-- io.py                          <-- from mcp/data_viz/io.py
|       +-- executor.py                    <-- from mcp/data_viz/executor.py (remove MCP error imports)
|       +-- ops_basic.py                   <-- from mcp/data_viz/ops_basic.py
|       +-- ops_distribution.py            <-- from mcp/data_viz/ops_distribution.py
|       +-- ops_categorical.py             <-- from mcp/data_viz/ops_categorical.py
|       +-- ops_matrix.py                  <-- from mcp/data_viz/ops_matrix.py
|
+-- core/
|   +-- tools/                             <-- PydanticAI wrappers (some already exist)
|   |   +-- file.py                        exists (wraps core/connectors/file.py)
|   |   +-- csv.py                         exists (wraps core/connectors/csv.py)
|   |   +-- json.py                        exists (wraps core/connectors/json.py)
|   |   +-- sql.py                         exists (wraps core/connectors/sql/)
|   |   +-- openapi.py                     exists (wraps core/connectors/openapi/)
|   |   +-- todo.py                        <-- NEW (wraps toolkits/todo/)
|   |   +-- data_analysis.py               <-- NEW (wraps toolkits/data_analysis/)
|   |   +-- data_viz.py                    <-- NEW (wraps toolkits/data_viz/)
|   |   +-- dynamic.py                     <-- NEW (shared dynamic tool generation helpers)
|   |   ...
|   +-- connectors/                        unchanged (data sources only)
|   ...
|
+-- mcp/                                   <-- after refactor: thin wrappers only
|   +-- file_ops/
|   |   +-- server.py
|   |   +-- tools.py                       already delegates to core/connectors/
|   +-- sql/
|   |   +-- server.py
|   |   +-- tools.py                       already delegates to core/connectors/sql/
|   +-- todo/
|   |   +-- server.py
|   |   +-- tools.py                       <-- SIMPLIFY: delegate to toolkits/todo/
|   +-- data_analysis/
|   |   +-- server.py
|   |   +-- tools.py                       <-- SIMPLIFY: delegate to toolkits/data_analysis/
|   +-- data_viz/
|   |   +-- server.py
|   |   +-- tools.py                       <-- SIMPLIFY: delegate to toolkits/data_viz/
|   +-- template/                          unchanged (teaching example)
|   ...
```

## What Changes per Module

### todo

`toolkits/todo/models.py` -- move from `mcp/todo/models.py` as-is.

`toolkits/todo/operations.py` -- extract from `mcp/todo/tools.py`: the cache (`_cache`), `_cache_key()`, `_get_task_list()`, `_new_task_list()`, `_save()`, `_add_one()`. Expose as plain functions: `add_task()`, `add_tasks()`, `create_task_list()`, `delete_task()`, `show_task_list()`, `update_task_status()`. No MCP imports, raise `ValueError`/`KeyError`.

`core/tools/todo.py` -- `get_all_tools()` returning plain functions that call `toolkits.todo.operations`.

`mcp/todo/tools.py` -- thin wrapper: import from `toolkits.todo.operations`, add `ctx.info()`, convert exceptions to `ToolRetryError`.

### data_analysis

Move all files except `server.py` and `tools.py` from `mcp/data_analysis/` to `toolkits/data_analysis/`.

In `toolkits/data_analysis/executor.py`, replace `ToolRetryError`/`ToolFatalError` with plain exceptions (`ValueError`, `RuntimeError`).

`core/tools/data_analysis.py` -- `get_all_tools()` generating PydanticAI tool functions from the operation registry. Uses shared helpers from `core/tools/dynamic.py`.

`mcp/data_analysis/tools.py` -- thin wrapper: imports from `toolkits.data_analysis`, adds `ctx: Context`, `@mcp.tool()`, exception conversion.

### data_viz

Same pattern as data_analysis. Move all files except `server.py`, `tools.py`, `__init__.py`.

In `toolkits/data_viz/executor.py`, replace MCP errors with plain exceptions.

`core/tools/data_viz.py` -- `get_all_tools()` from plot operation registry.

`mcp/data_viz/tools.py` -- thin wrapper.

### Shared: dynamic tool generation

`_get_param_signature()`, `_generate_param_docs()`, `_generate_tool_function()` are duplicated between `mcp/data_analysis/tools.py` and `mcp/data_viz/tools.py`. Extract into `core/tools/dynamic.py`. Both MCP wrappers and PydanticAI wrappers import from there.

### template (no change)

Teaching example. Leave as-is.

## Execution Order

1. `todo` -- simplest, fewest files
2. `data_analysis` -- mostly file moves, then rewire imports
3. `data_viz` -- mirrors data_analysis
4. `dynamic.py` -- deduplicate shared helpers
5. Fix imports project-wide, lint, test

## Tests

Existing tests keep passing (MCP public API unchanged). New unit tests for toolkits can be added later.
