"""
AG-UI application with state management and custom events.

This example demonstrates:
- Shared state between UI and agent via StateDeps
- State snapshot events for UI synchronization
- Custom events for application-specific signaling
- Tools that modify shared state

Run with: uvicorn agentic_patterns.examples.ui.example_agui_app_v3:app --reload
"""

from ag_ui.core import CustomEvent, EventType, StateSnapshotEvent
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware

from pydantic_ai import RunContext, ToolReturn
from pydantic_ai.ui import StateDeps
from pydantic_ai.ui.ag_ui.app import AGUIApp

from agentic_patterns.core.agents.agents import get_agent


class CalculatorState(BaseModel):
    """Shared state for the calculator application."""
    history: list[str] = []
    last_result: int | None = None

def update_state_with_result(ctx: RunContext[StateDeps[CalculatorState]], operation: str, a: int, b: int, result: int) -> ToolReturn:
    """Helper function to update state and emit events after a calculation."""
    state = ctx.deps.state
    state.history.append(f"{a} {operation} {b} = {result}")
    state.last_result = result
    return ToolReturn(
        return_value=f"Result: {result}",
        metadata=[
            StateSnapshotEvent(type=EventType.STATE_SNAPSHOT, snapshot=state),
            CustomEvent(type=EventType.CUSTOM, name='calculation_complete', value={'operation': operation, 'result': result}),
        ],
    )

async def add(ctx: RunContext[StateDeps[CalculatorState]], a: int, b: int) -> ToolReturn:
    """Add two numbers and update the state."""
    result = a + b
    return update_state_with_result(ctx, 'add', a, b, result)


async def sub(ctx: RunContext[StateDeps[CalculatorState]], a: int, b: int) -> ToolReturn:
    """Subtract two numbers and update the state."""
    result = a - b
    return update_state_with_result(ctx, 'sub', a, b, result)


async def mul(ctx: RunContext[StateDeps[CalculatorState]], a: int, b: int) -> ToolReturn:
    """Multiply two numbers and update the state."""
    result = a * b
    return update_state_with_result(ctx, 'mul', a, b, result)


async def div(ctx: RunContext[StateDeps[CalculatorState]], a: int, b: int) -> ToolReturn:
    """Divide two numbers and update the state."""
    if b == 0:
        return ToolReturn(
            return_value="Error: Division by zero is undefined.",
            metadata=[
                CustomEvent(type=EventType.CUSTOM, name='calculation_error', value={'operation': 'div', 'error': 'division_by_zero'}),
            ],
        )
    result = a // b  # Integer division
    return update_state_with_result(ctx, 'div', a, b, result)


async def show_history(ctx: RunContext[StateDeps[CalculatorState]]) -> str:
    """Show the calculation history."""
    state = ctx.deps.state
    if not state.history:
        return "No calculations performed yet."
    return "Calculation history:\n" + "\n".join(state.history)


async def clear_history(ctx: RunContext[StateDeps[CalculatorState]]) -> ToolReturn:
    """Clear the calculation history."""
    state = ctx.deps.state
    state.history = []
    state.last_result = None
    return ToolReturn(
        return_value="History cleared.",
        metadata=[
            StateSnapshotEvent(type=EventType.STATE_SNAPSHOT, snapshot=state),
            CustomEvent(type=EventType.CUSTOM, name='history_cleared', value=True),
        ],
    )


agent = get_agent(
    instructions=(
        'You are a calculator assistant. Use the provided tools to perform calculations. '
        'The calculation history is maintained in the shared state.'
    ),
    deps_type=StateDeps[CalculatorState],
    tools=[add, sub, mul, show_history, clear_history],
)

app = AGUIApp(agent, deps=StateDeps(CalculatorState()))
app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:5173'],
    allow_methods=['*'],
    allow_headers=['*'],
)
