"""Mock tool implementation for testing agent interactions."""

import functools
import inspect
from typing import Any, Awaitable, Callable, TypeVar

T = TypeVar("T")


class ToolMockWrapper:
    """Wrapper that tracks call statistics for mocked tool functions."""

    def __init__(self, func: Callable, return_values: list[Any], is_async: bool):
        self._func = func
        self._original_return_values = return_values.copy()
        self._return_values = return_values.copy()
        self._is_async = is_async
        self._call_count = 0
        self._call_args_list: list[tuple[tuple, dict]] = []
        functools.update_wrapper(self, func)

    @property
    def call_count(self) -> int:
        return self._call_count

    @property
    def was_called(self) -> bool:
        return self._call_count > 0

    @property
    def call_args_list(self) -> list[tuple[tuple, dict]]:
        return self._call_args_list.copy()

    def reset(self) -> None:
        """Reset call count, call history, and restore original return values."""
        self._call_count = 0
        self._call_args_list = []
        self._return_values = self._original_return_values.copy()

    def _record_call(self, args: tuple, kwargs: dict) -> Any:
        self._call_count += 1
        self._call_args_list.append((args, kwargs))
        if not self._return_values:
            raise IndexError(
                f"No more mock return values available for {self._func.__name__}. "
                f"Called more times than provided return values."
            )
        return self._return_values.pop(0)

    def __call__(self, *args, **kwargs) -> Any:
        return self._record_call(args, kwargs)


class ToolMockWrapperAsync(ToolMockWrapper):
    """Async version of ToolMockWrapper."""

    async def __call__(self, *args, **kwargs) -> Any:
        return self._record_call(args, kwargs)


def tool_mock(func: Callable[..., T | Awaitable[T]], return_values: list[Any]) -> ToolMockWrapper:
    """
    Creates a mock version of the provided function that returns values from a predefined list.
    Supports both synchronous and asynchronous functions.

    The returned mock tracks call statistics:
        - call_count: Number of times the mock was called
        - was_called: Whether the mock was called at least once
        - call_args_list: List of (args, kwargs) tuples for all calls made
        - reset(): Resets call count, history, and restores return values

    Args:
        func: The original function to mock (can be sync or async)
        return_values: A list of values to be returned sequentially on each call

    Returns:
        A ToolMockWrapper with the same signature and docstring as the original,
        but returns values from the provided list sequentially.

    Raises:
        IndexError: When called more times than there are return values
    """
    is_async = inspect.iscoroutinefunction(func)
    if is_async:
        return ToolMockWrapperAsync(func, return_values, is_async)
    return ToolMockWrapper(func, return_values, is_async)
