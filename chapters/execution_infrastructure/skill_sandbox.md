## Sandboxing Skill Execution

The sandbox infrastructure described earlier runs agent-generated code in isolated containers. Skills introduce a different trust model: the code is authored by developers, not by the agent. The agent chooses which skill to invoke and with what arguments, but the implementation itself is fixed. This distinction calls for a read-only execution layer where the container can run skill scripts but cannot modify them.

### Read-Only Mounts

The `ContainerConfig` accepts a `read_only_mounts` dictionary that maps host paths to container paths. When the container is created, these are mounted alongside the writable `/workspace` volume, but with Docker's `ro` flag:

```python
volumes = {str(session.data_dir): {"bind": config.working_dir, "mode": "rw"}}
for host_path, container_path in config.read_only_mounts.items():
    volumes[host_path] = {"bind": container_path, "mode": "ro"}
```

The result is two distinct zones inside the container. `/workspace` is the agent's writable scratch space for data and generated code. `/skills` is an immutable library of developer-authored scripts. The agent can read and execute anything under `/skills`, but any attempt to write there fails at the filesystem level.

### Wiring Skills to the Sandbox

`SandboxManager` accepts an optional `read_only_mounts` dictionary at construction time. This dictionary is passed through to every `ContainerConfig` created by the manager, so every container -- across all sessions -- sees the same read-only mounts:

```python
class SandboxManager:
    def __init__(self, read_only_mounts: dict[str, str] | None = None) -> None:
        self._client: docker.DockerClient | None = None
        self._read_only_mounts: dict[str, str] = read_only_mounts or {}
        self._sessions: dict[tuple[str, str], SandboxSession] = {}
```

To wire skills into the sandbox, the caller iterates over the skill registry and builds the mount dictionary. Each skill's `scripts/` directory is mapped to a container path under `/skills/{skill_name}/scripts/`:

```python
read_only_mounts = {}
for meta in registry.list_all():
    scripts_dir = meta.path / "scripts"
    if scripts_dir.exists():
        read_only_mounts[str(scripts_dir)] = f"/skills/{meta.path.name}/scripts"
manager = SandboxManager(read_only_mounts=read_only_mounts)
```

Skill execution then dispatches through `SandboxManager.execute_command`, which handles session lifecycle internally -- creating or reusing containers as needed:

```python
container_path = f"/skills/{skill.path.name}/scripts/{script_name}"
command = f"python {container_path} {args}" if script_name.endswith(".py") else f"bash {container_path} {args}"
manager.execute_command(user_id, session_id, command)
```

Because `execute_command` manages the full container lifecycle, skill execution benefits from the same network isolation and workspace persistence described in previous sections. If the session already has a container, the command runs there. If not, a new container is created with both the writable workspace and the read-only skill mounts. If `PrivateData` triggers a network ratchet mid-conversation, the recreated container preserves both mount types.

### Why Read-Only Matters

Without the read-only flag, a compromised or misbehaving agent could rewrite a skill script to inject malicious logic that executes on the next invocation -- either in the same session or, if mounts are shared, in other sessions. The `ro` flag is a filesystem-level guarantee enforced by Docker, not by application code. It does not depend on the agent cooperating or on any permission checks in the Python layer.

This creates a clean trust boundary: developers author skills, the platform mounts them immutably, and the agent can only invoke them as-is. The writable workspace remains available for the agent's own data and generated code, keeping the two trust levels physically separated inside the same container.
