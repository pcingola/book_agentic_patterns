"""MCP Todo server tools -- thin wrapper delegating to toolkits/todo/."""

from fastmcp import Context, FastMCP

from agentic_patterns.core.mcp import ToolRetryError
from agentic_patterns.core.tools.permissions import ToolPermission, tool_permission
from agentic_patterns.toolkits.todo import operations as ops


def register_tools(mcp: FastMCP) -> None:
    """Register all todo tools on the given MCP server instance."""

    @mcp.tool()
    @tool_permission(ToolPermission.WRITE)
    async def todo_add(
        description: str, parent_item_id: str | None = None, ctx: Context = None
    ) -> str:
        """Add a todo item. Returns the new item ID (e.g. '1.3.2').

        Args:
            description: Item description.
            parent_item_id: Optional parent ID to nest under (e.g. '1.3').
        """
        try:
            item_id = ops.todo_add(description, parent_item_id)
        except (ValueError, KeyError) as e:
            raise ToolRetryError(str(e)) from e
        await ctx.info(f"todo_add: id={item_id} desc='{description}'")
        return item_id

    @mcp.tool()
    @tool_permission(ToolPermission.WRITE)
    async def todo_add_many(
        descriptions: list[str], parent_item_id: str | None = None, ctx: Context = None
    ) -> list[str]:
        """Add several todo items at once. Returns list of new item IDs.

        Args:
            descriptions: List of item descriptions.
            parent_item_id: Optional parent ID to nest all under.
        """
        try:
            item_ids = ops.todo_add_many(descriptions, parent_item_id)
        except (ValueError, KeyError) as e:
            raise ToolRetryError(str(e)) from e
        await ctx.info(f"todo_add_many: ids={item_ids}")
        return item_ids

    @mcp.tool()
    @tool_permission(ToolPermission.WRITE)
    async def todo_create_list(
        descriptions: list[str], ctx: Context = None
    ) -> list[str]:
        """Create a new todo list replacing any existing one. Returns list of item IDs.

        Args:
            descriptions: List of item descriptions for the new list.
        """
        item_ids = ops.todo_create_list(descriptions)
        await ctx.info(f"todo_create_list: ids={item_ids}")
        return item_ids

    @mcp.tool()
    @tool_permission(ToolPermission.WRITE)
    async def todo_delete(item_id: str, ctx: Context = None) -> bool:
        """Delete a todo item by ID (e.g. '1.3.2'). Returns True if deleted."""
        success = ops.todo_delete(item_id)
        await ctx.info(f"todo_delete: id={item_id} success={success}")
        return success

    @mcp.tool()
    @tool_permission(ToolPermission.READ)
    async def todo_show(ctx: Context = None) -> str:
        """Show all todo items as a markdown checklist."""
        md = ops.todo_show()
        await ctx.info("todo_show")
        return md

    @mcp.tool()
    @tool_permission(ToolPermission.WRITE)
    async def todo_update_status(
        item_id: str, status: str, ctx: Context = None
    ) -> bool:
        """Update a todo item's status by ID.

        Args:
            item_id: Item ID (e.g. '3.2').
            status: New status: 'pending', 'in_progress', 'completed', or 'failed'.
        """
        try:
            success = ops.todo_update_status(item_id, status)
        except ValueError as e:
            raise ToolRetryError(str(e)) from e
        await ctx.info(
            f"todo_update_status: id={item_id} status={status} success={success}"
        )
        return success
