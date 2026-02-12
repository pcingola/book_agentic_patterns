"""Business logic for todo management. No framework dependency."""

from agentic_patterns.core.user_session import get_session_id, get_user_id
from agentic_patterns.toolkits.todo.models import TodoList, TodoState

# In-memory cache keyed by (user_id, session_id)
_cache: dict[tuple[str, str], TodoList] = {}


def _cache_key() -> tuple[str, str]:
    return (get_user_id(), get_session_id())


def _get_todo_list() -> TodoList:
    key = _cache_key()
    if key not in _cache:
        _cache[key] = TodoList.load()
    return _cache[key]


def _new_todo_list() -> TodoList:
    key = _cache_key()
    todo_list = TodoList()
    todo_list.save()
    _cache[key] = todo_list
    return todo_list


def _save(todo_list: TodoList) -> None:
    todo_list.save()
    _cache[_cache_key()] = todo_list


def _add_one(description: str, parent_item_id: str | None, todo_list: TodoList) -> str:
    if parent_item_id:
        parent_item = todo_list.get_item_by_id(parent_item_id)
        if not parent_item:
            raise ValueError(f"Parent item with ID '{parent_item_id}' not found")
        item = parent_item.add_item(description)
        return f"{parent_item_id}.{item.get_id()}"
    item = todo_list.add_item(description)
    return item.get_id()


def todo_add(description: str, parent_item_id: str | None = None) -> str:
    """Add a todo item. Returns the new item ID (e.g. '1.3.2')."""
    todo_list = _get_todo_list()
    item_id = _add_one(description, parent_item_id, todo_list)
    _save(todo_list)
    return item_id


def todo_add_many(descriptions: list[str], parent_item_id: str | None = None) -> list[str]:
    """Add several todo items at once. Returns list of new item IDs."""
    todo_list = _get_todo_list()
    item_ids = [_add_one(d, parent_item_id, todo_list) for d in descriptions]
    _save(todo_list)
    return item_ids


def todo_create_list(descriptions: list[str]) -> list[str]:
    """Create a new todo list replacing any existing one. Returns list of item IDs."""
    todo_list = _new_todo_list()
    item_ids = []
    for desc in descriptions:
        item = todo_list.add_item(desc)
        item_ids.append(item.get_id())
    _save(todo_list)
    return item_ids


def todo_delete(item_id: str) -> bool:
    """Delete a todo item by ID (e.g. '1.3.2'). Returns True if deleted."""
    todo_list = _get_todo_list()
    success = todo_list.delete(item_id)
    if success:
        _save(todo_list)
    return success


def todo_show() -> str:
    """Show all todo items as a markdown checklist."""
    todo_list = _get_todo_list()
    return todo_list.to_markdown()


def todo_update_status(item_id: str, status: str) -> bool:
    """Update a todo item's status by ID."""
    try:
        todo_state = TodoState(status)
    except ValueError:
        raise ValueError(
            f"Invalid status '{status}'. Use: pending, in_progress, completed, failed"
        )
    todo_list = _get_todo_list()
    success = todo_list.update_item_state(item_id, todo_state)
    if success:
        _save(todo_list)
    return success
