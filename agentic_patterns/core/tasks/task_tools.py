"""PydanticAI tool functions for task management."""

from collections.abc import Callable

from pydantic_ai import RunContext

from agentic_patterns.core.tasks.task_list import TaskList
from agentic_patterns.core.tasks.task_status import TaskStatus


def get_task_tools(task_list: TaskList) -> list[Callable]:
    """Return the four task management tools bound to the given TaskList."""

    async def task_create(
        ctx: RunContext,
        subject: str,
        description: str,
        *,
        active_form: str | None = None,
        metadata: dict | None = None,
    ) -> str:
        """Create a new task. Returns confirmation with the task ID."""
        task = await task_list.create(
            subject, description, active_form=active_form, metadata=metadata
        )
        return f"Task #{task.id} created: {task.subject}"

    async def task_get(ctx: RunContext, task_id: str) -> str:
        """Retrieve full task details by ID."""
        task = await task_list.get(task_id)
        if task is None:
            return f"Task #{task_id} not found."
        lines = [
            f"#{task.id} [{task.status.value}] {task.subject}",
            f"Description: {task.description}",
        ]
        if task.owner:
            lines.append(f"Owner: {task.owner}")
        if task.active_form:
            lines.append(f"Active form: {task.active_form}")
        if task.blocks:
            lines.append(f"Blocks: {', '.join(task.blocks)}")
        if task.blocked_by:
            lines.append(f"Blocked by: {', '.join(task.blocked_by)}")
        return "\n".join(lines)

    async def task_list_all(ctx: RunContext) -> str:
        """List all tasks with summary info."""
        tasks = await task_list.list_all()
        if not tasks:
            return "No tasks."
        lines = []
        for t in tasks:
            line = f"#{t.id} [{t.status.value}] {t.subject}"
            if t.owner:
                line += f" (owner: {t.owner})"
            if t.blocked_by:
                line += f" [blocked by: {', '.join(t.blocked_by)}]"
            lines.append(line)
        return "\n".join(lines)

    async def task_update(
        ctx: RunContext,
        task_id: str,
        *,
        status: str | None = None,
        subject: str | None = None,
        description: str | None = None,
        active_form: str | None = None,
        owner: str | None = None,
        metadata: dict | None = None,
        add_blocks: list[str] | None = None,
        add_blocked_by: list[str] | None = None,
    ) -> str:
        """Update a task. All fields except task_id are optional."""
        parsed_status = TaskStatus(status) if status else None
        try:
            task = await task_list.update(
                task_id,
                status=parsed_status,
                subject=subject,
                description=description,
                active_form=active_form,
                owner=owner,
                metadata=metadata,
                add_blocks=add_blocks,
                add_blocked_by=add_blocked_by,
            )
        except ValueError as e:
            return str(e)
        if task is None:
            return f"Task #{task_id} not found."
        if task.status == TaskStatus.DELETED:
            return f"Task #{task_id} deleted."
        parts = [f"Updated task #{task_id}"]
        if status:
            parts.append(f"status={status}")
        if subject:
            parts.append(f"subject={subject}")
        if owner:
            parts.append(f"owner={owner}")
        if add_blocks:
            parts.append(f"blocks+={add_blocks}")
        if add_blocked_by:
            parts.append(f"blockedBy+={add_blocked_by}")
        return " ".join(parts)

    return [task_create, task_get, task_list_all, task_update]
