"""JWT token generation and validation for cross-layer identity propagation."""

import time

import jwt

from agentic_patterns.core.config.config import JWT_ALGORITHM, JWT_SECRET


def create_token(user_id: str, session_id: str, expires_in: int = 3600) -> str:
    """Create a JWT carrying user identity claims."""
    now = int(time.time())
    payload = {
        "sub": user_id,
        "session_id": session_id,
        "iat": now,
        "exp": now + expires_in,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Validate a JWT and return its claims. Raises jwt.InvalidTokenError on failure."""
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
