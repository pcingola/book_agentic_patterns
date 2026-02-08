## Hands-on: MCP server isolation

This section walks through a working template that demonstrates the production MCP requirements from the previous sections. The template consists of a server (`examples/mcp/template/server.py` and `tools.py`) and a client (`examples/mcp/template/client.py`). Together they exercise authentication, workspace isolation, context management, permissions, compliance flagging, and error classification.

### Server setup

The server is a single import plus one function call:

```python
from agentic_patterns.core.mcp import create_mcp_server
from agentic_patterns.examples.mcp.template.tools import register_tools

mcp = create_mcp_server("template", instructions="Template MCP server with workspace, permissions, and compliance.")
register_tools(mcp)
```

`create_mcp_server()` returns a `FastMCP` instance with `AuthSessionMiddleware` already attached. Every incoming request has its JWT decoded and the `user_id`/`session_id` claims pushed into contextvars before any tool runs. Tools never handle authentication themselves -- they call `get_user_id()` or `get_session_id()` when they need identity, and the middleware has already set those values.

### Tools

The `tools.py` module registers four tools on the server, each highlighting a different requirement.

**read_file** combines three patterns in a single tool. The `@tool_permission(ToolPermission.READ)` decorator declares that this tool only reads data. The `@context_result()` decorator intercepts the return value and, if it exceeds the configured threshold, saves the full content to a workspace file and returns a truncated preview. Inside the function, `read_from_workspace(path)` translates the agent-visible `/workspace/...` path to the host filesystem path with traversal protection.

```python
@mcp.tool()
@tool_permission(ToolPermission.READ)
@context_result()
def read_file(path: str) -> str:
    return read_from_workspace(path)
```

**write_file** is the write counterpart. `@tool_permission(ToolPermission.WRITE)` marks it as a write operation. The `write_to_workspace()` call handles the same path translation and traversal protection.

**search_records** demonstrates retryable errors. When the agent sends an empty query, the tool raises `ToolRetryError`. This becomes `isError: true` on the MCP wire, PydanticAI converts it to `ModelRetry`, and the LLM gets another chance to provide a valid query. The error message tells the model what went wrong:

```python
if not query.strip():
    raise ToolRetryError("Query cannot be empty -- provide a search term")
```

**load_sensitive_dataset** shows the compliance workflow. It calls `PrivateData().add_private_dataset()` to register the dataset with a sensitivity level. From that point on, `session_has_private_data()` returns `True` for this session, which triggers downstream effects: `@tool_permission(CONNECT)` tools become blocked, and if the client uses `MCPClientPrivateData`, all subsequent MCP calls route to the isolated server instance. The tool also demonstrates `ToolFatalError` for infrastructure failures that should abort the agent run rather than retry:

```python
try:
    pd = PrivateData()
    pd.add_private_dataset(dataset_name, DataSensitivity.CONFIDENTIAL)
except Exception as e:
    raise ToolFatalError(f"Compliance system unavailable: {e}") from e
```

### Error classification

The MCP wire protocol has a single error signal: `isError: true` with a text message. PydanticAI converts all such responses into `ModelRetry`, giving the LLM a chance to retry with different arguments. This is correct for bad-input errors but wasteful for infrastructure failures that will never recover.

The solution uses a text-level convention. `ToolRetryError` produces a plain error message that becomes a normal `ModelRetry`. `ToolFatalError` prepends `[FATAL] ` to the message. On the client side, `MCPServerStreamableHTTPStrict` overrides `direct_call_tool` to intercept the response: if the error text starts with `[FATAL] `, it raises `RuntimeError` instead of `ModelRetry`, and the agent run aborts immediately.

```python
class MCPServerStreamableHTTPStrict(MCPServerStreamableHTTP):
    async def direct_call_tool(self, name, args, metadata=None):
        try:
            return await super().direct_call_tool(name, args, metadata)
        except ModelRetry as e:
            msg = str(e)
            if msg.startswith(FATAL_PREFIX):
                raise RuntimeError(msg[len(FATAL_PREFIX):]) from e
            raise
```

Tool authors choose explicitly which class to raise. Unhandled exceptions (bugs) go through FastMCP's default path, producing `isError: true` without the `[FATAL] ` prefix. They become retries, which is harmless -- the model hits the retry limit and the run ends.

### Client-side isolation switching

The client connects to the template server using `get_mcp_client()`:

```python
server = get_mcp_client("template")
agent = get_agent(toolsets=[server])
```

When the `config.yaml` entry for `template` includes a `url_isolated` field, `get_mcp_client()` returns `MCPClientPrivateData` instead of `MCPServerStreamableHTTPStrict`. This wrapper holds two connections -- one to the normal server instance on the bridge network, one to the isolated instance with no external access. Both connections open when the context is entered.

Every tool call passes through `_target()`, which checks `session_has_private_data()`. Before the agent loads sensitive data, calls route to the normal instance. The moment `load_sensitive_dataset` flags the session, all subsequent calls route to the isolated instance. The switch is a one-way ratchet -- it never reverts within a session.

```yaml
# config.yaml
mcp_servers:
  template:
    type: client
    url: "http://template-server:8000/mcp"
    url_isolated: "http://template-server-isolated:8000/mcp"
    read_timeout: 60
```

When `url_isolated` is absent, `get_mcp_client()` returns a plain `MCPServerStreamableHTTPStrict` and the isolation switching does not apply. This makes the feature opt-in per server.

### Running the template

Start the server in one terminal:

```bash
fastmcp run agentic_patterns/examples/mcp/template/server.py:mcp
```

Run the client in another:

```bash
python agentic_patterns/examples/mcp/template/client.py
```

The client exercises three scenarios: a normal file read, a search that shows retryable errors work, and a sensitive dataset load that flags the session as containing private data. After the third call, any `CONNECT` tools on the server would be blocked, and if a `url_isolated` is configured, MCP traffic would have already switched to the isolated instance.
