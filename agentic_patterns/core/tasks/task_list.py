"""TaskList: file-backed task storage with dependency management."""

import asyncio
import fcntl
from pathlib import Path

from agentic_patterns.core.tasks.task import Task
from agentic_patterns.core.tasks.task_status import TaskStatus


class TaskList:
    """Manages tasks persisted as individual JSON files.

    Storage layout: base_dir / 1.json, 2.json, ...
    """

    def __init__(self, base_dir: Path):
        self._base_dir = base_dir
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()

    @property
    def base_dir(self) -> Path:
        return self._base_dir

    async def create(
        self,
        subject: str,
        description: str,
        *,
        active_form: str | None = None,
        metadata: dict | None = None,
    ) -> Task:
        async with self._lock:
            task_id = self._next_id()
            task = Task(
                id=task_id,
                subject=subject,
                description=description,
                active_form=active_form,
                metadata=metadata or {},
            )
            self._write_task(task)
            return task

    async def get(self, task_id: str) -> Task | None:
        async with self._lock:
            return self._read_task(task_id)

    async def list_all(self) -> list[Task]:
        """Return summary of all tasks (without metadata), sorted by ID."""
        async with self._lock:
            tasks = []
            for path in sorted(
                self._base_dir.glob("*.json"), key=lambda p: int(p.stem)
            ):
                task = self._read_task_from_path(path)
                if task:
                    # Summary view: strip metadata
                    task.metadata = {}
                    tasks.append(task)
            return tasks

    async def update(
        self,
        task_id: str,
        *,
        status: TaskStatus | None = None,
        subject: str | None = None,
        description: str | None = None,
        active_form: str | None = None,
        owner: str | None = None,
        metadata: dict | None = None,
        add_blocks: list[str] | None = None,
        add_blocked_by: list[str] | None = None,
    ) -> Task | None:
        async with self._lock:
            task = self._read_task(task_id)
            if task is None:
                return None

            # Handle deletion
            if status == TaskStatus.DELETED:
                self._delete_task(task_id)
                task.status = TaskStatus.DELETED
                return task

            # Block transition to in_progress if task is blocked
            if status == TaskStatus.IN_PROGRESS and self._is_blocked(task):
                raise ValueError(
                    f"Task {task_id} is blocked and cannot transition to in_progress"
                )

            if status is not None:
                task.status = status
            if subject is not None:
                task.subject = subject
            if description is not None:
                task.description = description
            if active_form is not None:
                task.active_form = active_form
            if owner is not None:
                task.owner = owner

            # Metadata merge: null values delete keys
            if metadata is not None:
                for k, v in metadata.items():
                    if v is None:
                        task.metadata.pop(k, None)
                    else:
                        task.metadata[k] = v

            # Bidirectional dependency sync
            if add_blocks:
                for target_id in add_blocks:
                    if target_id not in task.blocks:
                        task.blocks.append(target_id)
                    self._sync_dependency(target_id, task_id, "blocked_by")

            if add_blocked_by:
                for target_id in add_blocked_by:
                    if target_id not in task.blocked_by:
                        task.blocked_by.append(target_id)
                    self._sync_dependency(target_id, task_id, "blocks")

            self._write_task(task)
            return task

    async def next_available(self, *, owner: str | None = None) -> Task | None:
        """Return the first pending, unblocked task (lowest ID). Optionally filter by owner."""
        async with self._lock:
            for path in sorted(
                self._base_dir.glob("*.json"), key=lambda p: int(p.stem)
            ):
                task = self._read_task_from_path(path)
                if task is None or task.status != TaskStatus.PENDING:
                    continue
                if owner is not None and task.owner != owner:
                    continue
                if not self._is_blocked(task):
                    return task
            return None

    # -- Internal helpers --

    def _is_blocked(self, task: Task) -> bool:
        """Check if any task in blocked_by is not completed."""
        for blocker_id in task.blocked_by:
            blocker = self._read_task(blocker_id)
            if blocker is None or blocker.status != TaskStatus.COMPLETED:
                return True
        return False

    def _next_id(self) -> str:
        existing = [
            int(p.stem) for p in self._base_dir.glob("*.json") if p.stem.isdigit()
        ]
        return str(max(existing, default=0) + 1)

    def _sync_dependency(self, target_id: str, source_id: str, field: str) -> None:
        """Add source_id to target's field (blocks or blocked_by) bidirectionally."""
        target = self._read_task(target_id)
        if target is None:
            return
        current = getattr(target, field)
        if source_id not in current:
            current.append(source_id)
            self._write_task(target)

    def _read_task(self, task_id: str) -> Task | None:
        path = self._base_dir / f"{task_id}.json"
        return self._read_task_from_path(path)

    def _read_task_from_path(self, path: Path) -> Task | None:
        if not path.exists():
            return None
        with open(path) as f:
            fcntl.flock(f, fcntl.LOCK_SH)
            try:
                return Task.from_json_file(f.read())
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)

    def _write_task(self, task: Task) -> None:
        path = self._base_dir / f"{task.id}.json"
        with open(path, "w") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                f.write(task.model_dump_json_file())
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)

    def _delete_task(self, task_id: str) -> None:
        path = self._base_dir / f"{task_id}.json"
        path.unlink(missing_ok=True)

    def __str__(self) -> str:
        tasks = []
        for path in sorted(self._base_dir.glob("*.json"), key=lambda p: int(p.stem)):
            task = self._read_task_from_path(path)
            if task:
                tasks.append(str(task))
        return "\n".join(tasks) if tasks else "(empty task list)"
