"""User feedback and session history persistence.

Stores feedback entries and conversation history as JSON files per session,
following the same directory pattern as PrivateData:
  FEEDBACK_DIR / user_id / session_id / {feedback.json, history.json}
"""

import logging
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter

from agentic_patterns.core.config.config import FEEDBACK_DIR
from agentic_patterns.core.user_session import get_session_id, get_user_id

logger = logging.getLogger(__name__)

FEEDBACK_FILENAME = "feedback.json"
HISTORY_FILENAME = "history.json"


class FeedbackType(str, Enum):
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    ERROR_REPORT = "error_report"
    COMMENT = "comment"


class FeedbackEntry(BaseModel):
    feedback_type: FeedbackType
    comment: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SessionFeedback(BaseModel):
    user_id: str
    session_id: str
    entries: list[FeedbackEntry] = []


def _session_dir(user_id: str | None, session_id: str | None) -> Path:
    uid = user_id or get_user_id()
    sid = session_id or get_session_id()
    return FEEDBACK_DIR / uid / sid


def add_feedback(
    feedback_type: FeedbackType,
    comment: str = "",
    user_id: str | None = None,
    session_id: str | None = None,
) -> None:
    """Append a feedback entry to the session's feedback.json."""
    session_feedback = get_feedback(user_id, session_id)
    session_feedback.entries.append(
        FeedbackEntry(feedback_type=feedback_type, comment=comment)
    )
    path = _session_dir(user_id, session_id) / FEEDBACK_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(session_feedback.model_dump_json(indent=2), encoding="utf-8")


def get_feedback(
    user_id: str | None = None, session_id: str | None = None
) -> SessionFeedback:
    """Load feedback for a session. Returns empty SessionFeedback if none exists."""
    uid = user_id or get_user_id()
    sid = session_id or get_session_id()
    path = _session_dir(user_id, session_id) / FEEDBACK_FILENAME
    if not path.exists():
        return SessionFeedback(user_id=uid, session_id=sid)
    return SessionFeedback.model_validate_json(path.read_text(encoding="utf-8"))


def load_session_history(
    user_id: str | None = None, session_id: str | None = None
) -> list[ModelMessage]:
    """Deserialize conversation history from history.json."""
    path = _session_dir(user_id, session_id) / HISTORY_FILENAME
    if not path.exists():
        return []
    return ModelMessagesTypeAdapter.validate_json(path.read_bytes())


def save_session_history(
    messages: list[ModelMessage],
    user_id: str | None = None,
    session_id: str | None = None,
) -> None:
    """Serialize conversation history to history.json."""
    path = _session_dir(user_id, session_id) / HISTORY_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(ModelMessagesTypeAdapter.dump_json(messages, indent=2))
