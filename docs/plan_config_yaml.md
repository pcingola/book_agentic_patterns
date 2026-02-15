# Plan: Sync config.yaml / .env and move env vars to config.yaml

## Context

Configuration was migrated from `.env` to `config.yaml`, but the files are out of sync: `.env` still has entries that belong in `config.yaml`, and `config_example.yaml` is missing sections that `config.yaml` has. Goal: config.yaml is the single source of truth; `.env` only keeps what frameworks force us to (CHAINLIT_AUTH_SECRET).

## Changes

### 1. Add `auth` and `docker_host` to config.yaml

Add to `config.yaml` (between `sandbox` and `openapi` sections):

```yaml
auth:
  jwt_secret: poc-shared-secret-change-in-production
  jwt_algorithm: HS256
```

Add `docker_host` at the `sandbox` level (sibling to `default`/`repl`):

```yaml
sandbox:
  docker_host: "unix:///Users/kqrw311/.rd/docker.sock"
  default:
    ...
```

### 2. Sync config_example.yaml with config.yaml

Add missing sections with placeholder values:
- `sandbox` section (with `docker_host` commented out, `default` and `repl` profiles)
- `auth` section (with placeholder jwt_secret)
- `openapi` MCP server entry in `mcp_servers`
- `openapi` A2A client in `a2a.clients`
- `openapi` sub_agent in `coordinator`, `full_agent`, and `infrastructure_agent` agents

### 3. Clean .env and .env_example

**.env**: Remove `JWT_SECRET` and `DOCKER_HOST`. Keep only `CHAINLIT_AUTH_SECRET`.

**.env_example**: Remove `JWT_SECRET`, `DOCKER_HOST`, and commented-out directory vars. Keep only `CHAINLIT_AUTH_SECRET`.

### 4. Update config.py to read auth from config.yaml

File: `agentic_patterns/core/config/config.py`

Replace the `get_variable_env("JWT_SECRET")` calls with config.yaml loading. Load the `auth` section from config.yaml, falling back to current defaults.

### 5. Add docker_host to SandboxConfig and its loader

File: `agentic_patterns/core/sandbox/config.py`

- Add `docker_host: str | None = None` field to `SandboxConfig`
- In `load_sandbox_config()`, extract `docker_host` from raw yaml before processing profiles
- Export a module-level `DOCKER_HOST` constant like the other sandbox constants

### 6. Use docker_host from config in Docker client creation

File: `agentic_patterns/core/sandbox/manager.py`
- Import `DOCKER_HOST` from sandbox config
- In the `client` property, use `docker.DockerClient(base_url=DOCKER_HOST)` when set, otherwise `docker.from_env()`

File: `agentic_patterns/core/repl/cli.py`
- Same pattern: use configured docker_host if available

## Files to modify

1. `config.yaml` - add auth section, add docker_host to sandbox
2. `config_example.yaml` - sync all missing sections
3. `.env` - remove JWT_SECRET, DOCKER_HOST
4. `.env_example` - remove JWT_SECRET, DOCKER_HOST, directory comments
5. `agentic_patterns/core/config/config.py` - read JWT from config.yaml
6. `agentic_patterns/core/sandbox/config.py` - add docker_host support
7. `agentic_patterns/core/sandbox/manager.py` - use docker_host from config
8. `agentic_patterns/core/repl/cli.py` - use docker_host from config

## Verification

- Run `scripts/test.sh` to ensure nothing breaks
- Check that `build-repl-image` still works (reads docker_host from config.yaml)
- Verify config.yaml and config_example.yaml have the same structure
