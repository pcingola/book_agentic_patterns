## Session propagation

The previous section dealt with errors, cancellation, and human interaction -- signals that flow in response to something going wrong or something needing attention. Session propagation addresses a quieter but equally fundamental concern: knowing *who* is making the request at every layer of the stack. When a user logs in through the UI and asks the agent to write a file to their workspace, the workspace module needs to know which user directory to write into. When that agent delegates to a sub-agent via A2A, and the sub-agent calls an MCP tool that also writes to the workspace, the same identity must arrive at the same workspace directory. The user's identity must survive every network hop without any layer in between having to know or care about the layers above or below it.

Within a single Python process this is straightforward. Python's `contextvars` module provides task-local storage that propagates automatically through `async` call chains. The project's `user_session.py` exposes three functions: `set_user_session(user_id, session_id)` sets the identity at the request boundary, and `get_user_id()` / `get_session_id()` read it from anywhere downstream. The workspace module calls `get_user_id()` and `get_session_id()` to construct the host path (`data/workspaces/{user_id}/{session_id}/`), and connectors, context decorators, and any other code that needs the identity do the same. As long as everything runs in the same process, `set_user_session()` at the top is enough and every function below sees the right values.

The problem appears at network boundaries. When the agent makes an HTTP call to an MCP server, the server is a separate process with its own `contextvars`. The user identity set in the agent's process does not exist there. The same happens when the agent delegates work to a sub-agent over A2A -- the sub-agent runs in its own process, potentially on a different machine, and has no knowledge of the original user. Each hop across a network boundary resets the identity to the default values, and the workspace writes to the wrong directory.

The solution is JWT tokens. A JSON Web Token encodes the user identity as signed claims (`sub` for the user ID, `session_id` for the session) and can be attached to any HTTP request as a standard `Authorization: Bearer` header. Both MCP and A2A are HTTP-based protocols, so they already have the plumbing for authorization headers. The task is not to invent a new identity mechanism but to wire the existing one through each boundary: encode the identity into a token before crossing the boundary, attach it to the HTTP request, validate it on the other side, and call `set_user_session()` so the downstream code works unchanged.


### The token

The project's `auth.py` provides two functions. `create_token(user_id, session_id)` encodes the claims with an HMAC-SHA256 signature and a configurable expiry (one hour by default). `decode_token(token)` validates the signature and expiry, returning the claims dict or raising `jwt.InvalidTokenError` if the token is tampered with or expired.

```python
def create_token(user_id: str, session_id: str, expires_in: int = 3600) -> str:
    now = int(time.time())
    payload = {"sub": user_id, "session_id": session_id, "iat": now, "exp": now + expires_in}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
```

The secret (`JWT_SECRET`) and algorithm (`JWT_ALGORITHM`) are read from environment variables with development defaults. For the proof-of-concept, all services in the stack share the same HMAC secret, which means the same token is valid everywhere. A production deployment would replace this with asymmetric keys (RS256 or ES256) and a JWKS endpoint, so servers can verify tokens without knowing the signing key. The point is that none of the propagation code needs to change when that happens -- only the key configuration.


### Crossing the MCP boundary

When PydanticAI calls an MCP tool, it goes through the `MCPServerStreamableHTTP` client, which makes an HTTP request to the MCP server. PydanticAI provides a `process_tool_call` callback that runs before each MCP tool invocation, receiving the run context, tool name, and arguments. ([PydanticAI][1]) The project uses this hook to inject the Bearer token.

The `create_process_tool_call` factory in `mcp.py` takes a `get_token` callable (a function that returns the current JWT, typically reading from the agent's dependencies or contextvars) and returns a callback that attaches the token to the MCP call metadata:

```python
def create_process_tool_call(get_token: Callable[[], str | None]):
    async def process_tool_call(ctx, tool_name, args):
        token = get_token()
        if token:
            args.setdefault("_metadata", {})["authorization"] = f"Bearer {token}"
        return args
    return process_tool_call
```

On the server side, FastMCP provides built-in JWT verification (`JWTVerifier`) and dependency injection for the access token (`get_access_token()`). ([FastMCP][2]) But verifying the token is not enough -- the server also needs to call `set_user_session()` so that workspace, connectors, and every other piece of code that reads from `contextvars` sees the right identity. The project's `AuthSessionMiddleware` handles this. It is a FastMCP middleware that runs on every request, reads the verified token claims, and sets the session:

```python
class AuthSessionMiddleware(Middleware):
    async def on_request(self, context, call_next):
        token = get_access_token()
        if token:
            set_user_session(
                token.claims["sub"],
                token.claims.get("session_id", DEFAULT_SESSION_ID),
            )
        return await call_next(context)
```

The effect is that an MCP tool function that calls `workspace_to_host_path()` or any other identity-dependent code gets the same user identity that was established in the UI, even though the tool runs in a different process. The tool author does not need to know about tokens, middleware, or propagation -- they just call `get_user_id()` and get the right answer.


### Crossing the A2A boundary

A2A delegation follows the same pattern with different plumbing. ([A2A][3]) The `A2AClientConfig` accepts an optional `bearer_token` field, and when present, `A2AClientExtended.__init__` sets the `Authorization` header on the underlying `httpx` client:

```python
class A2AClientExtended:
    def __init__(self, config: A2AClientConfig):
        self._client = A2AClient(base_url=config.url)
        if config.bearer_token:
            self._client.http_client.headers["Authorization"] = f"Bearer {config.bearer_token}"
```

Every subsequent request through that client -- `send_message`, `get_task`, `cancel_task` -- carries the token. On the receiving A2A server, the token arrives as a standard HTTP header. The server validates it and calls `set_user_session()`, just as the MCP middleware does. If the sub-agent then calls its own MCP tools, the same token (or a fresh one with the same claims) propagates further. The chain can be arbitrarily deep: UI to agent to sub-agent to sub-sub-agent, each boundary bridged by the same mechanism.


### The full path

Putting it together, the identity flows through the stack like this. The UI layer authenticates the user (login form, OAuth callback, API key -- whatever mechanism the frontend uses) and calls `set_user_session()` to establish the identity in the agent process. If the agent calls MCP tools, `create_process_tool_call` injects the JWT. The MCP server's `AuthSessionMiddleware` extracts the claims and restores the identity. If the agent delegates via A2A, the client sends the token in the HTTP header. The A2A server extracts and restores the identity. If the sub-agent calls its own MCP tools, the same injection happens again. At every layer, downstream code calls `get_user_id()` and gets the original user's identity.

```
UI (login)
  set_user_session("alice", "sess-42")
  |
  Agent process
  get_user_id() -> "alice"
  |
  |-- MCP call
  |     process_tool_call injects Bearer JWT
  |     |
  |     MCP Server process
  |       AuthSessionMiddleware -> set_user_session("alice", "sess-42")
  |       get_user_id() -> "alice"
  |       workspace writes to data/workspaces/alice/sess-42/
  |
  |-- A2A delegation
        httpx sends Authorization: Bearer JWT
        |
        A2A Server process
          token validated -> set_user_session("alice", "sess-42")
          get_user_id() -> "alice"
          |
          |-- MCP call (same pattern repeats)
```

The `user_session.py` module also provides a convenience function `set_user_session_from_token(token)` that combines decoding and session setting in one call. This is useful for entry points that receive a raw token string rather than structured claims -- for example, an A2A server handler that reads the `Authorization` header directly, or a script that needs to impersonate a user for batch processing.

The reason this works with so little code is that we are not building an authentication system. MCP and A2A are HTTP-based protocols, and HTTP has had authorization headers since 1996. FastMCP provides JWT verification out of the box. PydanticAI provides the `process_tool_call` hook for injecting metadata into MCP calls. The `httpx` client that A2A uses supports custom headers natively. The only project-specific code is the glue: generating the token (`auth.py`), managing the `contextvars` (`user_session.py`), and the middleware that bridges tokens back to `contextvars` at each server boundary. Everything else is standard HTTP machinery that these libraries already support.

[1]: https://ai.pydantic.dev/mcp/ "PydanticAI: MCP toolset"
[2]: https://gofastmcp.com/servers/auth "FastMCP: Authentication"
[3]: https://a2a-protocol.org/latest/specification/ "A2A Specification"
