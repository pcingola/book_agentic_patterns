"""FastMCP middleware for authentication and session management."""

from fastmcp.server.dependencies import get_access_token
from fastmcp.server.middleware import Middleware

from agentic_patterns.core.config.config import DEFAULT_SESSION_ID
from agentic_patterns.core.user_session import set_user_session


class AuthSessionMiddleware(Middleware):
    """FastMCP middleware that sets user session from the access token claims."""

    async def on_request(self, context, call_next):
        token = get_access_token()
        if token:
            set_user_session(token.claims["sub"], token.claims.get("session_id", DEFAULT_SESSION_ID))
        return await call_next(context)
