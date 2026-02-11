"""Tool permissions for controlling agent capabilities."""

import asyncio
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


def _check_private_data(func_name: str) -> None:
    from agentic_patterns.core.compliance.private_data import session_has_private_data

    if session_has_private_data():
        raise ToolPermissionError(f"Tool '{func_name}' blocked: session contains private data")


def tool_permission(*permissions: ToolPermission) -> Callable:
    """Decorator to attach permission requirements to a tool function.

    CONNECT tools are automatically blocked when the session contains private data.
    """

    def decorator(func: Callable) -> Callable:
        func._permissions = set(permissions)
        if ToolPermission.CONNECT not in permissions:
            return func

        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                _check_private_data(func.__name__)
                return await func(*args, **kwargs)
        else:
            @wraps(func)
            def wrapper(*args, **kwargs):
                _check_private_data(func.__name__)
                return func(*args, **kwargs)

        wrapper._permissions = func._permissions
        return wrapper

    return decorator


def get_permissions(func: Callable) -> set[ToolPermission]:
    """Get the permissions required by a tool. Defaults to READ if not specified."""
    return getattr(func, "_permissions", {ToolPermission.READ})


def filter_tools_by_permission(
    tools: list[Callable], granted: set[ToolPermission]
) -> list[Callable]:
    """Filter tools to only those allowed by the granted permissions."""
    return [t for t in tools if get_permissions(t).issubset(granted)]


def enforce_tool_permission(func: Callable, granted: set[ToolPermission]) -> Callable:
    """Wrap a tool with runtime permission checking. Permissions are baked into the wrapper."""
    required = get_permissions(func)

    @wraps(func)
    def wrapper(*args, **kwargs):
        if not required.issubset(granted):
            missing = required - granted
            raise ToolPermissionError(f"Tool '{func.__name__}' requires {missing}")
        return func(*args, **kwargs)

    wrapper._permissions = required
    return wrapper


def enforce_tools_permissions(
    tools: list[Callable], granted: set[ToolPermission]
) -> list[Callable]:
    """Wrap all tools with runtime permission checking."""
    return [enforce_tool_permission(t, granted) for t in tools]
