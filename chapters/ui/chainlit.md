## Chainlit

Chainlit is a lightweight framework for wrapping an agent or LLM workflow in a chat-oriented web UI, optimized for fast iteration and debugging during early development.

### A UI framework optimized for conversational prototypes

Chainlit fills a role similar to Streamlit, but is purpose-built for conversational and agentic systems. The primary interaction model is a chat session, where messages, partial outputs, and intermediate execution steps are first-class concepts. The UI natively supports token streaming, progress visualization, rich attachments, and structured user inputs, all of which are essential when prototyping agents whose behavior unfolds over time rather than in a single request–response cycle.

Internally, Chainlit runs as an asynchronous web application that communicates with the browser via websockets. This allows the UI to update incrementally as tokens are generated or tools are executed, rather than waiting for a full response to complete. For agent development, this low-latency feedback loop significantly improves debuggability and iteration speed.

### Programming model and chat lifecycle

A Chainlit application is defined by registering asynchronous lifecycle hooks. Developers do not manage an HTTP server directly; instead, they provide handlers that Chainlit invokes at well-defined moments in the chat lifecycle, such as when a session starts or when the user sends a message.

A minimal structure initializes per-session state and delegates each user message to an agent or orchestration function:

```python
@cl.on_chat_start
async def init():
    agent = build_agent()
    cl.user_session.set("agent", agent)

@cl.on_message
async def on_message(message: cl.Message):
    agent = cl.user_session.get("agent")
    answer = await agent(message.content)
    await cl.Message(content=answer).send()
```

This model keeps UI concerns separate from agent logic and aligns naturally with agent runtimes that expose a single asynchronous entry point.

### Messages and token streaming

The `Message` abstraction represents content sent to the user. Messages can be created eagerly, updated later, and populated incrementally via token streaming. Streaming is especially valuable during prototyping, as it exposes latency sources and makes partial progress visible.

```python
@cl.on_message
async def on_message(message: cl.Message):
    msg = await cl.Message(content="").send()

    async for token in llm_stream(message.content):
        await msg.stream_token(token)

    await msg.update()
```

This pattern applies equally to direct model calls and to more complex agent pipelines that yield tokens over time.

### Steps: exposing intermediate agent behavior

In agentic systems, the intermediate reasoning and tool usage often matter as much as the final answer. Chainlit provides the `Step` abstraction to surface these intermediate units of work directly in the UI. Steps are visible execution blocks that can represent retrieval, tool calls, planning phases, or sub-agent invocations.

While steps can be created explicitly, the idiomatic and recommended approach is to define them using the `@cl.step` decorator. In this model, a step corresponds to an asynchronous function, and Chainlit manages the step lifecycle automatically.

```python
@cl.step(type="tool")
async def crm_lookup(query: str):
    await cl.sleep(2)
    return "Response from the tool!"
```

When this function is awaited, Chainlit creates a step whose name defaults to the function name. The step starts when the function is entered, and the return value is displayed as the step output when the function completes.

Steps can be composed naturally inside a message handler:

```python
@cl.on_message
async def on_message(message: cl.Message):
    result = await crm_lookup(message.content)
    await cl.Message(content=result).send()
```

This pattern keeps UI instrumentation minimal while still producing a clear execution trace in the interface.

### Step inputs, outputs, and streaming

Decorated steps also support explicit inputs and token-level streaming. The currently executing step is accessible via the Chainlit context, which allows advanced behavior without abandoning the decorator-based approach.

```python
@cl.step(type="llm")
async def generate_answer(prompt: str):
    cl.context.current_step.input = prompt

    async for token in llm_stream(prompt):
        await cl.context.current_step.stream_token(token)

    return "Final synthesized answer"
```

This makes it possible to represent long-running or incremental operations as a single logical step, while still providing fine-grained visibility into progress.

For agent prototypes, steps provide a lightweight execution trace that is often sufficient on its own, without introducing a full observability or tracing stack.

### Session state and conversational context

Agents typically require memory and configuration, but web applications must avoid global state. Chainlit provides per-session storage via `user_session`, which is scoped to a single chat thread. This is where agent instances, tool clients, caches, or per-user configuration are usually stored.

```python
@cl.on_chat_start
async def init():
    cl.user_session.set("agent", build_agent())
    cl.user_session.set("settings", {"temperature": 0.2})

@cl.on_message
async def on_message(message: cl.Message):
    agent = cl.user_session.get("agent")
    settings = cl.user_session.get("settings")
    answer = await agent(message.content, **settings)
    await cl.Message(content=answer).send()
```

Chainlit can also expose the current conversation context in formats compatible with common LLM APIs, which is useful when prototyping agents that do not yet implement their own memory subsystem.

### Using Chainlit with agent runtimes

Chainlit is most effective when treated as a thin UI layer over an existing agent runtime. A common pattern is to structure the agent as an asynchronous generator that emits execution events, and to map those events to messages and steps.

However, when agent actions map cleanly to tools or sub-operations, the decorator-based step model often leads to simpler and more readable code. Tool calls, retrieval functions, and even sub-agent invocations can be expressed as decorated steps, producing a clear and structured execution trace with minimal UI glue.

Chainlit also offers first-party integrations with popular agent frameworks such as LangChain, LangGraph, and LlamaIndex, where callbacks automatically translate intermediate execution events into steps. These integrations are particularly useful for quickly visualizing agent behavior when adopting an existing framework.

Finally, Chainlit includes support for Model Context Protocol (MCP), enabling agents to connect to external tool providers through standardized interfaces. This allows developers to assemble tool-augmented prototypes without tightly coupling the UI to specific tool implementations.

### Deployment and operational considerations

Because Chainlit relies on websockets, deployments typically require infrastructure that supports persistent connections and, in many cases, session affinity so that a client remains routed to the same backend instance. Chainlit can also be served under a subpath, which is useful when embedding it into a larger application.

Authentication is optional but supported. Applications can be made private by enabling authentication and configuring token signing, and OAuth integration is available when users should authenticate via an existing identity provider.
