import itertools
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field

from agentic_patterns.core.tasks.state import TaskState

_task_counter = itertools.count(1)


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

    id: str = Field(default_factory=lambda: str(next(_task_counter)))
    state: TaskState = TaskState.PENDING
    input: str
    result: str | None = None
    error: str | None = None
    depends_on: list[str] = Field(default_factory=list)
    events: list[TaskEvent] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict = Field(default_factory=dict)

    def __str__(self) -> str:
        deps = f", deps={self.depends_on}" if self.depends_on else ""
        return f"Task({self.id}, {self.state.value}{deps}, {self.input[:40]})"
