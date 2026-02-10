# Plan: PydanticAI Tools and MCP Servers for REPL and Sandbox

## Context

The REPL (`core/repl/`) and Docker Sandbox (`core/sandbox/`) are core infrastructure modules that currently have no agent-facing wrappers. CodeAct agents need direct access to the sandbox to execute code as their primary mode of action. The REPL provides stateful notebook-style Python execution. Both need PydanticAI tool wrappers (for direct agent use) and MCP servers (for MCP-based agent use).

## Files to Create (6 files)

### 1. `agentic_patterns/tools/repl.py` -- PydanticAI tools for REPL

Pattern: same as `tools/todo.py`. Single `get_all_tools() -> list` with closures. Module-level `_load_notebook()` helper reads user/session from contextvars.

Tools:
- `repl_execute_cell(code, timeout=30)` -- WRITE, `@context_result()` -- add and execute cell, return `str(cell)`
- `repl_rerun_cell(cell_number, timeout=30)` -- WRITE, `@context_result()` -- re-execute existing cell
- `repl_show_notebook()` -- READ, `@context_result(save=False)` -- show all cells
- `repl_show_cell(cell_number)` -- READ -- show single cell
- `repl_delete_cell(cell_number)` -- WRITE -- delete cell
- `repl_clear_notebook()` -- WRITE -- clear all cells and namespace
- `repl_export_ipynb(path)` -- WRITE -- export to .ipynb

### 2. `agentic_patterns/tools/sandbox.py` -- PydanticAI tools for Docker Sandbox

Pattern: same closure pattern. `SandboxManager()` created at `get_all_tools()` scope.

Tools:
- `sandbox_execute(command, timeout=30)` -- WRITE, `@context_result()` -- execute shell command, return exit code + output
- `sandbox_close_session()` -- WRITE -- stop and remove Docker container

### 3. `agentic_patterns/mcp/repl/server.py` -- MCP server for REPL

Pattern: `mcp = create_mcp_server("repl", instructions=...)` + `register_tools(mcp)`.

### 4. `agentic_patterns/mcp/repl/tools.py` -- MCP tools for REPL

Pattern: same as `mcp/todo/tools.py`. `register_tools(mcp)` with `@mcp.tool()`, `ctx: Context`, error conversion (`ValueError`/`IndexError` -> `ToolRetryError`), `ctx.info()` logging. Module-level `_load_notebook()` helper.

Same 7 tools as `tools/repl.py` (without `repl_` prefix since MCP tool names are scoped to the server).

### 5. `agentic_patterns/mcp/sandbox/server.py` -- MCP server for Docker Sandbox

Pattern: `mcp = create_mcp_server("sandbox", instructions=...)` + `register_tools(mcp)`.

### 6. `agentic_patterns/mcp/sandbox/tools.py` -- MCP tools for Docker Sandbox

Pattern: same as `mcp/todo/tools.py`. Module-level `_manager = SandboxManager()` singleton. `DockerException`/`NotFound` -> `ToolFatalError`.

Same 2 tools as `tools/sandbox.py` (without `sandbox_` prefix).

## Key References

- `agentic_patterns/tools/todo.py` -- PydanticAI tool wrapper pattern
- `agentic_patterns/mcp/todo/tools.py` -- MCP tool pattern
- `agentic_patterns/mcp/todo/server.py` -- MCP server pattern
- `agentic_patterns/core/repl/notebook.py` -- Notebook API (load, add_cell, execute_cell, delete_cell, clear, save_as_ipynb)
- `agentic_patterns/core/sandbox/manager.py` -- SandboxManager API (execute_command, close_session)
- `agentic_patterns/core/context/decorators.py` -- `@context_result()` decorator
- `agentic_patterns/core/user_session.py` -- `get_user_id()`, `get_session_id()`

## Verification

Run `scripts/lint.sh` to check for import/style issues. Optionally import the tools modules in a Python shell to verify they load without errors:
```
python -c "from agentic_patterns.tools.repl import get_all_tools; print(len(get_all_tools()))"
python -c "from agentic_patterns.tools.sandbox import get_all_tools; print(len(get_all_tools()))"
```
