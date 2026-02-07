"""Tool permissions for controlling agent capabilities."""

from enum import Enum
from functools import wraps
from typing import Callable


class ToolPermission(str, Enum):
    """Permission levels for tools."""
    READ = "read"
    WRITE = "write"
    CONNECT = "connect"


class ToolPermissionError(Exception):
    """Raised when a tool is called without required permissions."""
    pass


def tool_permission(*permissions: ToolPermission) -> Callable:
    """Decorator to attach permission requirements to a tool function."""
    def decorator(func: Callable) -> Callable:
        func._permissions = set(permissions)
        return func
    return decorator


def get_permissions(func: Callable) -> set[ToolPermission]:
    """Get the permissions required by a tool. Defaults to READ if not specified."""
    return getattr(func, "_permissions", {ToolPermission.READ})


def filter_tools_by_permission(tools: list[Callable], granted: set[ToolPermission]) -> list[Callable]:
    """Filter tools to only those allowed by the granted permissions."""
    return [t for t in tools if get_permissions(t).issubset(granted)]


def enforce_tool_permission(func: Callable, granted: set[ToolPermission] | Callable[[], set[ToolPermission]]) -> Callable:
    """Wrap a tool with runtime permission checking.

    granted can be a static set or a callable that returns the current set,
    enabling dynamic resolution (e.g. revoking CONNECT mid-conversation).
    """
    required = get_permissions(func)

    @wraps(func)
    def wrapper(*args, **kwargs):
        effective = granted() if callable(granted) else granted
        if not required.issubset(effective):
            missing = required - effective
            raise ToolPermissionError(f"Tool '{func.__name__}' requires {missing}")
        return func(*args, **kwargs)

    wrapper._permissions = required
    return wrapper


def enforce_tools_permissions(tools: list[Callable], granted: set[ToolPermission] | Callable[[], set[ToolPermission]]) -> list[Callable]:
    """Wrap all tools with runtime permission checking."""
    return [enforce_tool_permission(t, granted) for t in tools]
