# MCP Template Design Document

This template provides a foundation for building FastMCP servers with secure data handling, workspace isolation, and enterprise authentication. The architecture prioritizes separation of concerns, proper error handling, and compliance with private data requirements.

## 2. Core Architecture

### 2.1 Component Layers

**Server Layer:**
- `server.py` - MCP server initialization with middleware stack
- Authentication, logging, error handling, timing, token limiting

**Entry Point Layer:**
- `main.py` - Imports server and registers tools via wildcard imports
- Tools only register when their modules are imported

**Tool Layer:**
- `tools/` - Modular tool implementations
- Each module contains related tool functions
- Tools use decorator pattern for registration

**Conceptual Structure:**
```
create_mcp_server(name, middleware) -> mcp
mcp.tool decorator -> register tool functions
main.py imports -> tool registration
```

### 2.2 Tool Registration Pattern

Tools register by importing after server creation:

```python
# server.py
mcp = create_mcp_server(name=__doc__)

# main.py
from server import mcp
from tools.tools_simple import *    # Tools register themselves
from tools.tools_context import *
```

If a tool module is not imported, its tools will not be available.

## 3. Data Isolation Architecture

### 3.1 Two-Path System

**Sandbox Paths (Agent View):**
- Virtual paths starting with `/workspace/`
- Example: `/workspace/results.csv`
- Agents NEVER see real filesystem paths

**Host Paths (Server Reality):**
- Real filesystem locations
- Example: `/data/workspaces/user123/session456/results.csv`
- Pattern: `$DATA_DIR/workspaces/$user_id/$session_id/`

**Path Conversion Pattern:**
```python
# Agent provides sandbox path
agent_path = "/workspace/result.csv"

# Convert to host path for file operations
host_path = container_to_host_path(PurePosixPath(agent_path), ctx)
# Returns: PosixPath('/data/workspaces/user123/session456/result.csv')

# Convert back for returning to agent
sandbox_path = host_to_container_path(host_path)
# Returns: '/workspace/result.csv'
```

### 3.2 Session Isolation

Each user/session has isolated workspace preventing cross-user data access:

```
/data/workspaces/
├── user_id_1/
│   ├── session_id_a/
│   └── session_id_b/
└── user_id_2/
    └── session_id_c/
```

**User/Session Retrieval:**
```python
user_id = get_user_id_from_request()
session_id = get_session_id_from_request()
```

Default values (`default_user`, `default_session`) for testing only, not production.

## 4. Tool Implementation Patterns

### 4.1 Simple Tools

Direct input/output for small results:

```python
@mcp.tool
async def add(a: int, b: int) -> int:
    """Adds two integers."""
    return a + b
```

**Characteristics:**
- Type hints on all parameters
- Clear docstrings
- Return values directly
- No context needed

### 4.2 Large Data Tools

Save results to files, return paths:

```python
@mcp.tool
async def query_database(sql: str, output_file: str, ctx: Context) -> str:
    """Execute query and save results."""
    # Generate large result
    df = execute_query(sql)

    # Convert sandbox path to host path
    host_path = container_to_host_path(PurePosixPath(output_file), ctx)

    # Save to file
    df.to_csv(host_path, index=False)

    # Return sandbox path + preview
    preview = df.head().to_csv(index=False)
    return f"Result in '{output_file}'\nPreview:\n{preview}"
```

**Key Requirements:**
- MUST save to file using `output_file` parameter
- MUST convert paths using `container_to_host_path()`
- MUST return sandbox path, NOT host path
- SHOULD include preview/summary

### 4.3 Context-Aware Tools

Use context for state, progress, messages:

```python
@mcp.tool
async def process_data(input: str, ctx: Context) -> str:
    """Process with state tracking."""
    # Get/set state
    data = ctx.get_state("my_data")
    ctx.set_state("my_data", updated_data)

    # Send messages
    await ctx.info("Starting process...")

    # Report progress
    for i in range(total):
        await ctx.report_progress(progress=i+1, total=total)

    return result
```

**Context parameter:**
- DO NOT document `ctx: Context` in docstring (framework injects it)
- Use for state: `get_state()`, `set_state()`
- Use for messages: `await info()`
- Use for progress: `await report_progress()`

### 4.4 Private Data Tools

Flag sensitive data for compliance:

```python
@mcp.tool
async def query_patient_data(sql: str, output_file: str, ctx: Context) -> str:
    """Query patient database."""
    # Query and save
    df = query_database(sql)
    host_path = container_to_host_path(PurePosixPath(output_file), ctx)
    df.to_csv(host_path, index=False)

    # Flag as private
    PrivateData(ctx).add_private_dataset(output_file)

    return f"Result in '{output_file}'"
```

**Requirements:**
- Follow all large data guidelines
- MUST flag with `PrivateData(ctx).add_private_dataset()`
- Workspace isolation provides data protection

### 4.5 Sandboxed Tools

Execute untrusted code with bubblewrap isolation:

```python
def execute_sandboxed(workspace_path: str, command: str) -> dict:
    """Execute command in sandbox."""
    bwrap_cmd = [
        "bwrap",
        "--unshare-all",              # Isolate all namespaces
        "--cap-drop", "ALL",           # Drop capabilities
        "--uid", "1000",               # Non-root
        "--gid", "1000",
        "--tmpfs", "/",                # Fake root (discarded)
        "--ro-bind", "/bin", "/bin",   # Read-only system
        "--ro-bind", "/lib", "/lib",
        "--ro-bind", "/usr", "/usr",
        "--bind", workspace_path, "/data",  # Read-write workspace
        "--chdir", "/data",
        "/bin/sh", "-c", command
    ]

    result = subprocess.run(bwrap_cmd, capture_output=True, timeout=30)
    return {"stdout": result.stdout, "exit_code": result.returncode}
```

**Requirements:**
- Docker compose needs security options:
```yaml
security_opt:
  - seccomp:unconfined
  - apparmor:unconfined
```

## 5. Error Handling Strategy

### 5.1 Two-Tier Exception Model

**Retryable Errors (AixToolError):**
- Input validation failures
- User-correctable errors
- LLM can fix and retry

**Code Errors (Standard Exceptions):**
- Bugs requiring developer attention
- Should propagate naturally
- Never caught and converted

### 5.2 Error Pattern

```python
@mcp.tool
async def process(name: str) -> str:
    """Process with validation."""
    # Retryable - LLM can fix
    if not name:
        raise AixToolError("Name cannot be empty")

    # Code errors - let propagate
    df = pd.read_csv(file_path)      # FileNotFoundError
    result = data['key']              # KeyError

    return result
```

### 5.3 Logging Behavior

**Middleware automatically logs:**
- `AixToolError` - WARNING level, short message
- Other exceptions - ERROR level, full stack trace
- Each line prefixed with `session_id`

### 5.4 Anti-Pattern

NEVER wrap entire tool in try/except:

```python
# WRONG - hides bugs
try:
    # entire tool code
except Exception as e:
    raise AixToolError(str(e))
```

## 6. Middleware Stack

### 6.1 Default Middleware

Automatically applied via `create_mcp_server()`:

1. **Authentication** - OAuth2 JWT validation
2. **Error Handling** - Two-tier exception logging
3. **Timing** - Request duration tracking
4. **Token Limiting** - Response truncation

### 6.2 Token Limit Middleware

**Automatic truncation:**
- Triggers when response exceeds 10,000 tokens
- Saves full response to `/workspace/full_tool_responses/`
- Returns truncated preview (first 2000 + last 2000 chars)
- Async writes avoid blocking

**Opt-out pattern:**
```python
from aixtools.mcp import TokenLimitMiddleware, get_default_middleware

mcp = create_mcp_server(
    name="My Server",
    middleware=[m for m in get_default_middleware()
                if not isinstance(m, TokenLimitMiddleware)]
)
```

**When to opt-out:**
- File read/edit tools needing complete contents
- Structured data requiring full parsing
- Code generation needing completeness

## 7. Authentication and Authorization

### 7.1 OAuth2 JWT Flow

**Azure EntraID integration:**
```
Client -> JWT token in Authorization header
   |
   v
Middleware validates token against EntraID
   |
   v
Check tenant ID, audience, scope, group membership
   |
   v
Extract user_id and session_id
```

**Environment Configuration:**
- `APP_TENANT_ID` - Azure AD tenant
- `APP_API_ID` - Application ID URI
- `APP_DEFAULT_SCOPE` - JWT scope
- `APP_AUTHORIZED_GROUPS` - Allowed group GUIDs

**Development bypass:**
```bash
SKIP_MCP_AUTHORIZATION=true
```

Never use in production.

## 8. Docker Architecture

### 8.1 Service Hierarchy

```
mcp-base-data          # Defines /data volume
    |
    v
mcp-base               # Standard service with auth
    |
    +-> mcp-base-aws       # Adds AWS credentials
    |       |
    |       v
    |   mcp-base-vault     # Adds Vault integration
```

### 8.2 Base Service Configuration

```yaml
mcp-base:
  extends: mcp-base-data
  environment:
    - APP_TENANT_ID
    - APP_AUTHORIZED_GROUPS
    - SKIP_MCP_AUTHORIZATION
  labels:
    # Path routing
    - traefik.http.routers.service.rule=PathPrefix(/service/)
    - traefik.http.middlewares.service-strip.stripprefix.prefixes=/service
    # OAuth well-known routing
    - traefik.http.routers.service-opr.rule=PathPrefix(/.well-known/oauth-protected-resource/service/)
```

### 8.3 Development Mode

**File watching:**
```yaml
develop:
  watch:
    - action: sync+restart
      path: ./mcp_module/
      target: /app/mcp_module/
    - action: sync+restart
      path: ./.env
      target: /app/.env
```

**Usage:**
```bash
docker compose up --watch
```

Auto-syncs changes and restarts service.

### 8.4 Build Optimization

**Layer caching:**
```dockerfile
RUN --mount=type=cache,target=/home/mcp_user/.cache/uv \
    uv sync
```

**Strategy:**
- Install dependencies before copying code
- Leverage BuildKit cache mounts
- Use `UV_LINK_MODE=copy` for consistency

## 9. Docker Base Images

### 9.1 Image Hierarchy

**mcp-base:**
- Ubuntu with uv, git, curl
- Zscaler certificate configuration
- Non-root user setup (mcp_user)

**mcp-base-datascience:**
- Extends mcp-base
- pandas, numpy, matplotlib, scikit-learn
- lightgbm, xgboost, shap

### 9.2 Certificate Handling

Custom certificates (Zscaler):
```bash
cat certs/custom_cert.crt >> .venv/lib/python*/site-packages/certifi/cacert.pem
```

Enables corporate proxy communication.

## 10. Script Architecture

### 10.1 Configuration Pattern

**config.sh - Single source of truth:**
```bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PROJECT_DIR="$SCRIPT_DIR/.."
export DATA_DIR="$PROJECT_DIR/data"
export SOURCE_DIR="$(cd $PROJECT_DIR/mcp_* ; pwd)"

# Activate venv
source "$PROJECT_DIR/.venv/bin/activate"

# Load and export .env
set -a
source "$PROJECT_DIR/.env"
set +a
```

**All scripts source config.sh:**
```bash
#!/bin/bash -eu
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/config.sh"

# Script logic here
```

### 10.2 Standard Scripts

**install.sh:**
- Create virtual environment with uv
- Install dependencies
- Install custom certificates
- Create .env from template
- Run db_download.sh and db_ingest.sh if present

**run.sh:**
- Default: Run FastMCP server
- `dev`: Run with MCP Inspector
- `watch`: Run with auto-reload

**test.sh:**
- Run all tests with coverage
- Support specific test files/functions
- Uses pytest

**lint.sh:**
- Check formatting and style
- `--fix`: Auto-fix issues
- Uses ruff

## 11. Tool Return Value Strategy

### 11.1 Two-Channel Output

**Prompt Values:**
- Small results (text, numbers, short JSON)
- Summaries and previews
- File paths (sandbox format)
- Auto-truncated if exceeds token limit

**Files:**
- Large datasets (CSV, JSON, Parquet)
- Images, plots, visualizations
- Full command outputs
- Path returned in prompt value

### 11.2 Large Data Pattern

```python
# Generate data
df = query_large_dataset(sql)

# Convert and save
result_file = container_to_host_path(PurePosixPath(output_file), ctx)
df.to_csv(result_file, index=False)

# Return path + preview
preview = df.head(10).to_string()
return f"Saved {len(df)} rows to '{output_file}'\n\nPreview:\n{preview}"
```

## 12. Database Guidelines

### 12.1 Local Database Pattern

For MCP servers with local databases (ClinicalTrials, OpenFDA):

**db_download.sh:**
- Downloads raw data from public sources
- Supports `--fast` flag for preprocessed data

**db_ingest.sh:**
- Ingests data into local database
- Supports `--fast` flag for quick setup

**install.sh integration:**
```bash
if [ -f "$SCRIPT_DIR/db_download.sh" ]; then
    bash "$SCRIPT_DIR/db_download.sh"
fi

if [ -f "$SCRIPT_DIR/db_ingest.sh" ]; then
    bash "$SCRIPT_DIR/db_ingest.sh"
fi
```

### 12.2 Fast Mode

Development mode for quick iteration:
```bash
./scripts/db_download.sh --fast
./scripts/db_ingest.sh --fast
```

Uses preprocessed data instead of full download/processing.

## 13. Testing and Debugging

### 13.1 In-Memory Client

For unit tests and notebooks:
```python
from fastmcp import Client
from mcp_template.server import mcp

# Create in-memory client
client = Client(mcp)

# Direct tool invocation
result = await client.call_tool("add", {"a": 5, "b": 3})
```

No server setup required.

### 13.2 Test Structure

```
tests/
├── __init__.py
├── test_simple_tools.py
├── test_large_data.py
└── data/
    └── test_data.csv
```

**Test execution:**
```bash
./scripts/test.sh                           # All tests
./scripts/test.sh tests/test_simple.py      # Specific file
./scripts/test.sh tests/test_simple.py::test_add  # Specific test
```

## 14. Naming Conventions

**Projects:**
- Use dashes: `mcp-sandbox`, `mcp-repl`, `mcp-playwright`

**Source directories:**
- Use underscores matching project: `mcp-sandbox/mcp_sandbox/`

**Pattern:**
```
mcp-my-service/
├── mcp_my_service/
│   ├── server.py
│   ├── main.py
│   └── tools/
├── scripts/
├── tests/
└── docker-compose.yml
```

## 15. Key Principles

### 15.1 Separation of Concerns

MCP servers should focus on single functionality:
- Database query tool - not mixed with file processing
- Sandbox execution - not mixed with API calls
- Follow Unix philosophy: do one thing well

### 15.2 Security First

- Workspace isolation prevents cross-user access
- OAuth2 JWT for authentication
- Bubblewrap sandboxing for untrusted code
- Private data flagging for compliance
- Never expose real filesystem paths to agents

### 15.3 Error Transparency

- Distinguish retryable vs code errors
- Detailed logging with session IDs
- Clear error messages for LLM recovery
- Full stack traces for developers

### 15.4 Agent Experience

- Agents work with simple `/workspace/` paths
- Large results automatically handled
- Progress reporting for long operations
- Token limiting prevents context overflow

## 16. Common Patterns Summary

### 16.1 Path Handling
```python
# Agent path -> Host path
host_path = container_to_host_path(PurePosixPath(agent_path), ctx)

# Host path -> Agent path
agent_path = host_to_container_path(host_path)
```

### 16.2 State Management
```python
data = ctx.get_state("key")
ctx.set_state("key", updated_data)
```

### 16.3 Progress Reporting
```python
await ctx.info("Starting task...")
await ctx.report_progress(progress=current, total=total)
```

### 16.4 Error Handling
```python
# Retryable
if invalid_input:
    raise AixToolError("Clear message for LLM")

# Code errors - let propagate
df = pd.read_csv(path)  # FileNotFoundError
```

### 16.5 Large Data
```python
host_path = container_to_host_path(PurePosixPath(output_file), ctx)
df.to_csv(host_path)
preview = df.head().to_string()
return f"Saved to '{output_file}'\n{preview}"
```

### 16.6 Private Data
```python
host_path = container_to_host_path(PurePosixPath(output_file), ctx)
df.to_csv(host_path)
PrivateData(ctx).add_private_dataset(output_file)
return f"Saved to '{output_file}'"
```

### 16.7 Middleware Customization
```python
mcp = create_mcp_server(
    name="My Server",
    middleware=[m for m in get_default_middleware()
                if not isinstance(m, TokenLimitMiddleware)]
)
```

This design document captures the essential patterns and architecture for building production-grade MCP servers with proper isolation, security, and error handling.
