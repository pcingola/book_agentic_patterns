# Execution Infrastructure

Infrastructure for running agent-generated code safely: process sandboxes, a stateful REPL, Docker-based container sandboxes, and MCP server network isolation driven by data sensitivity.

## Process Sandbox

`core/process_sandbox.py` provides a generic sandbox for running commands in isolated environments.

### Data Models

`BindMount(source, target, readonly)` maps a host `Path` to a path visible inside the sandbox. `SandboxResult(exit_code, stdout, stderr, timed_out)` holds the command output.

### Sandbox Implementations

`Sandbox` is the abstract base class with a single `run()` method:

```python
result = await sandbox.run(
    command=["python3", "-m", "my_module", "/tmp/workdir"],
    bind_mounts=[BindMount(Path("/data/workspace"), "/workspace")],
    timeout=30,
    isolate_network=True,
    isolate_pid=True,
    cwd="/workspace",
    env={"KEY": "value"},
)
```

`SandboxBubblewrap` is the Linux production implementation using bubblewrap (`bwrap`). It creates a minimal filesystem view with read-only system mounts (`/usr`, `/lib`, `/bin`, etc.), a private `/tmp`, and only the bind mounts explicitly granted. The Python prefix is mounted read-only so installed packages remain importable. PID and network namespaces can be unshared independently via `--unshare-pid` and `--unshare-net`. Timeout enforcement uses `asyncio.wait_for` -- on expiry, the process is killed and the result has `timed_out=True`.

`SandboxSubprocess` is the macOS/development fallback that runs commands as plain subprocesses with no isolation. Same timeout enforcement, but no filesystem or network restrictions.

### Factory

```python
from agentic_patterns.core.process_sandbox import get_sandbox

sandbox = get_sandbox()  # SandboxBubblewrap if bwrap on PATH, else SandboxSubprocess
```

## Docker Sandbox

`core/sandbox/` provides container-based sandboxing with Docker for production multi-tenant deployments.

### Configuration

`ContainerConfig` defines the container settings:

```python
from agentic_patterns.core.sandbox.container_config import ContainerConfig

config = ContainerConfig(
    image="my-sandbox:latest",    # default from SANDBOX_DOCKER_IMAGE
    cpu_limit=1.0,                # default from SANDBOX_CPU_LIMIT
    memory_limit="512m",          # default from SANDBOX_MEMORY_LIMIT
    working_dir="/workspace",
    network_mode=NetworkMode.FULL,
    read_only_mounts={"/host/skills": "/skills"},
    user="nobody",
)
```

Defaults are in `core/sandbox/config.py`: `SANDBOX_DOCKER_IMAGE`, `SANDBOX_CPU_LIMIT`, `SANDBOX_MEMORY_LIMIT`, `SANDBOX_COMMAND_TIMEOUT`, `SANDBOX_CONTAINER_PREFIX`.

### Network Mode

`NetworkMode` is an enum driven by the `PrivateData` compliance module:

```python
from agentic_patterns.core.sandbox.network_mode import NetworkMode, get_network_mode

mode = get_network_mode(user_id, session_id)
# NetworkMode.FULL ("bridge") -- normal
# NetworkMode.NONE ("none")   -- session has private data
```

This is a one-way ratchet: once private data enters a session, network access never returns.

### SandboxManager

`SandboxManager` manages Docker containers per user session:

```python
from agentic_patterns.core.sandbox.manager import SandboxManager

manager = SandboxManager(read_only_mounts={"/host/skills": "/skills"})

# Ephemeral (default) -- create, run, destroy
exit_code, output = manager.execute_command(user_id, session_id, "python script.py")

# Persistent -- reuse container across calls
exit_code, output = manager.execute_command(user_id, session_id, "ls /workspace", persistent=True)

# Close a persistent session
manager.close_session(user_id, session_id)
```

On every access to a persistent session, the manager checks `get_network_mode()`. If private data appeared since the container was created, the container is stopped and recreated with `network_mode="none"`. The workspace directory survives recreation because it is a bind mount on the host filesystem.

### SandboxSession

`SandboxSession` tracks the container lifecycle for a `(user_id, session_id)` pair. It records the container ID, name, network mode, config, data directory, and timestamps. `touch()` updates the `last_active_at` timestamp on every command execution.

### Tool Wrappers

PydanticAI tool (`tools/sandbox.py`):

```python
from agentic_patterns.tools.sandbox import get_all_tools

tools = get_all_tools()  # [sandbox_execute]
agent = Agent("model", tools=tools)
```

`sandbox_execute(command, timeout)` runs a shell command in the Docker sandbox and returns the exit code and output. Uses `asyncio.to_thread()` to avoid blocking the event loop.

MCP server (`mcp/sandbox/`): same single `execute` tool, converts `DockerException`/`NotFound` to `ToolFatalError`.

## REPL

`core/repl/` provides a stateful, notebook-like execution environment for iterative code. Each cell runs in a fresh subprocess (optionally sandboxed with bubblewrap) while preserving the illusion of a continuous namespace through pickle-based IPC.

### Notebook and Cell

A `Notebook` is scoped to a `(user_id, session_id)` pair and manages a list of `Cell` objects, a shared namespace, accumulated import statements, and function definitions.

```python
from agentic_patterns.core.repl.notebook import Notebook

nb = Notebook.load(user_id, session_id)  # loads from disk or creates new
cell = await nb.add_cell("x = 42", execute=True, timeout=30)
cell = await nb.add_cell("print(x)", execute=True)  # x is available
nb.delete_cell(0)
nb.clear()
nb.save_as_ipynb(Path("/workspace/output.ipynb"))
```

Each `Cell` tracks its code, state (`CellState`: IDLE, RUNNING, COMPLETED, ERROR, TIMEOUT), typed outputs, execution count, and timing. Outputs are `CellOutput` objects with an `OutputType` (TEXT, ERROR, HTML, IMAGE, DATAFRAME).

### Execution Model

Cell execution follows this flow:

1. `Cell.execute()` offloads to a worker thread via `asyncio.to_thread()` so the event loop stays responsive.
2. Inside the thread, a private event loop runs the async sandbox call.
3. The sandbox function (`repl/sandbox.py`) pickles the input (code, namespace, imports, function definitions) to a temp directory, runs the executor subprocess inside the generic sandbox, and reads the pickled output back.
4. The executor (`repl/executor.py`) restores the namespace, replays imports and function definitions, executes the cell code, captures stdout/stderr/matplotlib figures, filters the namespace to picklable objects, and writes the result.
5. After execution, the notebook parses the cell code via AST to extract new import statements and function definitions, which are accumulated and replayed before subsequent cells.

Network isolation is automatic: `execute_in_sandbox` checks `session_has_private_data(user_id, session_id)` and sets `isolate_network=True` when private data is present.

### Persistence

Notebooks are persisted as JSON at `WORKSPACE_DIR / user_id / session_id / mcp_repl / cells.json`. The notebook saves after every operation (add, execute, delete, clear). It can be exported to Jupyter `.ipynb` format via `save_as_ipynb()`.

### Tool Wrappers

PydanticAI tools (`tools/repl.py`):

```python
from agentic_patterns.tools.repl import get_all_tools

tools = get_all_tools()
# repl_execute_cell, repl_rerun_cell, repl_show_notebook, repl_show_cell,
# repl_delete_cell, repl_clear_notebook, repl_export_ipynb
```

MCP server (`mcp/repl/`): same seven tools, converts `ValueError`/`IndexError` to `ToolRetryError`.

## MCP Server Isolation

The `MCPServerPrivateData` class in `core/mcp/servers.py` implements dual-instance MCP server switching based on data sensitivity. It runs two connections to the same MCP server -- one normal, one network-isolated -- and routes all calls through the isolated instance once private data appears.

### Configuration

Add `url_isolated` to the MCP server config in `config.yaml`:

```yaml
mcp_servers:
  data_tools:
    type: client
    url: "http://data-tools:8000/mcp"
    url_isolated: "http://data-tools-isolated:8000/mcp"
    read_timeout: 60
```

The `MCPClientConfig` model has the optional `url_isolated` field. When set, `get_mcp_client()` returns an `MCPServerPrivateData` instance; when absent, it returns a plain `MCPServerStrict`.

### Client-Side Switching

```python
from agentic_patterns.core.mcp.factories import get_mcp_client

server = get_mcp_client("data_tools")  # MCPServerPrivateData if url_isolated present

async with server:  # opens both connections
    # all calls route to normal instance while session_has_private_data() is False
    # once private data appears, all calls route to isolated instance
    pass
```

`MCPServerPrivateData` extends `MCPServerStrict` and is a drop-in replacement in any toolset list. Both connections are alive for the entire session -- switching happens internally via `_target()` with no reconnection. The switch is a one-way ratchet. It reads session identity from contextvars (set by middleware at request boundaries).

### MCPServerStrict

`MCPServerStrict` extends PydanticAI's `MCPServerStreamableHTTP` and intercepts fatal tool errors. When a tool response starts with `[FATAL]`, it raises `RuntimeError` (aborting the agent run) instead of `ModelRetry` (which would retry). Non-fatal errors pass through as normal `ModelRetry` instances.

### Deployment

In production, run two instances of the same MCP server image:

```yaml
services:
  data-tools:
    image: my-mcp-server:latest
    networks: [bridge]
    volumes: [workspace:/workspace]

  data-tools-isolated:
    image: my-mcp-server:latest
    network_mode: "none"
    volumes: [workspace:/workspace]
```

The server code is identical between instances. Tools that require external connectivity fail with connection errors in the isolated instance.

## Skill Sandbox

Skills are developer-authored scripts that the agent can invoke but not modify. The `SandboxManager` supports `read_only_mounts` that map host directories to container paths with Docker's `ro` flag.

```python
from agentic_patterns.core.sandbox.manager import SandboxManager

read_only_mounts = {}
for meta in registry.list_all():
    scripts_dir = meta.path / "scripts"
    if scripts_dir.exists():
        read_only_mounts[str(scripts_dir)] = f"/skills/{meta.path.name}/scripts"

manager = SandboxManager(read_only_mounts=read_only_mounts)
manager.execute_command(user_id, session_id, f"python /skills/{skill_name}/scripts/{script_name}")
```

Inside the container, `/workspace` is the agent's writable scratch space, and `/skills` is an immutable library of developer-authored scripts. The `ro` flag is enforced at the filesystem level by Docker.
