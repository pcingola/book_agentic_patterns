"""MCP Todo server tools."""

from fastmcp import Context, FastMCP

from agentic_patterns.core.mcp import ToolRetryError
from agentic_patterns.core.tools.permissions import ToolPermission, tool_permission
from agentic_patterns.core.user_session import get_session_id, get_user_id
from agentic_patterns.mcp.todo.models import TaskList, TaskState

# In-memory cache keyed by (user_id, session_id)
_cache: dict[tuple[str, str], TaskList] = {}


def _cache_key() -> tuple[str, str]:
    return (get_user_id(), get_session_id())


def _get_task_list() -> TaskList:
    key = _cache_key()
    if key not in _cache:
        _cache[key] = TaskList.load()
    return _cache[key]


def _new_task_list() -> TaskList:
    key = _cache_key()
    task_list = TaskList()
    task_list.save()
    _cache[key] = task_list
    return task_list


def _save(task_list: TaskList) -> None:
    task_list.save()
    _cache[_cache_key()] = task_list


def _add_one(description: str, parent_task_id: str | None, task_list: TaskList) -> str:
    if parent_task_id:
        parent_task = task_list.get_task_by_id(parent_task_id)
        if not parent_task:
            raise ToolRetryError(f"Parent task with ID '{parent_task_id}' not found")
        task = parent_task.add_task(description)
        return f"{parent_task_id}.{task.get_id()}"
    task = task_list.add_task(description)
    return task.get_id()


def register_tools(mcp: FastMCP) -> None:
    """Register all todo tools on the given MCP server instance."""

    @mcp.tool()
    @tool_permission(ToolPermission.WRITE)
    async def add_task(description: str, parent_task_id: str | None = None, ctx: Context = None) -> str:
        """Add a task. Returns the new task ID (e.g. '1.3.2').

        Args:
            description: Task description.
            parent_task_id: Optional parent ID to nest under (e.g. '1.3').
        """
        task_list = _get_task_list()
        task_id = _add_one(description, parent_task_id, task_list)
        _save(task_list)
        await ctx.info(f"add_task: id={task_id} desc='{description}'")
        return task_id

    @mcp.tool()
    @tool_permission(ToolPermission.WRITE)
    async def add_tasks(descriptions: list[str], parent_task_id: str | None = None, ctx: Context = None) -> list[str]:
        """Add several tasks at once. Returns list of new task IDs.

        Args:
            descriptions: List of task descriptions.
            parent_task_id: Optional parent ID to nest all under.
        """
        task_list = _get_task_list()
        task_ids = [_add_one(d, parent_task_id, task_list) for d in descriptions]
        _save(task_list)
        await ctx.info(f"add_tasks: ids={task_ids}")
        return task_ids

    @mcp.tool()
    @tool_permission(ToolPermission.WRITE)
    async def create_task_list(descriptions: list[str], ctx: Context = None) -> list[str]:
        """Create a new task list replacing any existing one. Returns list of task IDs.

        Args:
            descriptions: List of task descriptions for the new list.
        """
        task_list = _new_task_list()
        task_ids = []
        for desc in descriptions:
            task = task_list.add_task(desc)
            task_ids.append(task.get_id())
        _save(task_list)
        await ctx.info(f"create_task_list: ids={task_ids}")
        return task_ids

    @mcp.tool()
    @tool_permission(ToolPermission.WRITE)
    async def delete_task(task_id: str, ctx: Context = None) -> bool:
        """Delete a task by ID (e.g. '1.3.2'). Returns True if deleted."""
        task_list = _get_task_list()
        success = task_list.delete(task_id)
        if success:
            _save(task_list)
        await ctx.info(f"delete_task: id={task_id} success={success}")
        return success

    @mcp.tool()
    @tool_permission(ToolPermission.READ)
    async def show_task_list(ctx: Context = None) -> str:
        """Show all tasks as a markdown checklist."""
        task_list = _get_task_list()
        md = task_list.to_markdown()
        await ctx.info("show_task_list")
        return md

    @mcp.tool()
    @tool_permission(ToolPermission.WRITE)
    async def update_task_status(task_id: str, status: str, ctx: Context = None) -> bool:
        """Update a task's status by ID.

        Args:
            task_id: Task ID (e.g. '3.2').
            status: New status: 'pending', 'in_progress', 'completed', or 'failed'.
        """
        try:
            task_state = TaskState(status)
        except ValueError:
            raise ToolRetryError(f"Invalid status '{status}'. Use: pending, in_progress, completed, failed")
        task_list = _get_task_list()
        success = task_list.update_task_state(task_id, task_state)
        if success:
            _save(task_list)
        await ctx.info(f"update_task_status: id={task_id} status={status} success={success}")
        return success
