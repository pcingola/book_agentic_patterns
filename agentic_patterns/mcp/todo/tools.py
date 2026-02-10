"""MCP Todo server tools -- thin wrapper delegating to toolkits/todo/."""

from fastmcp import Context, FastMCP

from agentic_patterns.core.mcp import ToolRetryError
from agentic_patterns.core.tools.permissions import ToolPermission, tool_permission
from agentic_patterns.toolkits.todo import operations as ops


def register_tools(mcp: FastMCP) -> None:
    """Register all todo tools on the given MCP server instance."""

    @mcp.tool()
    @tool_permission(ToolPermission.WRITE)
    async def add_task(
        description: str, parent_task_id: str | None = None, ctx: Context = None
    ) -> str:
        """Add a task. Returns the new task ID (e.g. '1.3.2').

        Args:
            description: Task description.
            parent_task_id: Optional parent ID to nest under (e.g. '1.3').
        """
        try:
            task_id = ops.add_task(description, parent_task_id)
        except (ValueError, KeyError) as e:
            raise ToolRetryError(str(e)) from e
        await ctx.info(f"add_task: id={task_id} desc='{description}'")
        return task_id

    @mcp.tool()
    @tool_permission(ToolPermission.WRITE)
    async def add_tasks(
        descriptions: list[str], parent_task_id: str | None = None, ctx: Context = None
    ) -> list[str]:
        """Add several tasks at once. Returns list of new task IDs.

        Args:
            descriptions: List of task descriptions.
            parent_task_id: Optional parent ID to nest all under.
        """
        try:
            task_ids = ops.add_tasks(descriptions, parent_task_id)
        except (ValueError, KeyError) as e:
            raise ToolRetryError(str(e)) from e
        await ctx.info(f"add_tasks: ids={task_ids}")
        return task_ids

    @mcp.tool()
    @tool_permission(ToolPermission.WRITE)
    async def create_task_list(
        descriptions: list[str], ctx: Context = None
    ) -> list[str]:
        """Create a new task list replacing any existing one. Returns list of task IDs.

        Args:
            descriptions: List of task descriptions for the new list.
        """
        task_ids = ops.create_task_list(descriptions)
        await ctx.info(f"create_task_list: ids={task_ids}")
        return task_ids

    @mcp.tool()
    @tool_permission(ToolPermission.WRITE)
    async def delete_task(task_id: str, ctx: Context = None) -> bool:
        """Delete a task by ID (e.g. '1.3.2'). Returns True if deleted."""
        success = ops.delete_task(task_id)
        await ctx.info(f"delete_task: id={task_id} success={success}")
        return success

    @mcp.tool()
    @tool_permission(ToolPermission.READ)
    async def show_task_list(ctx: Context = None) -> str:
        """Show all tasks as a markdown checklist."""
        md = ops.show_task_list()
        await ctx.info("show_task_list")
        return md

    @mcp.tool()
    @tool_permission(ToolPermission.WRITE)
    async def update_task_status(
        task_id: str, status: str, ctx: Context = None
    ) -> bool:
        """Update a task's status by ID.

        Args:
            task_id: Task ID (e.g. '3.2').
            status: New status: 'pending', 'in_progress', 'completed', or 'failed'.
        """
        try:
            success = ops.update_task_status(task_id, status)
        except ValueError as e:
            raise ToolRetryError(str(e)) from e
        await ctx.info(
            f"update_task_status: id={task_id} status={status} success={success}"
        )
        return success
