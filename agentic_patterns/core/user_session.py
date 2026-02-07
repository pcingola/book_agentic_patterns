"""User/session context for the current async task via contextvars.

Call set_user_session() once at the request boundary (middleware, MCP handler, etc.).
All downstream code can call get_user_id() / get_session_id() without propagating context.
"""

from contextvars import ContextVar

from agentic_patterns.core.auth import decode_token
from agentic_patterns.core.config.config import DEFAULT_SESSION_ID, DEFAULT_USER_ID

_user_id: ContextVar[str] = ContextVar("user_id", default=DEFAULT_USER_ID)
_session_id: ContextVar[str] = ContextVar("session_id", default=DEFAULT_SESSION_ID)


def get_session_id() -> str:
    return _session_id.get()


def get_user_id() -> str:
    return _user_id.get()


def set_user_session(user_id: str, session_id: str) -> None:
    _user_id.set(user_id)
    _session_id.set(session_id)


def set_user_session_from_token(token: str) -> None:
    """Decode a JWT and set user session from its claims."""
    claims = decode_token(token)
    set_user_session(claims["sub"], claims.get("session_id", DEFAULT_SESSION_ID))
