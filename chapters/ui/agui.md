## AG-UI

AG-UI is an event-stream protocol that standardizes how an agent backend and a user-facing application stay in sync during an interactive run. ([AG-UI][1])

### Chainlit vs. AG-UI

Chainlit is an application framework: it gives you a ready-made web UI plus a Python runtime model for chat-oriented apps, so your “frontend” and “agent loop” typically evolve together inside one stack. ([Chainlit][2])

AG-UI is a protocol boundary: it defines the bi-directional contract between “any agentic backend” and “any UI client” by streaming a sequence of typed interaction events (text deltas, tool calls, state updates, lifecycle signals). The result is that you can swap UIs without rewriting the agent, and you can swap agent frameworks without rebuilding the UI, as long as both sides speak the same event stream. ([AG-UI][1])

A practical way to summarize the tradeoff is that Chainlit optimizes for speed-to-demo (framework convenience), while AG-UI optimizes for long-lived interoperability (protocol stability across heterogeneous frontends and agent runtimes). ([AG-UI][1])

### The core abstraction: a streaming event log

AG-UI treats an interaction as a run that produces a single ordered stream of events. Events are the fundamental units of communication and are categorized around what a UI needs to render and control an agent run: lifecycle, streaming text/messages, tool execution, and state synchronization. ([AG-UI][3])

This “event log” framing is not cosmetic. It forces both sides to be explicit about what happened and when, which makes agentic UX debuggable: you can replay a run, inspect a failure around a tool call, or render partial progress while the agent is still thinking or waiting on external systems. ([AG-UI][3])

In pseudocode, a server-side agent run under AG-UI looks like producing an iterator of events:

```python
def run(input):
    yield RunStarted(run_id=input.run_id)

    # stream assistant text
    yield TextDelta(text="Let me check that...")
    result = call_tool("search_docs", query=input.user_message)

    # reflect tool progress to UI
    yield ToolCallStarted(name="search_docs")
    yield ToolCallFinished(name="search_docs", result_summary="3 matches")

    # optionally update shared UI/server state
    yield StatePatch(path="last_query", value=input.user_message)

    yield TextDelta(text="Here is what I found.")
    yield RunFinished()
```

The key point is that the UI is no longer forced to infer what is happening from raw tokens alone; it can render “tool is running”, “state changed”, “run ended”, and other agentic UX primitives directly from the stream. ([AG-UI][3])

### Messages: interaction as structured conversation history

AG-UI formalizes “what the user said” and “what the assistant said” as messages within the run input/output contract, alongside the event stream itself. On the server side, that typically means your agent receives both the latest user message and enough prior context to behave consistently across refreshes, reconnects, and multi-turn sessions. ([Pydantic AI][4])

This matters for UI design because message history is part of what the frontend can send, store, and recover. In other words, “conversation state” is not an implicit in-memory property of one Python process; it becomes explicit data moving over the protocol boundary. ([Pydantic AI][4])

### State management: shared, bidirectional application state

Many agentic applications need more than chat history: drafts, selections, form values, filters, “current document”, and other UI state must stay synchronized with the agent’s internal view. AG-UI includes state management events designed for real-time synchronization between the UI and the agent backend. ([AG-UI][3])

A useful mental model is to treat shared state as a small application store that either side can patch, with those patches flowing as events. When implemented carefully, this enables patterns like “agent edits the user’s document while the user types”, “agent proposes a diff the UI can accept/reject”, or “agent maintains a structured plan the UI visualizes”.

In Pydantic AI’s integration, the incoming state is carried as part of the run input, and you can validate/shape it as a typed model on the server side so you do not accept arbitrary frontend state blindly:

```python
class DocState(BaseModel):
    text: str
    cursor: int

class Deps(StateDeps[DocState]):
    pass

agent = Agent(model="openai:gpt-5", deps_type=Deps)

@agent.tool
def insert_text(ctx, new_text: str) -> None:
    s = ctx.deps.state
    s.text = s.text[:s.cursor] + new_text + s.text[s.cursor:]
    s.cursor += len(new_text)
```

The design intent is that state remains isolated per request/run and is validated when it crosses the boundary, which is essential when the “client” is a browser or another untrusted UI surface. ([Pydantic AI][4])

### Tools: making UI capabilities first-class

AG-UI is explicitly bi-directional: the UI can provide “client-side tools” that the agent can call, and the agent can expose server-side tools as part of its runtime. This supports modern agentic UX where some actions are best executed in the client (opening a modal, highlighting text, mutating a local canvas) while others must run on the server (database queries, private API calls, retrieval). ([AG-UI][5])

Conceptually, a client-side tool call is just another typed event in the stream. In practice, it means you can author UX-centric affordances without hard-coding them into a single framework:

```python
def run(input):
    yield TextDelta("I can highlight the relevant paragraph.")
    yield ToolCallRequested(
        name="highlight_range",
        args={"start": 120, "end": 210}
    )
    yield TextDelta("Done—now you can review that section.")
```

This separation aligns with the broader theme of agentic systems in this book: protocols define contracts; implementations remain swappable.

### Transport: “web-native streaming” as the default

AG-UI is designed to ride on common web transports (e.g., HTTP streaming or WebSockets) while preserving the semantics of a single ordered event stream. Pydantic AI’s AG-UI adapter, for example, streams events back to the caller using Server-Sent Events (SSE). ([Pydantic AI][6])

From an implementation standpoint, this emphasizes incremental rendering: the UI should assume the run is a live stream, not a single response blob, and should treat reconnection/retry as normal operational behavior for interactive systems.

### How AG-UI fits with MCP and A2A

In the emerging “agent protocol stack” framing, AG-UI targets agent↔user interaction, while MCP targets agent↔tools/data and A2A targets agent↔agent delegation. AG-UI’s documentation explicitly positions it as complementary to MCP and A2A, and describes protocol handshakes that allow AG-UI clients to front agents reachable via MCP or A2A. ([AG-UI][7])

This is a useful architectural dividing line for the rest of the book: use MCP to standardize external capabilities, use A2A to standardize multi-agent collaboration, and use AG-UI to standardize what the user sees and can control while those capabilities are exercised.

### Minimal integration sketch with Pydantic AI

Pydantic AI provides an ASGI app that exposes a Pydantic AI agent as an AG-UI server. The value here is not that you must use that stack, but that it demonstrates the adapter pattern cleanly: transform “run input” into an agent run, and transform agent events back into protocol events. ([Pydantic AI][8])

```python
agent = Agent(
    model="openai:gpt-5",
    instructions="You are a careful, tool-using research assistant."
)

app = AGUIApp(agent)  # expose the agent via AG-UI
```

Once you have this boundary, you can iterate on the UI independently: a chat UI, a copilot sidebar, a document editor with inline suggestions, or a workflow dashboard can all be clients of the same agent backend, as long as they interpret the same event stream semantics. ([AG-UI][1])

[1]: https://docs.ag-ui.com/ "AG-UI Overview - Agent User Interaction Protocol"
[2]: https://docs.chainlit.io/get-started/overview?utm_source=chatgpt.com "Chainlit: Overview"
[3]: https://docs.ag-ui.com/concepts/events "Events - Agent User Interaction Protocol"
[4]: https://ai.pydantic.dev/ui/ag-ui/ "AG-UI - Pydantic AI"
[5]: https://docs.ag-ui.com/quickstart/introduction "Introduction - Agent User Interaction Protocol"
[6]: https://ai.pydantic.dev/api/ag_ui/?utm_source=chatgpt.com "pydantic_ai.ag_ui"
[7]: https://docs.ag-ui.com/agentic-protocols?utm_source=chatgpt.com "MCP, A2A, and AG-UI - Agent User Interaction Protocol"
[8]: https://ai.pydantic.dev/api/ui/ag_ui/?utm_source=chatgpt.com "pydantic_ai.ui.ag_ui"
