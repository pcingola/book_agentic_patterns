# MCP Server Requirements

1. **Auth**: JWT via `AuthSessionMiddleware` -- extracts `sub`/`session_id` claims; tools access identity via `get_user_id()` / `get_session_id()` contextvars, never as parameters (`core/mcp.py`, `core/user_session.py`)
2. **Workspace**: All file I/O goes through `workspace_to_host_path()` / `host_to_workspace_path()` -- agents see `/workspace/...`, never host paths; directories isolated per user/session (`core/workspace.py`)
3. **Context**: Tools returning large results MUST use `@context_result()` to auto-truncate and save full output to workspace; named presets available (`"default"`, `"sql_query"`, `"log_search"`) with type-aware truncation (`core/context/`)
4. **Permissions**: Every tool MUST declare permissions with `@tool_permission(ToolPermission.READ|WRITE|CONNECT)`; `CONNECT` tools automatically blocked when session contains private data (`core/tools/permissions.py`, `core/compliance/private_data.py`)
5. **Compliance**: Tools reading sensitive data MUST call `PrivateData().add_private_dataset(name, sensitivity)` -- state persisted outside workspace to prevent agent tampering (`core/compliance/private_data.py`)
6. **Connectors**: Data operations live in connectors (inherit `Connector`, no MCP/PydanticAI deps, static methods, workspace isolation, `@context_result()`); tools wrap connectors adding decorators (`core/connectors/`)
7. **Config**: All server config MUST be in `config.yaml` under `mcp_servers` key with `${VAR}` env expansion; `.env` only for main environment variables (`core/mcp.py`, `core/config/`)
8. **Errors**: Two-tier exceptions: retryable tool errors (user-correctable, LLM can retry) vs code bugs (let propagate) -- never wrap entire tool in catch-all (`docs/mcp_template.md`)
9. **Docker / Network Isolation**: Three network modes driven by `DataSensitivity` -- `FULL` (bridge, no private data), `PROXIED` (Envoy whitelist, CONFIDENTIAL data), `NONE` (no network, SECRET data). Sensitivity is a one-way ratchet: it can escalate but never decrease within a session. The sandbox manager recreates the container with a more restrictive mode when sensitivity escalates mid-session; workspace volume survives the transition. For MCP servers, deploy two containers from the same image (one on bridge, one isolated); `MCPClientConfig.url_isolated` lets the client switch to the restricted instance automatically when private data enters the session (`core/sandbox/`, `core/compliance/private_data.py`, `core/mcp.py`)
10. **Testing**: Use FastMCP in-memory client for unit tests; structure in `tests/unit/` and `tests/integration/`


## Implementation plan

What already works: requirements 1-8 and 10 are satisfied by existing code (AuthSessionMiddleware, workspace helpers, @context_result, @tool_permission with CONNECT auto-blocking, PrivateData, Connector base, YAML config, FastMCP's ToolError). Requirement 9 is now implemented: `MCPClientPrivateData` provides client-side switching, `MCPServerStreamableHTTPStrict` handles fatal error classification.

Changes implemented in `core/mcp.py`:

1. **Done** -- `create_mcp_server(name)` -- factory that returns `FastMCP` with `AuthSessionMiddleware` already wired. Makes requirement 1 trivial for every new server.

2. **Done** -- `url_isolated` optional field on `MCPClientConfig`. When absent, behavior unchanged.

3. **Done** -- `MCPClientPrivateData` -- wrapper that holds two `MCPServerStreamableHTTPStrict` instances (normal and isolated), opens both on enter, and routes every call to the isolated instance once private data appears mid-session. The switch is a one-way ratchet.

4. **Done** -- Update `get_mcp_client()` to return `MCPClientPrivateData` when `url_isolated` is present in config, `MCPServerStreamableHTTPStrict` otherwise. Transparent to callers.

5. **Done** -- **Error classification** -- `ToolRetryError` (plain `ToolError`, LLM retries), `ToolFatalError` (prepends `[FATAL] ` prefix), `MCPServerStreamableHTTPStrict` (intercepts fatal errors and raises `RuntimeError` to abort the run).

6. **Done** -- **Template MCP server** (`examples/mcp/template/server.py`, `tools.py`) -- reference implementation demonstrating requirements 1-8: `create_mcp_server()` with `AuthSessionMiddleware`, tools with `@tool_permission`, workspace path translation, `@context_result()` for large results, `ToolRetryError` vs `ToolFatalError`, and `PrivateData` flagging.

7. **Done** -- **Template MCP client** (`examples/mcp/template/client.py`) -- agent that connects to the template server via `get_mcp_client()`, exercises the tools, and demonstrates error handling behavior (retryable vs fatal).

8. **Done** -- **Hands-on section** (`chapters/execution_infrastructure/hands_on_mcp_isolation.md`) -- walks through the template server and client, explaining how each requirement is satisfied by the code. Linked from `chapter.md`.


### MCPClientPrivateData

Wrapper that holds two `MCPServerStreamableHTTP` instances -- `_normal` and `_isolated` -- and opens both at context entry. Every call (`list_tools`, `call_tool`, etc.) is delegated to `_target()`, which checks `session_has_private_data()`. Once private data appears mid-session, all subsequent calls route to the isolated instance. The switch is a one-way ratchet: once `_is_isolated` is `True`, it never reverts.

This is NOT a subclass of `MCPServerStreamableHTTP`. It wraps two instances and implements the same interface PydanticAI expects for MCP toolsets. The exact base class or protocol to satisfy depends on PydanticAI's internal API -- check what `Agent(mcp_servers=[...])` expects each element to implement.

```python
class MCPClientPrivateData:
    def __init__(self, url: str, url_isolated: str, **kwargs):
        self._normal = MCPServerStreamableHTTP(url=url, **kwargs)
        self._isolated = MCPServerStreamableHTTP(url=url_isolated, **kwargs)
        self._is_isolated = False

    def _target(self) -> MCPServerStreamableHTTP:
        if not self._is_isolated:
            self._is_isolated = session_has_private_data()
        return self._isolated if self._is_isolated else self._normal

    async def __aenter__(self):
        await self._normal.__aenter__()
        await self._isolated.__aenter__()
        return self

    async def __aexit__(self, *args):
        await self._isolated.__aexit__(*args)
        await self._normal.__aexit__(*args)

    # Delegate all toolset methods to _target():
    # list_tools, call_tool, direct_call_tool, get_tools, etc.
```

Both connections are alive for the entire session. `_target()` checks the flag on every call, so the switch can happen between any two tool calls within the same open context. No teardown or reconnection needed.

```python
def get_mcp_client(name, config_path=None, bearer_token=None):
    config = _load_mcp_settings(config_path).get(name)
    headers = {"Authorization": f"Bearer {bearer_token}"} if bearer_token else None
    if config.url_isolated:
        return MCPClientPrivateData(
            url=config.url, url_isolated=config.url_isolated,
            timeout=config.read_timeout, headers=headers,
        )
    return MCPServerStreamableHTTP(url=config.url, timeout=config.read_timeout, headers=headers)
```


### Error classification

The MCP wire protocol has a single error signal: `isError: true` with a text message. FastMCP converts all tool exceptions (both explicit `ToolError` raises and unhandled exceptions) into this format. PydanticAI's MCP toolset then converts all `isError: true` responses into `ModelRetry`, giving the LLM a chance to retry with different arguments. This is correct for bad-input errors but wasteful for infrastructure failures that will never recover.

The solution uses a text-level convention: fatal errors carry a `[FATAL] ` prefix in the message. Two exception classes on the server side, one client subclass on the client side.

**Server side** -- two classes in `core/mcp.py`, both inheriting from FastMCP's `ToolError`:

```python
FATAL_PREFIX = "[FATAL] "

class ToolRetryError(ToolError):
    """Retryable: the LLM picked bad arguments, let it try again."""
    pass

class ToolFatalError(ToolError):
    """Fatal: infrastructure failure, abort the agent run."""
    def __init__(self, message: str):
        super().__init__(f"{FATAL_PREFIX}{message}")
```

Both serialize as `isError: true` on the wire. The only difference is the prefix in the text. Tool authors choose explicitly:

```python
@mcp.tool
async def query(sql: str) -> str:
    if not sql.strip():
        raise ToolRetryError("SQL cannot be empty")       # LLM retries
    try:
        return db.execute(sql)
    except ConnectionError as e:
        raise ToolFatalError(f"Database unreachable: {e}") # run aborts
```

Unhandled exceptions (bugs) go through FastMCP's default path, which also produces `isError: true` but without the `[FATAL] ` prefix. They become retries, which is harmless -- the model hits the retry limit and the run ends. For known fatal conditions, tool authors use `ToolFatalError` explicitly.

**Client side** -- `MCPServerStreamableHTTPStrict(MCPServerStreamableHTTP)` in `core/mcp.py`. Overrides the method that processes `CallToolResult` responses. When `isError` is `true` and the text starts with `[FATAL] `, strips the prefix and raises `RuntimeError(message)` -- which PydanticAI does not catch, so the agent run aborts immediately. Otherwise delegates to `super()`, which raises `ModelRetry` as usual.

```python
class MCPServerStreamableHTTPStrict(MCPServerStreamableHTTP):
    """MCP client that aborts the agent run on fatal tool errors."""
    # Override the call_tool result processing method.
    # Exact method name depends on PydanticAI internals -- check which
    # method inspects CallToolResult.isError and raises ModelRetry.
    # If text.startswith(FATAL_PREFIX): raise RuntimeError(text[len(FATAL_PREFIX):])
    # Else: super() handles it (ModelRetry)
```

`get_mcp_client()` returns this subclass instead of the plain class, so the error-aware behavior is transparent to callers.
