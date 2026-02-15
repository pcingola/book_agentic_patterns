# REPL Improvements Plan

## Context

Two problems with the current REPL sandbox:

1. The pickle files (`input.pkl`, `output.pkl`) used for IPC between parent and executor subprocess live in ephemeral `/tmp/repl_XXXXXXXX/` directories and are deleted immediately after execution. This makes debugging impossible -- you cannot examine what state was sent to the executor or what came back.

2. On macOS (no bubblewrap), `SandboxSubprocess` runs the executor as a plain subprocess with zero filesystem isolation. The process can read/write anywhere on the host filesystem.

To answer the questions posed: yes, `import_statements` (list of source strings) and `function_definitions` are both serialized inside `input.pkl` alongside the namespace, code, user_id, session_id, and workspace_path. And yes, there is one `input.pkl` per cell execution (overwritten on re-execution of the same cell).

## Changes

### 1. Persist pkl files per cell

Replace the ephemeral `/tmp/repl_XXXXXXXX/` temp directory with persistent pkl files inside the repl workspace:

```
WORKSPACE_DIR/<user_id>/<session_id>/.repl/<cell_id>_input.pkl
WORKSPACE_DIR/<user_id>/<session_id>/.repl/<cell_id>_output.pkl
```

No separate subdirectory per cell -- we only store two files per cell (input/output), so a flat layout with cell_id prefix is simpler. The `.repl` directory is hidden (dotfile convention) to avoid polluting the user-visible workspace.

This directory is already inside the workspace mount (`/workspace/.repl/` from the executor's perspective), so no additional bind mounts are needed for any sandbox backend.

Files to change:
- `agentic_patterns/core/repl/sandbox.py`: Replace `tempfile.mkdtemp()` with the `.repl` dir under the workspace. Remove the `shutil.rmtree()` cleanup. The function signature gains a `cell_id` parameter; pkl files are named `<cell_id>_input.pkl` / `<cell_id>_output.pkl`.
- `agentic_patterns/core/repl/cell.py`: Pass `self.id` (cell UUID) to `execute_in_sandbox()`.
- `agentic_patterns/core/repl/notebook.py`: On `clear()`, remove the `.repl` directory. On `delete_cell()`, remove the two pkl files for that cell.

### 2. Docker sandbox for REPL (when bwrap is unavailable)

Reuse the existing `core/sandbox/SandboxManager` to run the REPL executor inside a Docker container.

Execution flow in `repl/sandbox.py`:

```
if bwrap available:
    use SandboxBubblewrap (existing behavior)
elif docker available:
    use SandboxManager with persistent container per user/session
    run: python -m agentic_patterns.core.repl.executor /workspace/.repl <cell_id>
else:
    SandboxSubprocess fallback (log a warning about no isolation)
```

Since pkl files now live inside the workspace (change 1), they are automatically accessible inside the Docker container via the existing `/workspace` volume mount. No extra mounts needed per cell.

The project source code is mounted read-only so the executor can import `agentic_patterns`. `PYTHONPATH` is set in the container environment.

Files to change:
- `agentic_patterns/core/repl/sandbox.py`: Add Docker code path between bwrap and subprocess. Use `SandboxManager.execute_command(persistent=True)` with the Python executor command.
- `agentic_patterns/core/sandbox/config.py`: Add `REPL_DOCKER_IMAGE` config variable (defaults to `agentic-patterns-repl:latest`).
- `agentic_patterns/core/sandbox/manager.py`: Minor adaptation -- `_run_command` currently hardcodes `bash -c`. Extend to accept a raw command list (needed to run `python -m ...` directly, though `bash -c "python -m ..."` works too).

### 3. Docker image with pre-installed packages

A custom Docker image based on `python:3.12-slim` with all packages a REPL user would need.

Pre-installed packages:
- Data manipulation: pandas, polars, numpy, scipy, pyarrow
- ML / statistics: scikit-learn, statsmodels, xgboost, lightgbm
- Visualization: matplotlib, seaborn, plotly
- Office / document formats: openpyxl, xlsxwriter, python-docx, python-pptx
- Data formats: pyyaml, lxml, pillow
- Database: sqlalchemy, aiosqlite
- HTTP / web: requests, httpx, beautifulsoup4
- NLP: nltk
- Math / graphs: sympy, networkx
- Utilities: tqdm, tabulate, rich, pydantic

The `agentic_patterns` code is NOT baked into the image (mounted read-only at runtime), so the image only needs rebuilding when package dependencies change.

New files:
- `docker/repl/Dockerfile`
- `docker/repl/requirements.txt` (pinned versions of the packages above)
- `scripts/build_repl_image.sh`

## Verification

1. Run a cell that creates a file: verify `<cell_id>_input.pkl` and `<cell_id>_output.pkl` exist under `data/workspaces/<user>/<session>/.repl/`.
2. Unpickle `<cell_id>_input.pkl` and confirm it contains `code`, `namespace`, `import_statements`, `function_definitions`, etc.
3. Run a multi-cell notebook -- verify each cell has its own pair of pkl files with the accumulated state.
4. Build the Docker image via `scripts/build_repl_image.sh`.
5. With Docker running (and no bwrap), execute a cell that writes `open("test.txt", "w").write("hello")` -- verify the file appears in the workspace dir and NOT in the host's cwd.
6. Execute a cell with `import os; os.listdir("/etc")` -- verify it sees the container's `/etc`, not the host's.
