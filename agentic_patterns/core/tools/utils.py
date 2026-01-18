"""Utility functions for tool handling."""

import inspect
from typing import Callable, get_type_hints


def func_to_description(func: Callable) -> str:
    """Convert a function to a human-readable description including full signature."""
    sig = inspect.signature(func)

    # Try to get type hints, fall back to empty dict if not available
    try:
        hints = get_type_hints(func)
    except Exception:
        hints = {}

    # Build parameter descriptions
    params = []
    for name, param in sig.parameters.items():
        param_type = hints.get(name, param.annotation)
        type_str = _type_to_str(param_type) if param_type != inspect.Parameter.empty else "Any"

        if param.default != inspect.Parameter.empty:
            params.append(f"{name}: {type_str} = {repr(param.default)}")
        else:
            params.append(f"{name}: {type_str}")

    # Get return type
    return_type = hints.get("return", sig.return_annotation)
    return_str = _type_to_str(return_type) if return_type != inspect.Signature.empty else "None"

    # Build the description
    lines = [f"Tool: {func.__name__}({', '.join(params)}) -> {return_str}"]

    if func.__doc__:
        doc = func.__doc__.strip()
        lines.append(f"Description: {doc}")

    return "\n".join(lines)


def _type_to_str(type_hint) -> str:
    """Convert a type hint to a readable string."""
    if type_hint is None:
        return "None"
    if hasattr(type_hint, "__origin__"):
        # Handle generic types like list[int], dict[str, int], etc.
        origin = type_hint.__origin__
        args = getattr(type_hint, "__args__", ())
        if args:
            args_str = ", ".join(_type_to_str(arg) for arg in args)
            origin_name = getattr(origin, "__name__", str(origin))
            return f"{origin_name}[{args_str}]"
        return getattr(origin, "__name__", str(origin))
    if hasattr(type_hint, "__name__"):
        return type_hint.__name__
    return str(type_hint)
