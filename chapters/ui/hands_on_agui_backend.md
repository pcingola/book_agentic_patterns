## Hands-On: AG-UI Backend

This walkthrough covers the three backend examples that expose a PydanticAI agent via the AG-UI protocol, progressing from a minimal application to tools to state management.

### v1 -- Minimal Application

The first example shows the minimal AG-UI structure:

```python
from starlette.middleware.cors import CORSMiddleware

from pydantic_ai.ui.ag_ui.app import AGUIApp

from agentic_patterns.core.agents.agents import get_agent


agent = get_agent(
    instructions='You are a helpful assistant. Keep responses concise.',
)

app = AGUIApp(agent)
app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:5173'],
    allow_methods=['*'],
    allow_headers=['*'],
)
```

`get_agent()` creates a PydanticAI agent using the model configuration from `config.yaml` (defaulting to the `default` entry). `AGUIApp` wraps the agent and exposes it via the AG-UI protocol, handling HTTP requests, parsing the AG-UI run input, executing the agent, and streaming events back to the client.

The CORS middleware is required because the React frontend runs on a different origin (`localhost:5173` via Vite) than the backend (`localhost:8000`). Without it, the browser blocks cross-origin requests.

### v2 -- Adding Tools

The second example adds calculator tools:

```python
from starlette.middleware.cors import CORSMiddleware

from pydantic_ai.ui.ag_ui.app import AGUIApp

from agentic_patterns.core.agents.agents import get_agent


async def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


async def sub(a: int, b: int) -> int:
    """Subtract two numbers."""
    return a - b


async def mul(a: int, b: int) -> int:
    """Multiply two numbers."""
    return a * b


agent = get_agent(
    instructions='You are a calculator assistant. Use the provided tools to perform calculations.',
    tools=[add, sub, mul],
)

app = AGUIApp(agent)
app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:5173'],
    allow_methods=['*'],
    allow_headers=['*'],
)
```

Tools are standalone async functions passed to `get_agent()` via the `tools` parameter. There is no decorator -- PydanticAI inspects the function signature and docstring to generate the tool schema for the LLM. When the agent calls a tool, AG-UI emits tool call events in the SSE stream so the frontend can show what the agent is doing.

### v3 -- State Management

The third example introduces shared state between the UI and the agent. The full file has five tools; here we show the key pieces.

The state model:

```python
class CalculatorState(BaseModel):
    """Shared state for the calculator application."""
    history: list[str] = []
    last_result: int | None = None
```

`StateDeps` wraps this model so the agent and UI share a typed state object. Tools receive the state through `RunContext` and can modify it:

```python
async def add(ctx: RunContext[StateDeps[CalculatorState]], a: int, b: int) -> ToolReturn:
    """Add two numbers and update the state."""
    result = a + b
    state = ctx.deps.state
    state.history.append(f"{a} + {b} = {result}")
    state.last_result = result
    return ToolReturn(
        return_value=f"Result: {result}",
        metadata=[
            StateSnapshotEvent(type=EventType.STATE_SNAPSHOT, snapshot=state),
            CustomEvent(type=EventType.CUSTOM, name='calculation_complete', value={'operation': 'add', 'result': result}),
        ],
    )
```

The `ToolReturn` carries both the return value (what the LLM sees) and metadata events (what the frontend sees). `StateSnapshotEvent` tells the frontend to update its local state with the new snapshot. `CustomEvent` signals a domain-specific action the frontend can interpret however it wants.

The `sub` and `mul` tools follow the same pattern. Two additional tools handle history:

```python
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
```

`show_history` returns a plain string -- it reads state but doesn't modify it, so no snapshot is needed. `clear_history` resets the state and emits a snapshot so the frontend updates.

The agent and app are assembled with all five tools and the initial state:

```python
agent = get_agent(
    instructions=(
        'You are a calculator assistant. Use the provided tools to perform calculations. '
        'The calculation history is maintained in the shared state.'
    ),
    deps_type=StateDeps[CalculatorState],
    tools=[add, sub, mul, show_history, clear_history],
)

app = AGUIApp(agent, deps=StateDeps(CalculatorState()))
```

### Core Library Helpers

The core library in `agentic_patterns/core/ui/agui/` provides two shortcuts. `create_agui_app()` combines agent creation and AG-UI wrapping into one call, using the same `config.yaml` model configurations. `tool_return_with_state()` reduces the boilerplate of constructing `ToolReturn` with state snapshots and custom events:

```python
from agentic_patterns.core.ui.agui.events import tool_return_with_state

return tool_return_with_state(
    return_value=f"Result: {result}",
    state=ctx.deps.state,
    custom_events=[('calculation_complete', {'result': result})],
)
```

### Key Takeaways

AG-UI is a protocol, not a framework. The backend exposes an agent via HTTP with SSE streaming; any compatible frontend connects without the backend knowing or caring which one.

State management uses `StateDeps` to share a typed Pydantic model between frontend and agent. Tools modify state and emit `StateSnapshotEvent` to push updates.

Custom events via `CustomEvent` let the agent signal domain-specific actions. The frontend interprets them according to its needs.

The SSE event stream contains lifecycle events (run started/finished), text deltas for streaming, tool call events, state snapshots, and custom events. This gives frontends full visibility into agent execution.
