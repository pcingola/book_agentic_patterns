# Plan: REPL Core Library

## Context

The "Execution Infrastructure" chapter describes a REPL pattern for agents to execute Python code iteratively in a stateful, process-isolated environment. A reference implementation exists at `/Users/kqrw311/aixplore/mcp-repl`. We bring the core notebook/cell engine into `agentic_patterns/core/repl/`, replacing `aixtools` with `agentic_patterns.core` equivalents, and replacing the weak `unshare` + `sudo mount` isolation with a proper sandbox abstraction backed by bubblewrap (`bwrap`). No MCP server layer.

## Key Design Change: Sandbox Abstraction

The reference implementation mixes IPC and isolation concerns inside `run_code_in_subprocess()`. We split this into:

1. **Sandbox abstraction** (`sandbox.py`): Abstract base with two implementations
2. **Executor module** (`executor.py`): Standalone script that runs inside the sandbox

```
Cell._execute_sync()
    |
    v
Sandbox.execute(code, namespace, imports, funcdefs, timeout, ...)
    |
    +-- SandboxBubblewrap (Linux production)
    |     bwrap --ro-bind /usr /usr \
    |           --bind <workspace> /workspace \
    |           --unshare-net (if private data) \
    |           --unshare-pid \
    |           -- python3 -m agentic_patterns.core.repl.executor <temp_dir>
    |
    +-- SandboxProcess (macOS / development fallback)
          multiprocessing.Process + Pipe (current reference approach)
```

**Why bubblewrap over the reference approach:**
- No root/sudo required (uses user namespaces)
- Real filesystem isolation (cell code only sees `/workspace`, not host FS)
- Network blocking via `--unshare-net` when PrivateData is active
- PID namespace isolation (`--unshare-pid`)
- No `DATA_DIR` unmount hacks

**PrivateData integration:**
- `SandboxBubblewrap`: checks `session_has_private_data()` -- if true, adds `--unshare-net` to block all outbound network
- `SandboxProcess`: best-effort only (injects `__private_data__` flag into namespace, no real network blocking)

## Target Location

`agentic_patterns/core/repl/` -- 13 files.

## Files

### Copied with import adaptation only (no logic changes)

These files change only `mcp_repl.notebook.` imports to `agentic_patterns.core.repl.`:

| File | Source | Notes |
|------|--------|-------|
| `enums.py` | `notebook/enums.py` | As-is, no imports to change |
| `image.py` | `notebook/image.py` | As-is, no internal imports |
| `cell_output.py` | `notebook/cell_output.py` | Change internal imports |
| `matplotlib_backend.py` | `notebook/matplotlib_backend.py` | Change internal imports |
| `openpyxl_handler.py` | `notebook/openpyxl_handler.py` | As-is, no internal imports |
| `api_models.py` | `notebook/api_models.py` | Change internal imports |

### New or significantly adapted files

**`config.py`** -- Constants only:
```python
DEFAULT_CELL_TIMEOUT = 30
MAX_CELLS = 100
SERVICE_NAME = "mcp_repl"
```

**`sandbox.py`** -- New file, sandbox abstraction:
- `Sandbox` (ABC): `async execute(code, namespace, imports, funcdefs, timeout, user_id, session_id) -> SubprocessResult`
- `SandboxBubblewrap(Sandbox)`: Linux production sandbox using `bwrap`
  - Writes pickled input (namespace, code, imports, funcdefs) to temp dir
  - Builds bwrap command: `--ro-bind` for Python/system libs, `--bind` for workspace, `--unshare-pid`, `--unshare-net` if private data
  - Runs `python3 -m agentic_patterns.core.repl.executor <temp_dir>` inside bwrap
  - Reads pickled `SubprocessResult` from temp dir
  - Timeout via `asyncio.wait_for` + process kill
- `SandboxProcess(Sandbox)`: macOS/dev fallback using `multiprocessing.Process` + `Pipe`
  - Essentially the current `_execute_sync` logic from reference `cell.py`
- `get_sandbox() -> Sandbox`: Factory -- returns `SandboxBubblewrap` if `bwrap` is on PATH, else `SandboxProcess`

**`executor.py`** -- New file, runs inside sandbox:
- Entry point: `python -m agentic_patterns.core.repl.executor <temp_dir>`
- Reads pickled input from `<temp_dir>/input.pkl`
- Restores workbook references
- Configures matplotlib
- Replays imports and function definitions
- Executes cell code, captures last expression
- Captures stdout/stderr and matplotlib figures
- Filters namespace to picklable objects
- Writes pickled `SubprocessResult` to `<temp_dir>/output.pkl`

**`cell_utils.py`** -- Adapted from reference, slimmed down:
- Keep: `SubprocessResult`, `is_picklable`, `filter_picklable_namespace`, `extract_function_definitions`, `execute_and_capture_last_expression`, `get_temp_workbooks_dir`, `cleanup_temp_workbooks`, unpicklable hints
- Remove: `run_code_in_subprocess` (moved to `executor.py` and `sandbox.py`)
- Replace `aixtools` imports with `agentic_patterns.core` equivalents
- Replace `CONTAINER_WORKSPACE_PATH` with `PurePosixPath(SANDBOX_PREFIX)`

**`cell.py`** -- Adapted from reference:
- Replace `get_session_id_tuple()` with `(get_user_id(), get_session_id())`
- `_execute_sync()` now calls `sandbox.execute()` instead of directly spawning `multiprocessing.Process`
- Remove process management code (moved to sandbox)

**`notebook.py`** -- Adapted from reference:
- Replace `get_session_id_tuple()` / `get_workspace_path()` with `agentic_patterns.core.user_session` + `agentic_patterns.core.config.config.WORKSPACE_DIR`
- Remove `fastmcp.Context` dependency
- `_get_session_notebook_dir()` uses `WORKSPACE_DIR / user_id / session_id / SERVICE_NAME`

**`__init__.py`** -- Exports main classes.

## Import Mapping

| Reference (`aixtools`) | This project |
|---|---|
| `get_logger(__name__)` | `logging.getLogger(__name__)` |
| `get_session_id_tuple()` | `(get_user_id(), get_session_id())` from `agentic_patterns.core.user_session` |
| `get_workspace_path(ctx)` | `WORKSPACE_DIR / user_id / session_id` from `agentic_patterns.core.config.config` |
| `CONTAINER_WORKSPACE_PATH` | `PurePosixPath(SANDBOX_PREFIX)` from `agentic_patterns.core.config.config` |
| `DATA_DIR` | Not needed (bwrap doesn't mount it) |
| `fastmcp.Context` | Removed |

## Existing code reused

- `agentic_patterns/core/user_session.py`: `get_user_id()`, `get_session_id()`
- `agentic_patterns/core/config/config.py`: `WORKSPACE_DIR`, `SANDBOX_PREFIX`, `DATA_DIR`
- `agentic_patterns/core/compliance/private_data.py`: `session_has_private_data()`
- `agentic_patterns/core/workspace.py`: `workspace_to_host_path()` (for path translation if needed)

## Verification

1. Create a notebook, add cells, verify namespace persistence across cells
2. Verify subprocess isolation (cell crash doesn't crash parent)
3. Verify timeout handling
4. On Linux: verify bwrap sandbox restricts filesystem to workspace only
5. On macOS: verify fallback to process-based execution
6. Run `scripts/lint.sh`
