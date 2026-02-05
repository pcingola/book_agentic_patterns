## Hands-On: AG-UI

This hands-on demonstrates how to expose a PydanticAI agent via the AG-UI protocol. The examples progress from a minimal application to one with tools and state management. The code is in `example_agui_app_v1.py`, `example_agui_app_v2.py`, and `example_agui_app_v3.py`.

## Running AG-UI Applications

AG-UI applications are ASGI apps run with uvicorn:

```bash
uvicorn example_agui_app_v1:app --reload
```

This starts an HTTP server that speaks the AG-UI protocol. Unlike Chainlit, AG-UI does not provide a UI; it provides the protocol that any compatible UI client can connect to. For testing, you can use curl or a tool like the AG-UI playground.

## Minimal Application

The first example (`example_agui_app_v1.py`) shows the minimal AG-UI structure:

```python
from pydantic_ai import Agent
from pydantic_ai.ui.ag_ui.app import AGUIApp

agent = Agent(
    'openai:gpt-4o-mini',
    instructions='You are a helpful assistant. Keep responses concise.',
)

app = AGUIApp(agent)
```

`AGUIApp` wraps a PydanticAI agent and exposes it via the AG-UI protocol. The app handles HTTP requests, parses the AG-UI run input, executes the agent, and streams events back to the client.

This pattern separates the agent logic from the UI entirely. Any AG-UI compatible frontend can connect to this backend: a chat interface, a document editor with inline suggestions, or a workflow dashboard. The protocol handles the communication contract.

## Adding Tools

The second example (`example_agui_app_v2.py`) adds tools to the agent:

```python
from pydantic_ai import Agent
from pydantic_ai.ui.ag_ui.app import AGUIApp

agent = Agent(
    'openai:gpt-4o-mini',
    instructions='You are a calculator assistant. Use the provided tools.',
)

@agent.tool_plain
async def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

@agent.tool_plain
async def sub(a: int, b: int) -> int:
    """Subtract two numbers."""
    return a - b

app = AGUIApp(agent)
```

Tools are defined using the `@agent.tool_plain` decorator for tools that don't need context, or `@agent.tool` for tools that need access to the run context and dependencies. When the agent calls a tool, AG-UI emits tool call events that the UI can render to show users what the agent is doing.

## State Management

The third example (`example_agui_app_v3.py`) introduces shared state between the UI and agent:

```python
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext, ToolReturn
from pydantic_ai.ui import StateDeps
from pydantic_ai.ui.ag_ui.app import AGUIApp

class CalculatorState(BaseModel):
    history: list[str] = []
    last_result: int | None = None

agent = Agent(
    'openai:gpt-4o-mini',
    instructions='You are a calculator assistant.',
    deps_type=StateDeps[CalculatorState],
)

app = AGUIApp(agent, deps=StateDeps(CalculatorState()))
```

`StateDeps` wraps a Pydantic model that represents the shared state. The UI can send state with each request, and the agent can modify it and send updates back via state snapshot events.

### State Snapshot Events

Tools can emit state snapshots to synchronize UI state:

```python
from ag_ui.core import EventType, StateSnapshotEvent

@agent.tool
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
        ],
    )
```

The `ToolReturn` class allows tools to return both a value and metadata events. The `StateSnapshotEvent` tells the UI client to update its local state with the new snapshot. This enables real-time synchronization between agent and UI.

### Custom Events

Tools can also emit custom events for application-specific signaling:

```python
from ag_ui.core import CustomEvent, EventType

@agent.tool
async def add(ctx: RunContext[StateDeps[CalculatorState]], a: int, b: int) -> ToolReturn:
    result = a + b
    # ... state updates ...
    return ToolReturn(
        return_value=f"Result: {result}",
        metadata=[
            StateSnapshotEvent(type=EventType.STATE_SNAPSHOT, snapshot=state),
            CustomEvent(
                type=EventType.CUSTOM,
                name='calculation_complete',
                value={'operation': 'add', 'result': result}
            ),
        ],
    )
```

Custom events let agents signal domain-specific actions to the UI. A document editor might use them to trigger highlights; a workflow app might use them to update progress indicators. The UI interprets these events according to its needs.

## Using the Core Library

The core library provides helpers to simplify AG-UI application creation:

```python
from agentic_patterns.core.ui.agui.app import create_agui_app
from agentic_patterns.core.ui.agui.events import tool_return_with_state

# Create app from config
app = create_agui_app(
    config_name="default",
    instructions="You are a helpful assistant.",
    tools=[add, sub],
)

# In tools, use helpers for common patterns
@agent.tool
async def add(ctx: RunContext[StateDeps[State]], a: int, b: int) -> ToolReturn:
    result = a + b
    ctx.deps.state.last_result = result
    return tool_return_with_state(
        return_value=f"Result: {result}",
        state=ctx.deps.state,
        custom_events=[('calculation_complete', {'result': result})],
    )
```

The `create_agui_app` function uses the core agent configuration system, so you can leverage the same model configurations as the rest of the codebase. The event helpers reduce boilerplate when returning state snapshots and custom events.

## Testing with curl

You can test AG-UI endpoints directly with curl:

```bash
curl -X POST http://localhost:8000 \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"messages": [{"role": "user", "content": "What is 2 + 2?"}]}'
```

The response is a stream of Server-Sent Events (SSE) that represent the agent's execution: run started, text deltas, tool calls, state updates, and run finished.

## FastAPI Integration

For more control over the HTTP layer, use `AGUIAdapter` with FastAPI:

```python
from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import Response
from pydantic_ai import Agent
from pydantic_ai.ui.ag_ui import AGUIAdapter

agent = Agent('openai:gpt-4o-mini', instructions='Be helpful.')
app = FastAPI()

@app.post('/')
async def run_agent(request: Request) -> Response:
    return await AGUIAdapter.dispatch_request(request, agent=agent)
```

This gives you control over routing, middleware, authentication, and other FastAPI features while still using AG-UI for the agent communication protocol.

## Key Takeaways

AG-UI is a protocol, not a framework. `AGUIApp` wraps a PydanticAI agent and exposes it via HTTP with SSE streaming. Any AG-UI compatible frontend can connect.

State management uses `StateDeps` to share a typed Pydantic model between UI and agent. Tools can modify state and emit `StateSnapshotEvent` to synchronize changes.

Custom events via `CustomEvent` allow agents to signal domain-specific actions that the UI can interpret and render.

The event stream includes lifecycle events (run started/finished), text deltas for streaming responses, tool call events, state snapshots, and custom events. This gives UIs full visibility into agent execution.

AG-UI separates agent logic from UI completely. You can swap frontends without touching agent code, or swap agent implementations without rebuilding the UI, as long as both speak the AG-UI protocol.
