"""PydanticAI agent tools for task management -- wraps toolkits/todo/."""

from agentic_patterns.core.tools.permissions import ToolPermission, tool_permission
from agentic_patterns.toolkits.todo import operations as ops


def get_all_tools() -> list:
    """Get all todo tools for use with PydanticAI agents."""

    @tool_permission(ToolPermission.WRITE)
    async def add_task(description: str, parent_task_id: str | None = None) -> str:
        """Add a task. Returns the new task ID (e.g. '1.3.2')."""
        return ops.add_task(description, parent_task_id)

    @tool_permission(ToolPermission.WRITE)
    async def add_tasks(
        descriptions: list[str], parent_task_id: str | None = None
    ) -> list[str]:
        """Add several tasks at once. Returns list of new task IDs."""
        return ops.add_tasks(descriptions, parent_task_id)

    @tool_permission(ToolPermission.WRITE)
    async def create_task_list(descriptions: list[str]) -> list[str]:
        """Create a new task list replacing any existing one. Returns list of task IDs."""
        return ops.create_task_list(descriptions)

    @tool_permission(ToolPermission.WRITE)
    async def delete_task(task_id: str) -> bool:
        """Delete a task by ID (e.g. '1.3.2'). Returns True if deleted."""
        return ops.delete_task(task_id)

    @tool_permission(ToolPermission.READ)
    async def show_task_list() -> str:
        """Show all tasks as a markdown checklist."""
        return ops.show_task_list()

    @tool_permission(ToolPermission.WRITE)
    async def update_task_status(task_id: str, status: str) -> bool:
        """Update a task's status by ID. status: pending, in_progress, completed, or failed."""
        return ops.update_task_status(task_id, status)

    return [
        add_task,
        add_tasks,
        create_task_list,
        delete_task,
        show_task_list,
        update_task_status,
    ]
