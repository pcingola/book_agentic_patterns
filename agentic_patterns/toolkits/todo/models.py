"""Data models for todo management."""

import json
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Self

from pydantic import BaseModel, Field

from agentic_patterns.core.workspace import workspace_to_host_path

TODO_LIST_FILE = PurePosixPath("/workspace/todo/tasks.json")


class TodoState(str, Enum):
    """Todo item state enumeration."""

    COMPLETED = "completed"
    FAILED = "failed"
    IN_PROGRESS = "in_progress"
    PENDING = "pending"

    def __str__(self) -> str:
        return self.value


class TodoItem(BaseModel):
    """Hierarchical todo item with description, state, and optional sub-items."""

    description: str
    state: TodoState = TodoState.PENDING
    parent: "TodoList | None" = None
    subtasks: "TodoList | None" = None

    def model_post_init(self, __context: object) -> None:
        if self.subtasks is None:
            self.subtasks = TodoList(parent_item=self)

    def add_item(self, description: str) -> "TodoItem":
        """Add a sub-item."""
        if self.subtasks is None:
            self.subtasks = TodoList(parent_item=self)
        return self.subtasks.add_item(description)

    def delete(self, item_id: str) -> bool:
        """Delete a sub-item by its local index (e.g. '2')."""
        if self.subtasks is None:
            return False
        try:
            index = int(item_id) - 1
            if 0 <= index < len(self.subtasks.items):
                self.subtasks.items.pop(index)
                return True
            return False
        except (ValueError, IndexError):
            return False

    def get_id(self, parent_id: str = "") -> str:
        """Generate the hierarchical ID for this item."""
        if not self.parent or not self.parent.items:
            return "1"
        for i, item in enumerate(self.parent.items, 1):
            if item is self:
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
        """Render as markdown checkbox line with sub-items."""
        item_id = self.get_id(parent_id)
        match self.state:
            case TodoState.PENDING:
                checkbox = " "
            case TodoState.IN_PROGRESS:
                checkbox = "."
            case TodoState.COMPLETED:
                checkbox = "x"
            case TodoState.FAILED:
                checkbox = "F"
        indent = "  " * level
        result = f"{indent}- [{checkbox}] {item_id}: {self.description}\n"
        assert self.subtasks is not None
        if self.subtasks.items:
            for sub_item in self.subtasks.items:
                result += sub_item.to_markdown(level + 1, item_id)
        return result

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TodoItem):
            return False
        if self.description != other.description or self.state != other.state:
            return False
        if self.subtasks is not None and other.subtasks is not None:
            if len(self.subtasks.items) != len(other.subtasks.items):
                return False
            for i, item in enumerate(self.subtasks.items):
                if item != other.subtasks.items[i]:
                    return False
        elif self.subtasks is not None or other.subtasks is not None:
            return False
        return True

    def __getitem__(self, key: str | int) -> "TodoItem | None":
        if self.subtasks is None:
            return None
        return self.subtasks[key]

    def __repr__(self) -> str:
        return self.to_markdown()

    def __str__(self) -> str:
        return self.to_markdown()


class TodoList(BaseModel):
    """Collection of todo items with persistence via workspace isolation."""

    items: list[TodoItem] = Field(default_factory=list)
    parent_item: TodoItem | None = None

    def add_item(self, description: str) -> TodoItem:
        item = TodoItem(description=description, parent=self)
        self.items.append(item)
        return item

    def delete(self, item_id: str) -> bool:
        """Delete an item by hierarchical ID (e.g. '1.3.2')."""
        if not item_id or not self.items:
            return False
        id_parts = item_id.split(".")
        if len(id_parts) > 1:
            parent_item = self.get_item_by_id(".".join(id_parts[:-1]))
            if parent_item:
                return parent_item.delete(id_parts[-1])
            return False
        try:
            index = int(id_parts[0]) - 1
            if 0 <= index < len(self.items):
                self.items.pop(index)
                return True
            return False
        except (ValueError, IndexError):
            return False

    def get_item_by_id(self, item_id: str) -> TodoItem | None:
        """Get an item by hierarchical ID (e.g. '1.3.2')."""
        if not item_id or not self.items:
            return None
        id_parts = item_id.split(".")
        try:
            index = int(id_parts[0]) - 1
            if index < 0 or index >= len(self.items):
                return None
            item = self.items[index]
            assert item.subtasks is not None
            if len(id_parts) > 1:
                return item.subtasks.get_item_by_id(".".join(id_parts[1:]))
            return item
        except (ValueError, IndexError):
            return None

    @classmethod
    def load(cls) -> Self:
        """Load todo list from workspace."""
        file_path = workspace_to_host_path(TODO_LIST_FILE)
        if not file_path.exists():
            return cls()
        with open(file_path) as f:
            data = json.load(f)
        todo_list = cls()

        def create_items(item_data_list: list[dict], parent_list: "TodoList") -> None:
            for item_data in item_data_list:
                item = TodoItem(
                    description=item_data["description"],
                    state=TodoState(item_data["state"]),
                    parent=parent_list,
                )
                parent_list.items.append(item)
                if item_data.get("subtasks") and item_data["subtasks"].get("tasks"):
                    assert item.subtasks is not None
                    create_items(item_data["subtasks"]["tasks"], item.subtasks)

        if "tasks" in data:
            create_items(data["tasks"], todo_list)
        return todo_list

    def save(self) -> Path:
        """Save todo list to workspace."""
        file_path = workspace_to_host_path(TODO_LIST_FILE)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w") as f:
            f.write(json.dumps(self.to_dict(), indent=2))
        return file_path

    def to_dict(self) -> dict:
        return {"tasks": [item.to_dict() for item in self.items]}

    def to_markdown(self) -> str:
        result = "# Todo List\n\n"
        for item in self.items:
            result += item.to_markdown()
        return result

    def update_item_state(self, item_id: str, state: TodoState) -> bool:
        item = self.get_item_by_id(item_id)
        if item:
            item.state = state
            return True
        return False

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TodoList):
            return False
        if len(self.items) != len(other.items):
            return False
        for i, item in enumerate(self.items):
            if item != other.items[i]:
                return False
        return True

    def __getitem__(self, key: str | int) -> TodoItem | None:
        if isinstance(key, int):
            try:
                return self.items[key - 1]
            except IndexError:
                return None
        return self.get_item_by_id(key)

    def __repr__(self) -> str:
        return self.to_markdown()

    def __str__(self) -> str:
        return self.to_markdown()
