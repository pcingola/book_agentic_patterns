# Plan: Sandbox Container Lifecycle -- Destroy by Default

## Context

`SandboxManager.execute_command()` calls `get_or_create_session()` which creates a Docker container with `detach=True, tty=True`. The container stays running forever -- the only way to stop it is an explicit `close_session()` call. This leaks containers. Even a single `ls` command leaves a container running indefinitely.

The workspace is a host directory mounted into the container. Files persist on the host regardless of container lifecycle. There is no reason to keep the container alive between commands.

`sandbox_close_session` was added as an agent tool to work around this, but an agent should never manage its own container lifecycle.

Two additional problems exist in the current code:

1. Ephemeral cleanup is not guaranteed. A bare `try/finally` in `execute_command()` is fragile -- it mixes session creation, command execution, and cleanup in a single method. A context manager on the session itself makes the lifecycle explicit and impossible to skip.

2. The async tool wrappers (`tools/sandbox.py`, `mcp/sandbox/tools.py`) are declared `async def` but call `manager.execute_command()` synchronously. The Docker SDK uses `requests` internally -- every Docker call (`containers.run`, `exec_run`, `container.stop`, `container.remove`) is blocking I/O. A long-running sandbox command blocks the entire event loop, freezing all other users. The codebase already solves this in `core/repl/cell.py` (`await asyncio.to_thread(self._execute_sync, ...)`) and `core/workspace.py` (`await asyncio.to_thread(read_from_workspace, ...)`). The sandbox tools must follow the same pattern.

## Current State

### `SandboxManager` (core/sandbox/manager.py)

- `get_or_create_session()` -- creates container if not cached in `_sessions` dict, reuses if cached
- `execute_command()` -- calls `get_or_create_session()`, runs `container.exec_run()`
- `close_session()` -- stops and removes container, deletes from `_sessions`
- `_ensure_network_mode()` -- on every `get_or_create_session()`, checks if private data changed and recreates container if needed
- No `__del__`, no context manager, no automatic cleanup

### Consumers

1. `agentic_patterns/tools/sandbox.py` -- PydanticAI tool wrapper. Exposes `sandbox_execute` + `sandbox_close_session`. Creates `SandboxManager()` inside `get_all_tools()`.
2. `agentic_patterns/mcp/sandbox/tools.py` -- MCP wrapper. Exposes `execute` + `close_session`. Module-level `_manager = SandboxManager()`.
3. `agentic_patterns/core/skills/tools.py` -- `create_skill_sandbox_manager()` creates a SandboxManager with read-only mounts. `run_skill_script()` calls `manager.execute_command()`.
4. `tests/integration/test_sandbox_network_isolation.py` -- creates SandboxManager in `setUp`, calls `close_session` in `tearDown`.
5. `tests/integration/test_sandbox_read_only_mounts.py` -- same pattern.

### Config (core/sandbox/config.py)

`SANDBOX_SESSION_TIMEOUT` exists (default 3600s) but is never used anywhere. It was clearly intended for session expiry but never implemented.

## Design

### New default: destroy container after each command

`execute_command()` gets a new parameter `persistent: bool = False`.

- `persistent=False` (default): create container, run command, destroy container. No session caching.
- `persistent=True`: current behavior -- cache session, reuse container across commands.

The private data network mode ratchet still works in both modes: `get_network_mode()` is called on every `execute_command()`.

### Context manager for ephemeral container lifecycle

`Session` gets an `ephemeral_session(manager)` context manager (on `SandboxManager`, returns `Session`). The context manager creates a container on enter and destroys it on exit, guaranteeing cleanup regardless of exceptions. Ephemeral sessions use a uuid suffix in the container name to avoid collisions with persistent sessions.

```python
@contextmanager
def ephemeral_session(self, user_id: str, session_id: str) -> Iterator[Session]:
    session = self._new_session(user_id, session_id, ephemeral=True)
    try:
        yield session
    finally:
        self._remove_container(session.container_id)
```

`execute_command()` uses this context manager when `persistent=False`:

```python
def execute_command(self, user_id, session_id, command, timeout=None, persistent=False):
    if persistent:
        session = self.get_or_create_session(user_id, session_id)
        return self._run_command(session, command, timeout)

    with self.ephemeral_session(user_id, session_id) as session:
        return self._run_command(session, command, timeout)
```

The actual exec_run logic moves to `_run_command(session, command, timeout)` so both paths share the same execution code.

### Async wrapping: do not block the event loop

The async tool wrappers must not call blocking Docker SDK methods on the event loop. The fix: wrap the synchronous `manager.execute_command()` call with `asyncio.to_thread()` in both `tools/sandbox.py` and `mcp/sandbox/tools.py`.

This follows the existing codebase pattern:
- `core/repl/cell.py:68` -- `await asyncio.to_thread(self._execute_sync, ...)`
- `core/workspace.py` -- `await asyncio.to_thread(read_from_workspace, ...)`

The `SandboxManager` itself stays synchronous. Only the async wrappers change.

### Rename `Session` to `SandboxSession`

The class `Session` in `core/sandbox/session.py` is ambiguous -- the codebase also has HTTP sessions, login sessions, and conversation sessions (`session_id` from `set_user_session()`). This class specifically tracks the lifecycle of a Docker container backing a conversation session. Rename it to `SandboxSession` to make that clear. Update all imports and type annotations in `manager.py` and `__init__.py`.

### Remove `sandbox_close_session` from agent tools

The agent never needs this. Container cleanup is infrastructure, not agent behavior.

- `tools/sandbox.py`: `get_all_tools()` returns only `[sandbox_execute]`
- `mcp/sandbox/tools.py`: `register_tools()` registers only `execute`

### Keep `close_session()` on the manager

Tests and infrastructure code still need it for persistent sessions. The method stays, but no agent-facing wrapper exposes it.

## Files to Modify

### 1. `agentic_patterns/core/sandbox/manager.py`

Add `ephemeral_session()` context manager, `_run_command()` helper, `persistent` param on `execute_command()`, and `ephemeral` flag on `_new_session()`:

```python
from contextlib import contextmanager
from collections.abc import Iterator
import uuid

class SandboxManager:

    @contextmanager
    def ephemeral_session(self, user_id: str, session_id: str) -> Iterator[Session]:
        """Create a container, yield the session, destroy the container on exit."""
        session = self._new_session(user_id, session_id, ephemeral=True)
        try:
            yield session
        finally:
            self._remove_container(session.container_id)

    def execute_command(self, user_id, session_id, command, timeout=None, persistent=False):
        if persistent:
            session = self.get_or_create_session(user_id, session_id)
            return self._run_command(session, command, timeout)
        with self.ephemeral_session(user_id, session_id) as session:
            return self._run_command(session, command, timeout)

    def _new_session(self, user_id, session_id, ephemeral=False):
        # ephemeral=True adds uuid suffix to container name to avoid collisions
        suffix = f"-{uuid.uuid4().hex[:8]}" if ephemeral else ""
        container_name = f"{SANDBOX_CONTAINER_PREFIX}-{user_id}-{session_id}{suffix}"
        # ... rest unchanged ...

    def _run_command(self, session, command, timeout=None):
        """Execute a command in the session's container. Returns (exit_code, output)."""
        session.touch()
        timeout = timeout or SANDBOX_COMMAND_TIMEOUT
        container = self.client.containers.get(session.container_id)
        result = container.exec_run(
            cmd=["bash", "-c", command], workdir=session.config.working_dir, demux=True
        )
        stdout = result.output[0].decode("utf-8", errors="replace") if result.output[0] else ""
        stderr = result.output[1].decode("utf-8", errors="replace") if result.output[1] else ""
        return result.exit_code, stdout + stderr
```

### 2. `agentic_patterns/tools/sandbox.py`

Remove `sandbox_close_session`. Wrap `manager.execute_command()` with `asyncio.to_thread()`:

```python
import asyncio

async def sandbox_execute(command: str, timeout: int = SANDBOX_COMMAND_TIMEOUT) -> str:
    exit_code, output = await asyncio.to_thread(
        manager.execute_command, get_user_id(), get_session_id(), command, timeout
    )
    header = f"Exit code: {exit_code}\n"
    return header + output

return [sandbox_execute]
```

### 3. `agentic_patterns/mcp/sandbox/tools.py`

Remove `close_session` tool. Wrap `_manager.execute_command()` with `asyncio.to_thread()`:

```python
import asyncio

async def execute(command: str, timeout: int = SANDBOX_COMMAND_TIMEOUT, ctx: Context = None) -> str:
    try:
        exit_code, output = await asyncio.to_thread(
            _manager.execute_command, get_user_id(), get_session_id(), command, timeout
        )
    except NotFound as e:
        raise ToolFatalError(str(e)) from e
    except DockerException as e:
        raise ToolFatalError(str(e)) from e
    await ctx.info(f"execute: exit_code={exit_code}")
    header = f"Exit code: {exit_code}\n"
    return header + output
```

### 4. `agentic_patterns/core/sandbox/session.py`

Rename `Session` to `SandboxSession`. Update `__str__`.

### 5. `agentic_patterns/core/sandbox/__init__.py`

Update import and `__all__` to use `SandboxSession`.

### 6. `agentic_patterns/core/sandbox/manager.py` (additional)

Update import and all type annotations from `Session` to `SandboxSession`.

### 7. Tests

`test_sandbox_network_isolation.py` and `test_sandbox_read_only_mounts.py` use persistent sessions (they run multiple commands in the same container and test container recreation). Update them to pass `persistent=True` where needed, or keep using `get_or_create_session()` + `close_session()` directly since they test infrastructure, not agent behavior.

Specifically in `test_sandbox_network_isolation.py`: `test_workspace_survives_container_recreation` mixes `execute_command()` with `get_or_create_session()` to test the ratchet. Both `execute_command()` calls need `persistent=True` so they share the cached session.

## Verification

1. `scripts/lint.sh`
2. `scripts/test.sh` -- both sandbox integration tests must pass
3. Manual: run `sandbox_execute("echo hello")` -- verify no container is left running after the call
