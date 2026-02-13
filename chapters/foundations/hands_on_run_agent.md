## Hands-On: How run_agent() Works (Optional)

This section explains how the `run_agent()` function combines Python's async features to enable agent execution streaming. If you haven't read the Python concepts recap in the previous section, review that first.

### The run_agent() Function

Let's examine the `run_agent()` function in `agentic_patterns/core/agents/agents.py`:

```python
async def run_agent(
        agent: Agent,
        prompt: str | list[str],
        message_history: Sequence[ModelMessage] | None = None,
        usage_limits: UsageLimits | None = None,
        verbose: bool = False,
        catch_exceptions: bool = False,
        ctx: Context | None = None,
    ) -> tuple[AgentRun | None, list]:

    agent_run, nodes = None, []
    try:
        async with agent.iter(prompt, usage_limits=usage_limits, message_history=message_history) as agent_run:
            async for node in agent_run:
                nodes.append(node)
                if ctx:
                    await ctx.debug(f"MCP server {ctx.fastmcp.name}: {node}")
                if verbose:
                    rich.print(f"[green]Agent step:[/green] {node}")
    except Exception as e:
        if verbose:
            rich.print(f"[red]Error running agent:[/red] {e}")
        if not catch_exceptions:
            raise e
    return agent_run, nodes
```

Let's break this down by examining each key part.

### The Async Context Manager

```python
async with agent.iter(prompt, ...) as agent_run:
```

The `agent.iter()` method from Pydantic-AI returns an async context manager. This does two critical things:

On entry (`__aenter__`), it initializes the agent run by sending the prompt to the model and preparing to stream execution events. The context manager ensures proper setup of the agent execution environment.

On exit (`__aexit__`), it finalizes the run, ensuring all resources are cleaned up and the final result is computed. Even if an error occurs during iteration, cleanup happens.

### The Async Iterator

```python
async for node in agent_run:
    nodes.append(node)
```

The `agent_run` object is an async iterator that yields Pydantic-AI graph nodes one at a time. Each node is one of three types: `UserPromptNode` (user input), `ModelRequestNode` (a new model request), or `CallToolsNode` (tool execution requested by the model).

Why async? Because each iteration might involve waiting for the model to generate tokens, for tools to execute, or for network I/O. Using `async for` allows other coroutines to run while we wait, making the system efficient.

We collect all execution events into a list. This provides complete visibility into what the agent did, useful for debugging, logging, and understanding the execution flow.

### Optional Debug Logging

```python
if ctx:
    await ctx.debug(f"MCP server {ctx.fastmcp.name}: {node}")
```

If running within an MCP server context, we send debug messages to the MCP client. Note the `await` because sending messages is an async operation.

### Exception Handling

```python
except Exception as e:
    if verbose:
        rich.print(f"[red]Error running agent:[/red] {e}")
    if not catch_exceptions:
        raise e
```

Standard error handling. If `catch_exceptions=False` (the default), errors propagate to the caller. If `True`, we suppress them and return `None` for the agent run.

### Return Results

```python
return agent_run, nodes
```

We return both the complete `AgentRun` object (containing the final result and metadata) and the list of execution events.

### Why This Design?

This architecture provides several benefits:

**Streaming execution**: You receive events as they happen, not all at once after everything completes. This enables real-time UI updates, progress indicators, and early detection of issues.

**Resource safety**: The async context manager guarantees cleanup happens, preventing resource leaks even during errors or early termination.

**Efficiency**: Async operations mean the thread isn't blocked waiting for API responses. Your application can handle multiple agent runs concurrently on a single thread.

**Observability**: Collecting execution nodes gives complete visibility into agent behavior, essential for debugging complex multi-step reasoning or tool interactions.

**Flexibility**: The same pattern scales from simple one-shot prompts to complex multi-turn conversations with tools, memory, and sophisticated orchestration.

### Key Takeaways

The `run_agent()` function demonstrates how modern Python's async features enable elegant agent implementations. By combining async context managers (for safe resource handling), async iterators (for streaming events), and coroutines (for efficient I/O), we get a clean API that's both powerful and easy to use.

When you write `await run_agent(agent, prompt)`, you're using:
- A coroutine (`run_agent` is `async def`)
- An async context manager (`async with agent.iter()`)
- An async iterator (`async for node in agent_run`)
- Async operations throughout (each `await` yields control while waiting)

This pattern appears throughout modern async Python codebases, especially for systems involving I/O operations like API calls, databases, or message queues. Understanding it unlocks the ability to build sophisticated, efficient applications that handle multiple concurrent operations gracefully.
