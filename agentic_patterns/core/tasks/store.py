import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path

from agentic_patterns.core.config.config import DATA_DIR
from agentic_patterns.core.tasks.models import Task, TaskEvent
from agentic_patterns.core.tasks.state import TaskState

logger = logging.getLogger(__name__)

DEFAULT_TASKS_DIR = DATA_DIR / "tasks"


class TaskStore(ABC):
    """Abstract base class defining the task storage contract."""

    @abstractmethod
    async def add_event(self, task_id: str, event: TaskEvent) -> None: ...

    @abstractmethod
    async def create(self, task: Task) -> Task: ...

    @abstractmethod
    async def get(self, task_id: str) -> Task | None: ...

    @abstractmethod
    async def list_by_state(self, state: TaskState) -> list[Task]: ...

    @abstractmethod
    async def next_pending(self) -> Task | None: ...

    @abstractmethod
    async def update_state(self, task_id: str, state: TaskState, *, result: str | None = None, error: str | None = None) -> Task | None: ...


class TaskStoreJson(TaskStore):
    """JSON file-backed task store. One JSON file per task."""

    def __init__(self, directory: Path = DEFAULT_TASKS_DIR) -> None:
        self._dir = directory
        self._dir.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()

    def _task_path(self, task_id: str) -> Path:
        return self._dir / f"{task_id}.json"

    def _read(self, task_id: str) -> Task | None:
        path = self._task_path(task_id)
        if not path.exists():
            return None
        return Task.model_validate_json(path.read_text())

    def _write(self, task: Task) -> None:
        self._task_path(task.id).write_text(task.model_dump_json(indent=2))

    async def add_event(self, task_id: str, event: TaskEvent) -> None:
        async with self._lock:
            task = self._read(task_id)
            if task is None:
                return
            task.events.append(event)
            task.updated_at = datetime.now(timezone.utc)
            self._write(task)

    async def create(self, task: Task) -> Task:
        async with self._lock:
            self._write(task)
            logger.debug("Created task %s", task.id[:8])
            return task

    async def get(self, task_id: str) -> Task | None:
        async with self._lock:
            return self._read(task_id)

    async def list_by_state(self, state: TaskState) -> list[Task]:
        async with self._lock:
            tasks = []
            for path in self._dir.glob("*.json"):
                task = Task.model_validate_json(path.read_text())
                if task.state == state:
                    tasks.append(task)
            return sorted(tasks, key=lambda t: t.created_at)

    async def next_pending(self) -> Task | None:
        tasks = await self.list_by_state(TaskState.PENDING)
        return tasks[0] if tasks else None

    async def update_state(self, task_id: str, state: TaskState, *, result: str | None = None, error: str | None = None) -> Task | None:
        async with self._lock:
            task = self._read(task_id)
            if task is None:
                return None
            task.state = state
            if result is not None:
                task.result = result
            if error is not None:
                task.error = error
            task.updated_at = datetime.now(timezone.utc)
            self._write(task)
            logger.debug("Task %s -> %s", task_id[:8], state.value)
            return task
