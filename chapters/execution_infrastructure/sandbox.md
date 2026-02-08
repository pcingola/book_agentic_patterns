## Code Sandbox

When agents use the CodeAct pattern -- generating and executing arbitrary code to accomplish tasks -- they need an execution environment that is isolated, recoverable, and auditable. A sandbox provides this environment. It sits between the agent and the host operating system, enforcing boundaries that the agent's code cannot circumvent.

This section describes the concepts and mechanisms behind sandboxed execution. The sandbox is a library-level abstraction: it provides the building blocks that higher-level systems (MCP servers, API services, CLI tools) compose into complete execution environments.

## Why Agents Need Sandboxes

Tool-based agents operate within a controlled vocabulary: each tool has defined inputs, outputs, and permissions (see the `@tool_permission` decorator in our tools module). But CodeAct agents write and run arbitrary code. A Python snippet can open files, make network requests, spawn processes, or modify the filesystem in ways that no tool permission system can anticipate.

The sandbox addresses this by enforcing isolation at the infrastructure level. Rather than trying to restrict what code can do through static analysis or allow-lists (which are brittle and bypassable), the sandbox constrains the environment in which the code runs.

## Process Isolation

The fundamental mechanism is process isolation: executing the agent's code in a separate process with restricted access to the host system.

### Lightweight Isolation: Bubblewrap

On Linux, [bubblewrap](https://github.com/containers/bubblewrap) (`bwrap`) provides user-namespace-based isolation without requiring root privileges or a container runtime. It creates a minimal filesystem view by selectively bind-mounting only the paths the child process needs:

```python
class SandboxBubblewrap(Sandbox):
    def _build_command(self, command, bind_mounts, isolate_network, isolate_pid, cwd):
        cmd = [
            "bwrap",
            "--ro-bind", "/usr", "/usr",
            "--ro-bind", "/lib", "/lib",
            "--ro-bind", "/lib64", "/lib64",
            "--ro-bind", "/bin", "/bin",
            "--ro-bind", "/sbin", "/sbin",
            "--ro-bind", "/etc/resolv.conf", "/etc/resolv.conf",
            "--proc", "/proc",
            "--dev", "/dev",
            "--tmpfs", "/tmp",
        ]
        # User-specified mounts
        for mount in bind_mounts:
            flag = "--ro-bind" if mount.readonly else "--bind"
            cmd.extend([flag, str(mount.source), mount.target])
        # Optional namespace isolation
        if isolate_pid:
            cmd.append("--unshare-pid")
        if isolate_network:
            cmd.append("--unshare-net")
        ...
```

The child process sees a read-only root filesystem, a private `/tmp`, and only the bind mounts explicitly granted. PID and network namespaces can be unshared independently. This is lightweight (no daemon, no images, no layers) and fast to start.

### Fallback: Plain Subprocess

On platforms without bwrap (macOS, Windows), a subprocess fallback runs the command directly. No isolation is provided -- this is a development convenience, not a security boundary. The factory function selects the appropriate implementation:

```python
def get_sandbox() -> Sandbox:
    if shutil.which("bwrap"):
        return SandboxBubblewrap()
    return SandboxSubprocess()
```

### Heavyweight Isolation: Containers

For production multi-tenant deployments, container runtimes (Docker, Podman) provide stronger isolation: separate filesystem layers, cgroup resource limits, full network namespace control, and seccomp profiles. Container-based sandboxes are heavier to start and manage, but offer guarantees that bwrap alone does not (CPU/memory limits, storage quotas, image-based reproducibility).

The sandbox abstraction accommodates both: the `Sandbox` ABC defines a uniform `run()` interface, and implementations range from "no isolation" through "user namespaces" to "full containers". The choice depends on the deployment context.

## Filesystem Isolation

The agent's code needs to read and write files, but it should only access its own workspace -- not the host filesystem, not other users' data.

### Bind Mounts

The sandbox exposes specific host directories to the child process through bind mounts. A `BindMount(source, target, readonly)` maps a host path to a path visible inside the sandbox:

```python
bind_mounts = [
    BindMount(workspace_path, "/workspace"),           # read-write
    BindMount(temp_dir, str(temp_dir)),                # IPC channel
]
```

Inside the sandbox, the code sees `/workspace` as its working directory. It has no way to access paths outside the mounted directories.

### Multi-Tenant Directory Layout

When multiple users and sessions share a host, each session gets its own workspace directory:

```
{data_dir}/
  {user_id}/
    {session_id}/
      [session files]
```

The sandbox mounts only the current session's directory. Physical separation at the filesystem level prevents cross-session access without relying on application-level checks.

### Path Translation

A translation layer converts between the agent-visible path (`/workspace/report.csv`) and the host path (`/data/users/alice/session-42/report.csv`). This happens at the boundary between the application and the sandbox -- the agent's code never sees host paths, and the host system never trusts agent-provided paths without translation and traversal checks.

## Network Isolation

Network access is the primary exfiltration vector for code running inside a sandbox. An agent that has loaded sensitive data into its workspace could POST it to an external server. Tool permissions cannot prevent this because the code runs outside the tool framework.

### Binary Network Control

The simplest and most auditable approach is a binary choice: the sandbox either has full network access or none at all. On bwrap, `--unshare-net` removes all network interfaces except loopback. On Docker, `network_mode="none"` does the same.

There is no allow-list, no proxy, no partial access. This eliminates configuration errors and makes the security property trivial to verify.

### Integration with Data Sensitivity

The network isolation decision can be driven by data classification. When a session processes sensitive data (flagged by connectors via a compliance layer like `PrivateData`), the sandbox automatically disables network access:

```python
isolate_network = session_has_private_data(user_id, session_id)
```

This is a one-way ratchet: once sensitive data enters a session, the network stays off for the session's lifetime. Sensitivity escalates but never degrades.

### Workspace Survival Across Recreation

If a running sandbox must be recreated to change its network mode (for example, when private data arrives mid-session), the workspace survives because it lives on the host filesystem. The old sandbox is destroyed, a new one is created with network disabled, and the same workspace directory is mounted again. From the agent's perspective, all files are still present -- only the network has changed.

## Timeout Enforcement

Agent-generated code can loop forever, deadlock, or simply take longer than acceptable. Reliable timeout enforcement requires process-level control -- you cannot reliably interrupt a thread executing arbitrary code.

The sandbox starts the child process, then uses `asyncio.wait_for` with a timeout. If the timeout expires, the process is killed:

```python
try:
    stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
    return SandboxResult(exit_code=process.returncode, stdout=stdout, stderr=stderr)
except asyncio.TimeoutError:
    process.kill()
    await process.wait()
    return SandboxResult(exit_code=-1, timed_out=True)
```

The calling code receives a `SandboxResult` with `timed_out=True` and can report the timeout to the agent without crashing the host process.

## Inter-Process Communication

The sandbox runs code in a separate process. The calling code needs to send input (source code, namespace state) and receive output (results, stdout, stderr, figures). Two common patterns:

### Pickle IPC

The REPL module uses pickle-based IPC through the filesystem. The caller writes a pickle file to a temp directory, the sandbox mounts that directory, the executor reads input and writes output as pickle files:

```python
# Caller side
(temp_dir / "input.pkl").write_bytes(pickle.dumps(input_data))
result = await sandbox.run(command, bind_mounts=[BindMount(temp_dir, str(temp_dir))], ...)
output = pickle.loads((temp_dir / "output.pkl").read_bytes())
```

This works because the temp directory is bind-mounted into the sandbox, giving both sides access. The approach is simple and supports arbitrary Python objects (dataframes, figures, custom classes).

### Stdout/Stderr Capture

For simpler cases, the sandbox captures the child process's stdout and stderr as byte strings in `SandboxResult`. This suffices for commands that produce text output and where the only structured result is the exit code.

## Resource Limits

Beyond filesystem and network isolation, production sandboxes need resource limits to prevent a single session from exhausting host resources.

**CPU and memory**: Container runtimes enforce these through cgroups. Bwrap does not manage cgroups, so resource limits require either a container runtime or external cgroup management.

**Execution time**: Handled by the timeout mechanism described above.

**Storage**: Workspace directories can be placed on quota-managed filesystems or volume-limited container mounts.

**Process count**: PID namespace isolation (`--unshare-pid` in bwrap, default in containers) prevents fork bombs from affecting the host.

## Session Lifecycle

In a multi-tenant system, sandboxes are tied to user sessions. The lifecycle follows a predictable pattern:

**Lazy creation**: The sandbox is not created when the user connects. It is created on first code execution, avoiding resource allocation for sessions that never run code.

**Activity tracking**: Each code execution updates a timestamp. Sessions that remain idle beyond a configurable timeout are eligible for cleanup.

**Failure recovery**: If a sandbox process crashes or is killed externally, the next execution attempt detects the failure and creates a new sandbox. The workspace persists through failures because it lives on the host filesystem, making the sandbox a disposable execution environment.

**Cleanup**: Background processes periodically remove expired sessions and their sandbox resources. Cleanup operations are defensive -- errors in cleaning one session do not prevent cleanup of others.

## Security Layers

The sandbox is one layer in a defense-in-depth approach to agent security:

1. **Tool permissions** (`@tool_permission` with READ/WRITE/CONNECT) constrain what the agent can do through its normal tool-calling interface.
2. **Sandbox isolation** constrains what the agent's generated code can do at the infrastructure level -- filesystem, network, process, and resource boundaries.
3. **Data compliance** drives sandbox configuration automatically, tightening isolation when sensitive data enters a session.

These layers are independent. Tool permissions cannot prevent code from making network requests inside a sandbox. Sandbox network isolation cannot prevent a tool from calling an external API. Together, they cover both vectors without relying on the agent's cooperation.

## Design Trade-offs

**One sandbox per session** simplifies lifecycle management (no shared state, no cross-session interference) but costs more resources than pooling. For strong isolation, this trade-off is worthwhile.

**Binary network control** (full access or none) is less flexible than allow-lists or proxies, but eliminates configuration errors and is easy to audit.

**Pickle IPC** supports rich Python objects but introduces deserialization risks. The temp directory is short-lived and mounted read-write only for the duration of execution, limiting the attack surface.

**Subprocess fallback** provides no isolation on non-Linux platforms. This is acceptable for development but must not be used in production with untrusted code.
