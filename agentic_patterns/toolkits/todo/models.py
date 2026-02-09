"""Data models for task management."""

import json
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Self

from pydantic import BaseModel, Field

from agentic_patterns.core.workspace import workspace_to_host_path

TASK_LIST_FILE = PurePosixPath("/workspace/todo/tasks.json")


class TaskState(str, Enum):
    """Task state enumeration."""
    COMPLETED = "completed"
    FAILED = "failed"
    IN_PROGRESS = "in_progress"
    PENDING = "pending"

    def __str__(self) -> str:
        return self.value


class Task(BaseModel):
    """Hierarchical task with description, state, and optional subtasks."""
    description: str
    state: TaskState = TaskState.PENDING
    parent: "TaskList | None" = None
    subtasks: "TaskList | None" = None

    def model_post_init(self, __context: object) -> None:
        if self.subtasks is None:
            self.subtasks = TaskList(parent_task=self)

    def add_task(self, description: str) -> "Task":
        """Add a subtask."""
        if self.subtasks is None:
            self.subtasks = TaskList(parent_task=self)
        return self.subtasks.add_task(description)

    def delete(self, task_id: str) -> bool:
        """Delete a subtask by its local index (e.g. '2')."""
        if self.subtasks is None:
            return False
        try:
            index = int(task_id) - 1
            if 0 <= index < len(self.subtasks.tasks):
                self.subtasks.tasks.pop(index)
                return True
            return False
        except (ValueError, IndexError):
            return False

    def get_id(self, parent_id: str = "") -> str:
        """Generate the hierarchical ID for this task."""
        if not self.parent or not self.parent.tasks:
            return "1"
        for i, task in enumerate(self.parent.tasks, 1):
            if task is self:
                return f"{parent_id}.{i}" if parent_id else str(i)
        return "?"

    def to_dict(self) -> dict:
        """Convert to dict without circular parent references."""
        return {
            "description": self.description,
            "state": self.state.value,
            "subtasks": self.subtasks.to_dict() if self.subtasks else None,
        }

    def to_markdown(self, level: int = 0, parent_id: str = "") -> str:
        """Render as markdown checkbox line with subtasks."""
        task_id = self.get_id(parent_id)
        match self.state:
            case TaskState.PENDING:
                checkbox = " "
            case TaskState.IN_PROGRESS:
                checkbox = "."
            case TaskState.COMPLETED:
                checkbox = "x"
            case TaskState.FAILED:
                checkbox = "F"
        indent = "  " * level
        result = f"{indent}- [{checkbox}] {task_id}: {self.description}\n"
        assert self.subtasks is not None
        if self.subtasks.tasks:
            for subtask in self.subtasks.tasks:
                result += subtask.to_markdown(level + 1, task_id)
        return result

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Task):
            return False
        if self.description != other.description or self.state != other.state:
            return False
        if self.subtasks is not None and other.subtasks is not None:
            if len(self.subtasks.tasks) != len(other.subtasks.tasks):
                return False
            for i, task in enumerate(self.subtasks.tasks):
                if task != other.subtasks.tasks[i]:
                    return False
        elif self.subtasks is not None or other.subtasks is not None:
            return False
        return True

    def __getitem__(self, key: str | int) -> "Task | None":
        if self.subtasks is None:
            return None
        return self.subtasks[key]

    def __repr__(self) -> str:
        return self.to_markdown()

    def __str__(self) -> str:
        return self.to_markdown()


class TaskList(BaseModel):
    """Collection of tasks with persistence via workspace isolation."""
    tasks: list[Task] = Field(default_factory=list)
    parent_task: Task | None = None

    def add_task(self, description: str) -> Task:
        task = Task(description=description, parent=self)
        self.tasks.append(task)
        return task

    def delete(self, task_id: str) -> bool:
        """Delete a task by hierarchical ID (e.g. '1.3.2')."""
        if not task_id or not self.tasks:
            return False
        id_parts = task_id.split(".")
        if len(id_parts) > 1:
            parent_task = self.get_task_by_id(".".join(id_parts[:-1]))
            if parent_task:
                return parent_task.delete(id_parts[-1])
            return False
        try:
            index = int(id_parts[0]) - 1
            if 0 <= index < len(self.tasks):
                self.tasks.pop(index)
                return True
            return False
        except (ValueError, IndexError):
            return False

    def get_task_by_id(self, task_id: str) -> Task | None:
        """Get a task by hierarchical ID (e.g. '1.3.2')."""
        if not task_id or not self.tasks:
            return None
        id_parts = task_id.split(".")
        try:
            index = int(id_parts[0]) - 1
            if index < 0 or index >= len(self.tasks):
                return None
            task = self.tasks[index]
            assert task.subtasks is not None
            if len(id_parts) > 1:
                return task.subtasks.get_task_by_id(".".join(id_parts[1:]))
            return task
        except (ValueError, IndexError):
            return None

    @classmethod
    def load(cls) -> Self:
        """Load task list from workspace."""
        file_path = workspace_to_host_path(TASK_LIST_FILE)
        if not file_path.exists():
            return cls()
        with open(file_path) as f:
            data = json.load(f)
        task_list = cls()

        def create_tasks(task_data_list: list[dict], parent_list: "TaskList") -> None:
            for task_data in task_data_list:
                task = Task(description=task_data["description"], state=TaskState(task_data["state"]), parent=parent_list)
                parent_list.tasks.append(task)
                if task_data.get("subtasks") and task_data["subtasks"].get("tasks"):
                    assert task.subtasks is not None
                    create_tasks(task_data["subtasks"]["tasks"], task.subtasks)

        if "tasks" in data:
            create_tasks(data["tasks"], task_list)
        return task_list

    def save(self) -> Path:
        """Save task list to workspace."""
        file_path = workspace_to_host_path(TASK_LIST_FILE)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w") as f:
            f.write(json.dumps(self.to_dict(), indent=2))
        return file_path

    def to_dict(self) -> dict:
        return {"tasks": [task.to_dict() for task in self.tasks]}

    def to_markdown(self) -> str:
        result = "# Task List\n\n"
        for task in self.tasks:
            result += task.to_markdown()
        return result

    def update_task_state(self, task_id: str, state: TaskState) -> bool:
        task = self.get_task_by_id(task_id)
        if task:
            task.state = state
            return True
        return False

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TaskList):
            return False
        if len(self.tasks) != len(other.tasks):
            return False
        for i, task in enumerate(self.tasks):
            if task != other.tasks[i]:
                return False
        return True

    def __getitem__(self, key: str | int) -> Task | None:
        if isinstance(key, int):
            try:
                return self.tasks[key - 1]
            except IndexError:
                return None
        return self.get_task_by_id(key)

    def __repr__(self) -> str:
        return self.to_markdown()

    def __str__(self) -> str:
        return self.to_markdown()
