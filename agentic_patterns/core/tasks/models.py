import uuid
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class EventType(str, Enum):
    STATE_CHANGE = "state_change"
    PROGRESS = "progress"
    LOG = "log"


class TaskEvent(BaseModel):
    """Records state transitions and progress for observation."""
    task_id: str
    event_type: EventType
    payload: dict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Task(BaseModel):
    """A unit of work submitted to the broker and executed by a worker."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    state: str = "pending"
    input: str
    result: str | None = None
    error: str | None = None
    events: list[TaskEvent] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict = Field(default_factory=dict)

    def __str__(self) -> str:
        return f"Task(id={self.id[:8]}, state={self.state}, input={self.input[:40]})"
