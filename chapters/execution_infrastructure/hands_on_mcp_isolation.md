## Hands-On: MCP Server Isolation

This hands-on walks through `example_mcp_isolation.ipynb`, where an agent connects to a template MCP server through the `MCPServerPrivateData` client. The notebook demonstrates the dual-instance isolation pattern: before private data enters the session, tool calls route to the normal server instance; after a tool flags the session as containing sensitive data, all subsequent calls switch to the isolated instance. The switch is a one-way ratchet that never reverts within the session.

The notebook also exercises several production MCP server requirements in a single flow: workspace path translation, `@context_result()` for large results, `@tool_permission` decorators, error classification with `ToolRetryError`, and server-to-client log forwarding via `ctx.info()`.

## Starting the Servers

The template server lives in `agentic_patterns/mcp/template/`. Before running the notebook, start two instances of the same server on different ports:

```bash
fastmcp run agentic_patterns/mcp/template/server.py:mcp --transport http --port 8000
fastmcp run agentic_patterns/mcp/template/server.py:mcp --transport http --port 8001
```

In production, these would be two Docker containers from the same image -- one on the bridge network, one with `network_mode: "none"`. For the notebook, two local processes on different ports simulate the same topology without Docker.

## The Template Server

The server itself is minimal. `server.py` calls `create_mcp_server()` from the core library, which returns a `FastMCP` instance with `AuthSessionMiddleware` pre-wired for JWT-based identity propagation. Tools are registered from a separate `tools.py` module:

```python
mcp = create_mcp_server("template", instructions="Template MCP server with workspace, permissions, and compliance.")
register_tools(mcp)
```

The four tools in `tools.py` each demonstrate a different requirement. `read_file` combines `@tool_permission(READ)`, `@context_result()`, and `read_from_workspace()` in a single tool. `write_file` shows workspace writes. `search_records` raises `ToolRetryError` when given an empty query, giving the LLM a chance to correct its arguments. `load_sensitive_dataset` flags the session as containing private data via `PrivateData.add_private_dataset()`, which triggers the client-side isolation switch.

## Connecting via get_mcp_client

The notebook creates the MCP client with a single call:

```python
server = get_mcp_client("template")
```

This reads the `config.yaml` entry for the `template` server. Because that entry has both `url` and `url_isolated` configured, the factory returns an `MCPServerPrivateData` instance instead of a plain `MCPServerStrict`:

```yaml
mcp_servers:
  template:
    type: client
    url: http://localhost:8000/mcp
    url_isolated: http://localhost:8001/mcp
    read_timeout: 60
```

The caller does not need to know which variant it got. `MCPServerPrivateData` is a drop-in replacement for `MCPServerStrict` -- it implements the same interface and can be passed directly as a toolset to `get_agent()`.

## Normal Tool Call

The first agent interaction writes a file to the workspace and reads it back. At this point, `session_has_private_data()` returns `False`, so `MCPServerPrivateData._target()` routes the tool call to the normal instance on port 8000.

```python
print(f"Private data: {session_has_private_data()}")
async with agent:
    result, _ = await run_agent(agent, "Write 'hello world' to /workspace/hello.txt, then read it back.")
```

The `async with agent` context manager opens both MCP connections (normal and isolated) simultaneously. Both are kept alive for the entire session so that switching between them does not require a reconnection.

The log output shows `ctx.info("Reading file: ...")` messages from the server, delivered through the MCP protocol's `notifications/message` mechanism and forwarded to Python logging by the client's `log_handler`.

## Retryable Error

The second interaction deliberately triggers a `ToolRetryError`. The agent is asked to call `search_records` with an empty string:

```python
async with agent:
    result, _ = await run_agent(
        agent,
        "Call the search_records tool with an empty string '' as the query argument.",
        verbose=True,
    )
```

The `search_records` tool checks for empty queries and raises `ToolRetryError("Query cannot be empty -- provide a search term")`. FastMCP converts this to a `ToolError`, which PydanticAI surfaces as a `ModelRetry`. The LLM receives the error message and gets another chance to provide valid arguments. With `verbose=True`, the step-by-step log shows the retry followed by a second tool call with a non-empty query.

This is the distinction between `ToolRetryError` and `ToolFatalError`. A retryable error means the tool's logic is fine but the arguments were wrong -- the LLM should try again. A fatal error means something is broken at the infrastructure level and the agent run should abort immediately. `MCPServerStrict` intercepts fatal errors (identified by the `[FATAL]` prefix) and raises `RuntimeError` instead of `ModelRetry`.

## Private Data and Isolation Switch

The third interaction loads a sensitive dataset:

```python
print(f"Private data   : {session_has_private_data()}")
print(f"Isolated before: {getattr(server, 'is_isolated', 'N/A')}")

async with agent:
    result, _ = await run_agent(agent, "Load the 'patient_records' sensitive dataset")
```

Inside `load_sensitive_dataset`, the tool calls `PrivateData().add_private_dataset("patient_records", DataSensitivity.CONFIDENTIAL)`. This writes a `.private_data` JSON file outside the agent's workspace (so the agent cannot tamper with it) and sets the session's sensitivity level to CONFIDENTIAL.

After the agent run completes, inspecting the client state reveals the switch:

```python
print(f"Private data  : {session_has_private_data()}")   # True
print(f"Isolated after: {getattr(server, 'is_isolated', 'N/A')}")  # True
```

The `is_isolated` property flipped from `False` to `True`. From this point on, every `list_tools`, `call_tool`, and `direct_call_tool` invocation on the `MCPServerPrivateData` object routes to the isolated instance on port 8001 instead of the normal instance on port 8000.

## How the Switch Works Internally

`MCPServerPrivateData` holds two `MCPServerStrict` instances and delegates every call through `_target()`:

```python
def _target(self) -> MCPServerStrict:
    if not self._is_isolated:
        self._is_isolated = session_has_private_data()
    return self._isolated if self._is_isolated else self._normal
```

The check is cheap -- `session_has_private_data()` reads a contextvar and a file -- and it runs on every tool call. Once the flag flips, `_is_isolated` stays `True` forever; the conditional short-circuits and never checks the file again. This is the one-way ratchet: escalation from normal to isolated is automatic, but there is no path back within the session.

Both connections are opened at `__aenter__` and closed at `__aexit__`. There is no reconnection at the switch point. PydanticAI sees the same toolset object throughout the session; the routing change is entirely internal.

## Production Deployment

In production, the two server instances run as Docker containers from the same image with different network configurations:

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

Tools in the isolated container that attempt external connections (HTTP requests, database calls to remote hosts, webhook posts) fail with network errors. This is the intended behavior: the network block acts as a safety net independent of application-level permission checks. Even if `@tool_permission(CONNECT)` has a bug, or a tool reaches an external service through a code path that was not tagged with CONNECT, the container-level network isolation prevents data from leaving.

## Key Takeaways

`MCPServerPrivateData` provides transparent client-side switching between normal and isolated MCP server instances based on session sensitivity. The `get_mcp_client()` factory selects the right client variant based on whether `url_isolated` is configured, so callers do not need conditional logic. The switch is a one-way ratchet triggered by `PrivateData` tagging, matching the escalation semantics used across the compliance layer. In production, the two instances are Docker containers with different network policies, providing defense-in-depth that does not depend on the correctness of application-level permission checks.
