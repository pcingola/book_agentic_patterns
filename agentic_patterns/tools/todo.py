"""PydanticAI agent tools for todo management -- wraps toolkits/todo/."""

from agentic_patterns.core.tools.permissions import ToolPermission, tool_permission
from agentic_patterns.toolkits.todo import operations as ops


def get_all_tools() -> list:
    """Get all todo tools for use with PydanticAI agents."""

    @tool_permission(ToolPermission.WRITE)
    async def todo_add(description: str, parent_item_id: str | None = None) -> str:
        """Add a todo item. Returns the new item ID (e.g. '1.3.2')."""
        return ops.todo_add(description, parent_item_id)

    @tool_permission(ToolPermission.WRITE)
    async def todo_add_many(
        descriptions: list[str], parent_item_id: str | None = None
    ) -> list[str]:
        """Add several todo items at once. Returns list of new item IDs."""
        return ops.todo_add_many(descriptions, parent_item_id)

    @tool_permission(ToolPermission.WRITE)
    async def todo_create_list(descriptions: list[str]) -> list[str]:
        """Create a new todo list replacing any existing one. Returns list of item IDs."""
        return ops.todo_create_list(descriptions)

    @tool_permission(ToolPermission.WRITE)
    async def todo_delete(item_id: str) -> bool:
        """Delete a todo item by ID (e.g. '1.3.2'). Returns True if deleted."""
        return ops.todo_delete(item_id)

    @tool_permission(ToolPermission.READ)
    async def todo_show() -> str:
        """Show all todo items as a markdown checklist."""
        return ops.todo_show()

    @tool_permission(ToolPermission.WRITE)
    async def todo_update_status(item_id: str, status: str) -> bool:
        """Update a todo item's status by ID. status: pending, in_progress, completed, or failed."""
        return ops.todo_update_status(item_id, status)

    return [
        todo_add,
        todo_add_many,
        todo_create_list,
        todo_delete,
        todo_show,
        todo_update_status,
    ]
