"""Common Chainlit handlers for authentication, data layer, and chat resume."""

from logging import getLogger

import chainlit as cl

from agentic_patterns.core.config.config import USER_DATABASE_FILE
from agentic_patterns.core.ui.auth import UserDatabase
from agentic_patterns.core.ui.chainlit.data_layer import get_sqlite_data_layer
from agentic_patterns.core.user_session import set_user_session

logger = getLogger(__name__)

HISTORY = "history"


def register_auth_callback():
    """Register password authentication callback."""

    @cl.password_auth_callback
    async def auth_callback(username: str, password: str) -> cl.User | None:
        db = UserDatabase(USER_DATABASE_FILE)
        user = db.authenticate(username, password)
        if user:
            return cl.User(
                identifier=user.username,
                metadata={"role": user.role, "provider": "credentials"},
            )
        return None


def register_data_layer():
    """Register SQLite data layer for chat persistence."""

    @cl.data_layer
    def get_data_layer():
        return get_sqlite_data_layer()


def register_chat_resume():
    """Register chat resume handler to restore conversation history."""

    @cl.on_chat_resume
    async def on_chat_resume(thread):
        logger.info("Chat resumed, restoring history.")
        steps = thread["steps"]
        history = []
        for step in steps:
            if step["type"] in ("user_message", "assistant_message"):
                message = step["input"] + "\n" + step["output"]
                message = message.strip()
                history.append(message)
        logger.info(f"Restored history with {len(history)} messages")
        cl.user_session.set(HISTORY, history)


def setup_user_session():
    """Set user and session IDs from Chainlit context for downstream use."""
    user = cl.user_session.get("user")
    thread_id = cl.user_session.get("id")
    user_id = user.identifier if user else "anonymous"
    session_id = thread_id or "default"
    set_user_session(user_id, session_id)
    logger.info(f"User session set: user_id={user_id}, session_id={session_id}")


def register_all():
    """Register all standard Chainlit handlers (auth, data layer, chat resume)."""
    register_auth_callback()
    register_data_layer()
    register_chat_resume()
