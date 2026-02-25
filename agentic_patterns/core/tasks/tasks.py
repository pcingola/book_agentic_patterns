from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from agentic_patterns.core.tasks.models import Task
from agentic_patterns.core.tasks.state import TaskState


class Tasks:
    """Domain collection managing Task objects with dependency-aware queries.

    The on_update callback is fired by TaskStoreMemory after releasing its
    async lock. It accepts both sync and async callables.
    """

    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}
        self.on_update: Callable[["Tasks"], Any] | None = None

    def add(self, task: Task) -> Task:
        self._tasks[task.id] = task
        return task

    def dependents(self, task_id: str) -> list[Task]:
        return [t for t in self._tasks.values() if task_id in t.depends_on]

    def get(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    def list_by_state(self, state: TaskState) -> list[Task]:
        return sorted(
            [t for t in self._tasks.values() if t.state == state],
            key=lambda t: t.created_at,
        )

    def next_pending(self, exclude: set[str] | None = None) -> Task | None:
        exclude = exclude or set()
        for t in sorted(self._tasks.values(), key=lambda t: t.created_at):
            if t.state != TaskState.PENDING or t.id in exclude:
                continue
            if t.depends_on and not all(
                (dep := self._tasks.get(dep_id)) and dep.state == TaskState.COMPLETED
                for dep_id in t.depends_on
            ):
                continue
            return t
        return None

    def update_state(
        self,
        task_id: str,
        state: TaskState,
        *,
        result: str | None = None,
        error: str | None = None,
    ) -> Task | None:
        task = self._tasks.get(task_id)
        if task is None:
            return None
        task.state = state
        if result is not None:
            task.result = result
        if error is not None:
            task.error = error
        task.updated_at = datetime.now(timezone.utc)
        return task

    def __len__(self) -> int:
        return len(self._tasks)

    _STATE_MARKER = {
        TaskState.COMPLETED: "[x]",
        TaskState.RUNNING: "[~]",
        TaskState.FAILED: "[!]",
        TaskState.CANCELLED: "[-]",
    }

    def __str__(self) -> str:
        if not self._tasks:
            return "Tasks: (empty)"
        sorted_tasks = sorted(self._tasks.values(), key=lambda t: t.created_at)
        lines: list[str] = []
        for t in sorted_tasks:
            marker = self._STATE_MARKER.get(t.state, "[ ]")
            agent = t.metadata.get("agent_name", "?")
            desc = t.input[:70] + ("..." if len(t.input) > 70 else "")
            line = f"  {marker} {t.id}. ({agent}) {desc}"
            if t.depends_on:
                line += f"\n       depends on: {', '.join(t.depends_on)}"
            lines.append(line)
        return "\n".join(lines)
