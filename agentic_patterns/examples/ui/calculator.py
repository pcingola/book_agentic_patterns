"""Shared calculator components for AG-UI examples (v3-v5)."""

from ag_ui.core import CustomEvent, EventType, StateSnapshotEvent
from pydantic import BaseModel

from pydantic_ai import RunContext, ToolReturn
from pydantic_ai.ui import StateDeps


class CalculatorState(BaseModel):
    """Shared state for the calculator application."""

    history: list[str] = []
    last_result: int | None = None


def update_state_with_result(
    ctx: RunContext[StateDeps[CalculatorState]],
    operation: str,
    a: int,
    b: int,
    result: int,
) -> ToolReturn:
    """Update state and emit events after a calculation."""
    state = ctx.deps.state
    state.history.append(f"{a} {operation} {b} = {result}")
    state.last_result = result
    return ToolReturn(
        return_value=f"Result: {result}",
        metadata=[
            StateSnapshotEvent(type=EventType.STATE_SNAPSHOT, snapshot=state),
            CustomEvent(
                type=EventType.CUSTOM,
                name="calculation_complete",
                value={"operation": operation, "result": result},
            ),
        ],
    )


async def add(
    ctx: RunContext[StateDeps[CalculatorState]], a: int, b: int
) -> ToolReturn:
    """Add two numbers and update the state."""
    return update_state_with_result(ctx, "add", a, b, a + b)


async def mul(
    ctx: RunContext[StateDeps[CalculatorState]], a: int, b: int
) -> ToolReturn:
    """Multiply two numbers and update the state."""
    return update_state_with_result(ctx, "mul", a, b, a * b)


async def show_history(ctx: RunContext[StateDeps[CalculatorState]]) -> str:
    """Show the calculation history."""
    state = ctx.deps.state
    if not state.history:
        return "No calculations performed yet."
    return "Calculation history:\n" + "\n".join(state.history)


async def sub(
    ctx: RunContext[StateDeps[CalculatorState]], a: int, b: int
) -> ToolReturn:
    """Subtract two numbers and update the state."""
    return update_state_with_result(ctx, "sub", a, b, a - b)
