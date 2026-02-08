"""Starlette middleware for A2A server authentication and session management."""

import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from agentic_patterns.core.user_session import set_user_session_from_token

logger = logging.getLogger(__name__)


class AuthSessionMiddleware(BaseHTTPMiddleware):
    """Extract Bearer token from Authorization header and set user session."""

    async def dispatch(self, request: Request, call_next) -> Response:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth.removeprefix("Bearer ")
            try:
                set_user_session_from_token(token)
            except Exception:
                logger.warning("Invalid Bearer token in A2A request")
        return await call_next(request)
