"""
AG-UI event utilities.

Provides helpers for creating AG-UI events in tool returns.
"""

from typing import Any

from ag_ui.core import CustomEvent, EventType, StateSnapshotEvent
from pydantic import BaseModel
from pydantic_ai import ToolReturn


def state_snapshot(state: BaseModel) -> StateSnapshotEvent:
    """Create a state snapshot event for UI synchronization."""
    return StateSnapshotEvent(type=EventType.STATE_SNAPSHOT, snapshot=state)


def custom_event(name: str, value: Any) -> CustomEvent:
    """Create a custom event for application-specific signaling."""
    return CustomEvent(type=EventType.CUSTOM, name=name, value=value)


def tool_return_with_state(
    return_value: Any,
    state: BaseModel,
    custom_events: list[tuple[str, Any]] | None = None,
) -> ToolReturn:
    """
    Create a ToolReturn with state snapshot and optional custom events.

    Args:
        return_value: The value to return from the tool.
        state: Current state to snapshot.
        custom_events: List of (name, value) tuples for custom events.

    Returns:
        ToolReturn with state snapshot and custom events as metadata.
    """
    metadata = [state_snapshot(state)]
    if custom_events:
        metadata.extend(custom_event(name, value) for name, value in custom_events)
    return ToolReturn(return_value=return_value, metadata=metadata)
