import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path

from agentic_patterns.core.config.config import DATA_DIR
from agentic_patterns.core.tasks.models import Task, TaskEvent
from agentic_patterns.core.tasks.state import TaskState
from agentic_patterns.core.tasks.tasks import Tasks

logger = logging.getLogger(__name__)

DEFAULT_TASKS_DIR = DATA_DIR / "tasks"


class TaskStore(ABC):
    """Abstract base class defining the task storage contract."""

    @abstractmethod
    async def add_event(self, task_id: str, event: TaskEvent) -> None: ...

    @abstractmethod
    async def create(self, task: Task) -> Task: ...

    @abstractmethod
    async def dependents(self, task_id: str) -> list[Task]:
        """Return tasks that depend on the given task ID."""
        ...

    @abstractmethod
    async def get(self, task_id: str) -> Task | None: ...

    @abstractmethod
    async def list_by_state(self, state: TaskState) -> list[Task]: ...

    @abstractmethod
    async def next_pending(self, exclude: set[str] | None = None) -> Task | None: ...

    @abstractmethod
    async def update_state(
        self,
        task_id: str,
        state: TaskState,
        *,
        result: str | None = None,
        error: str | None = None,
    ) -> Task | None: ...


class TaskStoreMemory(TaskStore):
    """In-memory task store backed by a Tasks collection. Ideal for notebooks."""

    def __init__(self, tasks: Tasks | None = None) -> None:
        self.tasks = tasks if tasks is not None else Tasks()
        self._lock = asyncio.Lock()

    async def add_event(self, task_id: str, event: TaskEvent) -> None:
        async with self._lock:
            task = self.tasks.get(task_id)
            if task is None:
                return
            task.events.append(event)
            task.updated_at = datetime.now(timezone.utc)

    async def create(self, task: Task) -> Task:
        async with self._lock:
            self.tasks.add(task)
            logger.debug("Created task %s", task.id)
        await self._notify()
        return task

    async def dependents(self, task_id: str) -> list[Task]:
        async with self._lock:
            return self.tasks.dependents(task_id)

    async def get(self, task_id: str) -> Task | None:
        async with self._lock:
            return self.tasks.get(task_id)

    async def list_by_state(self, state: TaskState) -> list[Task]:
        async with self._lock:
            return self.tasks.list_by_state(state)

    async def next_pending(self, exclude: set[str] | None = None) -> Task | None:
        async with self._lock:
            return self.tasks.next_pending(exclude)

    async def update_state(
        self,
        task_id: str,
        state: TaskState,
        *,
        result: str | None = None,
        error: str | None = None,
    ) -> Task | None:
        async with self._lock:
            task = self.tasks.update_state(task_id, state, result=result, error=error)
            if task:
                logger.debug("Task %s -> %s", task_id, state.value)
        await self._notify()
        return task

    async def _notify(self) -> None:
        cb = self.tasks.on_update
        if cb is None:
            return
        if asyncio.iscoroutinefunction(cb):
            await cb(self.tasks)
        else:
            cb(self.tasks)


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
            logger.debug("Created task %s", task.id)
            return task

    async def dependents(self, task_id: str) -> list[Task]:
        async with self._lock:
            result = []
            for path in self._dir.glob("*.json"):
                task = Task.model_validate_json(path.read_text())
                if task_id in task.depends_on:
                    result.append(task)
            return result

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

    async def next_pending(self, exclude: set[str] | None = None) -> Task | None:
        async with self._lock:
            exclude = exclude or set()
            pending = []
            all_tasks: dict[str, Task] = {}
            for path in self._dir.glob("*.json"):
                task = Task.model_validate_json(path.read_text())
                all_tasks[task.id] = task
                if task.state == TaskState.PENDING and task.id not in exclude:
                    pending.append(task)
            pending.sort(key=lambda t: t.created_at)
            for t in pending:
                if t.depends_on and not all(
                    all_tasks.get(dep_id)
                    and all_tasks[dep_id].state == TaskState.COMPLETED
                    for dep_id in t.depends_on
                ):
                    continue
                return t
            return None

    async def update_state(
        self,
        task_id: str,
        state: TaskState,
        *,
        result: str | None = None,
        error: str | None = None,
    ) -> Task | None:
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
            logger.debug("Task %s -> %s", task_id, state.value)
            return task
