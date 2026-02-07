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

The `SandboxManager` receives read-only mounts at construction time. A skill registry maps each skill name to a host directory containing a `scripts/` subdirectory. These are passed as read-only mounts so that every container in every session sees the same skill scripts at the same container paths.

The `run_skill_script` tool function bridges the two systems. It looks up the skill in the registry, resolves the script name to a container path under `/skills/{skill_name}/scripts/{script_name}`, and dispatches execution via `SandboxManager.execute_command`. Python scripts are invoked with `python`, shell scripts with `bash`. The tool returns the exit code and combined output.

```python
container_path = f"/skills/{skill.path.name}/scripts/{script_name}"
command = f"python {container_path} {args}" if script_name.endswith(".py") else f"bash {container_path} {args}"
return manager.execute_command(user_id, session_id, command)
```

Because `execute_command` calls `get_or_create_session` internally, skill execution benefits from the same lifecycle management, network isolation, and workspace persistence described in previous sections. If the session already has a container, the command runs there. If not, a new container is created with both the writable workspace and the read-only skill mounts. If PrivateData triggers a network ratchet mid-conversation, the recreated container preserves both mount types.

### Why Read-Only Matters

Without the read-only flag, a compromised or misbehaving agent could rewrite a skill script to inject malicious logic that executes on the next invocation -- either in the same session or, if mounts are shared, in other sessions. The `ro` flag is a filesystem-level guarantee enforced by Docker, not by application code. It does not depend on the agent cooperating or on any permission checks in the Python layer.

This creates a clean trust boundary: developers author skills, the platform mounts them immutably, and the agent can only invoke them as-is. The writable workspace remains available for the agent's own data and generated code, keeping the two trust levels physically separated inside the same container.
