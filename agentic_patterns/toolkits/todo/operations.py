"""Business logic for task management. No framework dependency."""

from agentic_patterns.core.user_session import get_session_id, get_user_id
from agentic_patterns.toolkits.todo.models import TaskList, TaskState

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
            raise ValueError(f"Parent task with ID '{parent_task_id}' not found")
        task = parent_task.add_task(description)
        return f"{parent_task_id}.{task.get_id()}"
    task = task_list.add_task(description)
    return task.get_id()


def add_task(description: str, parent_task_id: str | None = None) -> str:
    """Add a task. Returns the new task ID (e.g. '1.3.2')."""
    task_list = _get_task_list()
    task_id = _add_one(description, parent_task_id, task_list)
    _save(task_list)
    return task_id


def add_tasks(descriptions: list[str], parent_task_id: str | None = None) -> list[str]:
    """Add several tasks at once. Returns list of new task IDs."""
    task_list = _get_task_list()
    task_ids = [_add_one(d, parent_task_id, task_list) for d in descriptions]
    _save(task_list)
    return task_ids


def create_task_list(descriptions: list[str]) -> list[str]:
    """Create a new task list replacing any existing one. Returns list of task IDs."""
    task_list = _new_task_list()
    task_ids = []
    for desc in descriptions:
        task = task_list.add_task(desc)
        task_ids.append(task.get_id())
    _save(task_list)
    return task_ids


def delete_task(task_id: str) -> bool:
    """Delete a task by ID (e.g. '1.3.2'). Returns True if deleted."""
    task_list = _get_task_list()
    success = task_list.delete(task_id)
    if success:
        _save(task_list)
    return success


def show_task_list() -> str:
    """Show all tasks as a markdown checklist."""
    task_list = _get_task_list()
    return task_list.to_markdown()


def update_task_status(task_id: str, status: str) -> bool:
    """Update a task's status by ID."""
    try:
        task_state = TaskState(status)
    except ValueError:
        raise ValueError(f"Invalid status '{status}'. Use: pending, in_progress, completed, failed")
    task_list = _get_task_list()
    success = task_list.update_task_state(task_id, task_state)
    if success:
        _save(task_list)
    return success
