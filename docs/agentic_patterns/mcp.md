# MCP (Model Context Protocol)

MCP standardizes how agents connect to external tools, data, and prompts. The library provides infrastructure on top of PydanticAI and FastMCP for building production MCP servers and clients: YAML-based configuration, error classification (retryable vs fatal), authentication middleware, network isolation for private data, and factory functions that wire everything together.

All MCP infrastructure lives in `agentic_patterns.core.mcp`. Thin MCP server wrappers live in `agentic_patterns.mcp.*`.


## Connecting Agents to MCP Servers

Agents connect to MCP servers by passing them as `toolsets` to `get_agent()`. PydanticAI handles protocol mechanics (initialization, tool discovery, invocation) transparently.

### STDIO transport (local development)

The server runs as a subprocess. No separate process is needed.

```python
from pydantic_ai.mcp import MCPServerStdio
from agentic_patterns.core.agents import get_agent, run_agent

server = MCPServerStdio(command="fastmcp", args=["run", "-t", "stdio", "server.py"])
agent = get_agent(toolsets=[server])

async with agent:
    result, nodes = await run_agent(agent, "What is 40 + 2?", verbose=True)
```

### HTTP transport (remote/persistent servers)

The server must be started separately (e.g., `fastmcp run server.py`).

```python
from pydantic_ai.mcp import MCPServerStreamableHTTP
from agentic_patterns.core.agents import get_agent, run_agent

server = MCPServerStreamableHTTP(url="http://127.0.0.1:8000/mcp/")
agent = get_agent(toolsets=[server])

async with agent:
    result, nodes = await run_agent(agent, "What is 40 + 2?", verbose=True)
```

The `async with agent:` context manager is required when using MCP toolsets. It manages the connection lifecycle.


## Building MCP Servers

### Server creation

`create_mcp_server()` wraps FastMCP with `AuthSessionMiddleware` pre-wired for JWT-based user session handling.

```python
from agentic_patterns.core.mcp import create_mcp_server

mcp = create_mcp_server("my-server", instructions="A server for data operations.")
```

Register tools on the server using FastMCP's `@mcp.tool()` decorator.

### Error classification

MCP tools should use two error types to communicate failure semantics to the agent:

```python
from agentic_patterns.core.mcp import ToolRetryError, ToolFatalError

@mcp.tool()
def query_data(sql: str) -> str:
    """Execute a SQL query."""
    try:
        return execute(sql)
    except ValueError as e:
        # Agent should retry with different arguments
        raise ToolRetryError(str(e))
    except RuntimeError as e:
        # Agent should stop -- unrecoverable error
        raise ToolFatalError(str(e))
```

`ToolRetryError` extends FastMCP's `ToolError` and signals the LLM to try again with corrected arguments. `ToolFatalError` prefixes the message with `[FATAL]` and causes the agent run to abort immediately rather than retrying.

### The thin wrapper pattern

All MCP servers in `agentic_patterns/mcp/` follow the same structure: a `server.py` that creates the server and a `tools.py` that registers tools delegating to toolkits or connectors. Error conversion maps domain exceptions to `ToolRetryError` or `ToolFatalError`.

```
agentic_patterns/mcp/todo/
    server.py       # create_mcp_server("todo-server")
    tools.py        # @mcp.tool() wrappers delegating to toolkits/todo/operations
```


## Configuration

MCP client and server settings are defined in `config.yaml` and loaded via `load_mcp_settings()`.

```yaml
mcp_servers:
  sql:
    url: http://localhost:8101/mcp
    url_isolated: http://localhost:8102/mcp   # Optional: for private data sessions
    read_timeout: 60

  file_ops:
    url: http://localhost:8103/mcp
```

`url_isolated` is optional. When present, sessions containing private data are routed to the isolated endpoint (which may have network restrictions). See Network Isolation below.

### Client factories

```python
from agentic_patterns.core.mcp import get_mcp_client, get_mcp_clients

# Single client
sql_client = get_mcp_client("sql")

# Multiple clients
clients = get_mcp_clients(["sql", "file_ops"])

# With Bearer token for authenticated servers
sql_client = get_mcp_client("sql", bearer_token="eyJ...")
```

`get_mcp_client()` reads the config, creates the appropriate server wrapper, injects the Bearer token in request headers, and attaches a log handler that forwards MCP log messages to Python's logging.

When `url_isolated` is configured, `get_mcp_client()` returns an `MCPServerPrivateData` instance (see below). Otherwise, it returns an `MCPServerStrict` instance.


## Authentication Middleware

`AuthSessionMiddleware` extracts JWT claims from the access token and calls `set_user_session()` at the request boundary. It is pre-wired by `create_mcp_server()`.

```python
from agentic_patterns.core.mcp import AuthSessionMiddleware

# Typically you don't use this directly; create_mcp_server() adds it.
# But you can add it to a raw FastMCP server:
mcp = FastMCP("my-server", middleware=[AuthSessionMiddleware()])
```

The middleware reads `sub` (user ID) and `session_id` from JWT claims and sets the contextvars that downstream code (workspace paths, compliance checks, etc.) relies on.


## Network Isolation

`MCPServerPrivateData` provides a dual-instance wrapper for compliance-sensitive deployments. It holds two connections -- a normal one and an isolated one (with restricted network access) -- and routes calls based on whether the session contains private data.

```python
# Configured via url_isolated in config.yaml
# The client factory handles this automatically:
client = get_mcp_client("sql")  # Returns MCPServerPrivateData if url_isolated is set
```

The routing is a one-way ratchet: once private data is detected in a session, all subsequent calls go to the isolated endpoint. This prevents data leakage through external network access.

`MCPServerStrict` extends `MCPServerStreamableHTTP` and intercepts fatal errors. When a tool response contains the `[FATAL]` prefix, it raises `RuntimeError` to abort the agent run instead of allowing the model to retry.


## API Reference

### `agentic_patterns.core.mcp`

| Name | Kind | Description |
|---|---|---|
| `create_mcp_server(name, instructions)` | Function | Create a FastMCP server with auth middleware |
| `get_mcp_client(name, config_path, bearer_token)` | Function | Create an MCP client from config |
| `get_mcp_clients(names, config_path, bearer_token)` | Function | Create multiple MCP clients |
| `ToolRetryError` | Exception | Agent should retry with different arguments |
| `ToolFatalError` | Exception | Agent run should abort |
| `AuthSessionMiddleware` | Middleware | JWT claims to user session bridge |
| `MCPServerStrict` | Toolset | MCP client with fatal error interception |
| `MCPServerPrivateData` | Toolset | Dual-instance client with compliance routing |
| `MCPClientConfig` | Pydantic model | Client config (url, url_isolated, read_timeout) |
| `MCPServerConfig` | Pydantic model | Server config (name, instructions, port) |
| `load_mcp_settings(config_path)` | Function | Load MCP settings from YAML |


## Examples

See the notebooks in `agentic_patterns/examples/mcp/`:

- `example_mcp_stdio.ipynb` -- raw MCP protocol over STDIO transport
- `example_agent_mcp_client_stdio.ipynb` -- agent connected to MCP server via STDIO
- `example_agent_mcp_client_http.ipynb` -- agent connected to MCP server via HTTP
- `example_mcp_features.ipynb` -- tools, resources, and prompts via FastMCP client
