# Plan: User/Session Propagation Across Layers

## Problem

The stack has multiple layers (UI -> Agent -> A2A -> Sub-Agent -> MCP -> Tool) but user identity only lives in contextvars (`user_session.py`). There is no mechanism to propagate identity across network boundaries (MCP HTTP calls, A2A delegation). Each hop loses track of who the user is.

## Design

Each layer uses its own standard transport mechanism. The libraries (FastMCP, PydanticAI, fasta2a, httpx) already provide the plumbing for auth at each hop. The missing piece is glue code that bridges JWT tokens to our contextvars-based identity system.

The token carries `{"sub": "<user_id>", "session_id": "<session_id>", "exp": ...}` and is validated independently at each server. After validation, the server calls `set_user_session()` so all downstream code (workspace, connectors, etc.) works unchanged.

```
UI (login) --> set_user_session()
  |
  Agent (PydanticAI deps)
  |
  |-- MCP call --> process_tool_call injects Bearer JWT
  |                --> FastMCP JWTVerifier validates
  |                    --> middleware calls set_user_session()
  |                        --> workspace, connectors work as-is
  |
  |-- A2A delegation --> httpx sends Authorization: Bearer JWT
                         --> A2A server validates
                             --> set_user_session()
                                 --> sub-agent repeats same pattern
```

For the PoC, all services share an HMAC secret (HS256). Production would use asymmetric keys with JWKS endpoints. The MCP spec forbids token passthrough, but with a shared secret the same JWT is valid at every hop since all services are the same trust domain.

## What Libraries Already Provide

**FastMCP**: `JWTVerifier` (JWKS, HMAC, static key), `get_access_token()` DI, `AccessToken.claims`, `AuthMiddleware`, `require_scopes()`, session state.

**PydanticAI**: `process_tool_call` callback on `MCPServerStreamableHTTP`/`MCPServerStdio` -- receives `RunContext` (with deps) and can inject metadata or headers into MCP tool calls.

**fasta2a**: `A2AClient` wraps `httpx.AsyncClient` (accessible as `client.http_client`) -- supports setting auth headers. Agent card declares `securitySchemes`.

**httpx**: `auth` parameter, custom headers, `BearerAuth`.

## Changes

### 1. `core/auth.py` (new, ~40 lines)

JWT generation and validation helpers using PyJWT with HS256.

- `create_token(user_id, session_id, expires_in=3600) -> str` -- encodes claims (`sub`, `session_id`, `exp`, `iat`) with the shared secret.
- `decode_token(token) -> dict` -- validates and returns claims. Raises on invalid/expired.
- Secret and algorithm read from config/env (`JWT_SECRET`, `JWT_ALGORITHM`).

This covers the generation side. The validation side for FastMCP servers uses `JWTVerifier` directly (no custom code needed).

### 2. `core/user_session.py` (extend, ~10 lines)

Add `set_user_session_from_token(token: str)` that decodes a JWT and calls `set_user_session()`. Convenience for A2A servers and other non-FastMCP entry points that receive a raw token string.

### 3. `core/mcp.py` (extend, ~15 lines)

Extend `get_mcp_client()` to accept optional `bearer_token` parameter. When provided, passes it to `MCPServerStreamableHTTP` via `headers={"Authorization": f"Bearer {token}"}`.

Add a reusable `create_process_tool_call(get_token)` factory that returns a `process_tool_call` callback. The callback calls `get_token()` (e.g. reads from deps or contextvars) and injects it as metadata into MCP tool calls. This bridges PydanticAI's `RunContext` to MCP request metadata.

### 4. `core/mcp.py` or `core/auth.py` (extend, ~15 lines)

A FastMCP middleware function `auth_session_middleware` that, on each request, reads `get_access_token()` and calls `set_user_session()`. Intended to be added to FastMCP servers via `server.add_middleware()`.

```python
class AuthSessionMiddleware(Middleware):
    async def on_request(self, context, call_next):
        token = get_access_token()
        if token:
            set_user_session(token.claims["sub"], token.claims.get("session_id", DEFAULT_SESSION_ID))
        return await call_next(context)
```

### 5. `core/a2a/client.py` + `core/a2a/config.py` (extend, ~10 lines)

Add optional `bearer_token` to `A2AClientConfig`. In `A2AClientExtended.__init__`, if token is present, set the `Authorization` header on the underlying `httpx.AsyncClient`.

### 6. Config (`config.py`, `.env`)

Add `JWT_SECRET` and `JWT_ALGORITHM` (default `HS256`) to env/config.

## What Does NOT Change

- `workspace.py`, connectors, and all code that reads `get_user_id()`/`get_session_id()` -- unchanged, they keep reading from contextvars.
- No OAuth server, no PKCE, no DCR, no token refresh -- out of scope for PoC.
- No changes to MCP or A2A protocol semantics.

## Dependencies

- `PyJWT` (add to `pyproject.toml`).
