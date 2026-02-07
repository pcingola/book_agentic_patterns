## Error propagation, cancellation, and human-in-the-loop

When an agent run spans multiple layers -- tools, sub-agents, inter-agent protocols, and a user-facing frontend -- three concerns that feel simple in a monolithic application become distributed problems: errors, cancellation, and human interaction. Each layer in the stack encodes these signals in its own way. A tool protocol may represent failure as a structured response field. An inter-agent protocol may represent it as a task state transition. An agent framework may represent it as a language-level exception. A UI protocol may represent it as an interrupted event stream. None of these representations are equivalent, yet they all describe "something went wrong", "stop what you are doing", or "I need input before I can continue".

The challenge is translation at boundaries. When a tool error crosses into an agent framework, it must become something the framework can act on (retry, abort, ask the user). When a sub-agent failure crosses into a coordinator, it must become something the coordinator model can reason about. When all recovery options are exhausted, the failure must reach the UI as a clean terminal signal rather than a stream that silently dies. This section walks through what each layer in our stack provides -- MCP, A2A, PydanticAI, AG-UI -- where the translation gaps are, and how the project bridges them. Earlier chapters covered MCP tool errors (Tools chapter), A2A task lifecycle (A2A chapter), and MCP elicitation (MCP Features chapter); the focus here is on what happens when these layers are stacked.


### Error representations across the stack

#### MCP

MCP defines two error paths, covered in the Tools chapter. Protocol errors are standard JSON-RPC error responses (unknown tool, invalid arguments, internal error) that indicate the call never executed. Tool execution errors are successful JSON-RPC responses whose result carries `isError: true`, indicating the tool ran and failed. ([MCP Spec][1])

In FastMCP, when a tool function raises an unhandled exception, the `ToolManager` catches it and re-raises a `ToolError`. The server's low-level handler converts `ToolError` into a `CallToolResult` with `isError: true` and the error message as text content. The `mask_error_details` setting controls whether the original exception message reaches the client: when enabled, the client sees only `"Error calling tool 'x'"` without the underlying cause. When a tool explicitly raises `ToolError`, the message always reaches the client regardless of masking. ([FastMCP][2])

A tool error result looks like this on the wire:

```json
{
  "content": [
    {"type": "text", "text": "Error calling tool 'fetch_data': connection refused"}
  ],
  "isError": true
}
```

#### PydanticAI

PydanticAI draws a sharp line between two kinds of tool failure. `ModelRetry` means "the model made a fixable mistake -- give it the error message and let it try again with different arguments". Any other exception means "something is genuinely broken -- abort the run". The tool manager only catches `ModelRetry` (and `ValidationError` for argument validation); everything else propagates up uncaught and ends the agent run.

```python
from pydantic_ai import Agent, ModelRetry, RunContext

agent = Agent("openai:gpt-4o")

@agent.tool
async def lookup_user(ctx: RunContext, email: str) -> str:
    if not email.endswith("@example.com"):
        # Recoverable: the model picked a bad argument, let it retry
        raise ModelRetry(f"Invalid domain in {email}. Only @example.com is allowed.")

    user = db.find_by_email(email)
    if user is None:
        # Fatal: the database is unreachable or the data is missing.
        # Don't let the model waste tokens retrying -- end the run.
        raise ValueError(f"No user found for {email}")

    return f"User: {user.name}, role: {user.role}"
```

At the run level, PydanticAI defines the `AgentRunError` hierarchy for failures that are not tool-specific: `UnexpectedModelBehavior` for malformed model responses, `UsageLimitExceeded` for token/request limits, `ModelHTTPError` for provider API failures (4xx/5xx), and `FallbackExceptionGroup` when all fallback models fail. ([PydanticAI Exceptions][4])

PydanticAI also handles MCP tool errors internally, but with a different policy. When an MCP tool returns a result with `isError: true`, the MCP toolset raises `ModelRetry` with the error text. Similarly, when the MCP server returns a JSON-RPC protocol error (`McpError`), the toolset also raises `ModelRetry`. In other words, all MCP tool failures become retries -- the model always gets a second chance. ([PydanticAI MCP][3])

This creates a subtle inconsistency worth being aware of. Consider the same `ValueError` raised in two contexts: as a direct PydanticAI tool, it ends the run immediately. As an MCP tool, FastMCP catches it, wraps it in a `ToolError`, the server converts that to `isError: true`, PydanticAI's MCP toolset sees the error flag, and raises `ModelRetry` -- giving the model a chance to retry. Same exception, same tool logic, different behavior depending on the deployment boundary. The MCP path is more forgiving because it has no way to distinguish "bad arguments the model could fix" from "infrastructure failure that will never recover" -- everything is flattened into `isError: true`. When moving tools between direct registration and MCP servers, keep this asymmetry in mind: you may need to add explicit `ModelRetry` raises in the direct version to match the retry behavior you relied on through MCP.

#### A2A

A2A uses the same two-level error model as MCP but expressed differently, as covered in the A2A chapter. Protocol errors follow JSON-RPC conventions: standard codes `-32700` through `-32603` for parse/request/method/params/internal errors, plus A2A-specific codes in the `-32001` to `-32009` range for domain errors like `TaskNotFoundError` (`-32001`), `TaskNotCancelableError` (`-32002`), and `VersionNotSupportedError` (`-32009`). ([A2A Spec][5])

Execution failures surface as task state transitions rather than exceptions. When a sub-agent's work fails, the task enters the terminal `failed` state with an optional `message` in the `TaskStatus` describing what went wrong. In FastA2A, the worker catches any unhandled exception from the agent run and transitions the task to `failed`, using the exception message as the status message.

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "id": "task-abc-123",
    "status": {
      "state": "failed",
      "message": {"role": "agent", "parts": [{"kind": "text", "text": "Database connection refused"}]}
    }
  }
}
```

This design is deliberate: failure is an outcome of the task lifecycle, not a transport-level exception. The caller inspects the task state rather than catching an exception across a process boundary.

#### AG-UI

PydanticAI's `AGUIAdapter` runs the agent via `run_stream()` and converts agent events into AG-UI SSE events. When the agent run completes normally, the stream ends with a `RunFinished` event. When the run raises an exception, the adapter catches it and terminates the SSE stream. The frontend observes this as a stream that ends without a `RunFinished` event -- there is no structured `RunError` object in the AG-UI event vocabulary. The frontend must therefore treat an abnormally terminated stream as a failed run. ([PydanticAI AG-UI][6])


### Bridging the A2A boundary

The A2A boundary is where the project needs explicit translation logic, because A2A task outcomes arrive as state transitions but PydanticAI expects either return values or exceptions. The project's `create_a2a_tool()` in `agentic_patterns/core/a2a/tool.py` bridges this gap.

The delegation tool calls `A2AClientExtended.send_and_observe()`, which returns a `tuple[TaskStatus, dict | None]` -- the `TaskStatus` enum and the raw task dict. It then uses `match` to translate each outcome into a formatted string that the coordinator model can parse:

```python
match status:
    case TaskStatus.COMPLETED:
        text = extract_text(task) or "Task completed"
        return f"[COMPLETED] {text}"
    case TaskStatus.INPUT_REQUIRED:
        question = extract_question(task)
        return f"[INPUT_REQUIRED:task_id={task['id']}] {question}"
    case TaskStatus.FAILED:
        msg = task["status"].get("message") if task else "Unknown error"
        return f"[FAILED] {msg}"
    case TaskStatus.CANCELLED:
        return "[CANCELLED] Task was cancelled"
    case TaskStatus.TIMEOUT:
        return "[TIMEOUT] Task timed out"
```

The design choice is to return formatted strings rather than raising exceptions. The `[COMPLETED]`, `[FAILED]`, `[INPUT_REQUIRED:task_id=xyz]`, `[CANCELLED]`, and `[TIMEOUT]` prefixes are conventions the coordinator model interprets through its system prompt. A `[FAILED]` result does not crash the coordinator -- the model can decide whether to try a different sub-agent, reformulate the request, or report the failure to the user.

When should this boundary raise `ModelRetry` or `RuntimeError` instead of returning a string? If a sub-agent failure is potentially recoverable (wrong parameters, ambiguous request the coordinator could reformulate), `ModelRetry` lets the LLM try a different approach. If the failure is permanent (service down, authentication failure), a `RuntimeError` ends the run cleanly rather than wasting tokens on retries. The current implementation favors returning strings for all outcomes, giving the coordinator maximum flexibility, but a stricter variant could raise exceptions for clearly permanent failures.


### Cancellation

#### MCP

MCP supports best-effort cancellation of in-flight requests via the `notifications/cancelled` notification, which carries the `requestId` and an optional `reason` string. Receivers may ignore the notification if the request is unknown, already completed, or not cancelable. The `initialize` request must not be cancelled. For task-augmented requests (the experimental tasks feature), `tasks/cancel` must be used instead of `notifications/cancelled`. ([MCP Spec][7])

#### A2A

A2A provides the `CancelTask` JSON-RPC method, which takes a task ID and transitions the task to the `canceled` state. The operation returns `TaskNotCancelableError` (`-32002`) for tasks already in a terminal state (`completed`, `failed`, `canceled`, `rejected`). Once canceled, the task must remain in `canceled` state even if execution continues internally -- the protocol treats cancellation as a commitment, not a suggestion. ([A2A Spec][8])

#### Project integration

The project's `A2AClientExtended.send_and_observe()` accepts an `is_cancelled` callback that is checked on each poll iteration. When the callback returns `True`, the client calls `cancel_task()` and returns `(TaskStatus.CANCELLED, None)` without waiting for the server to acknowledge:

```python
if is_cancelled and is_cancelled():
    logger.info(f"[A2A] Task {task_id} cancelled by user")
    await self.cancel_task(task_id)
    return (TaskStatus.CANCELLED, None)
```

This pattern composes across layers. A coordinator agent can pass its own cancellation signal through to sub-agents by providing an `is_cancelled` callback when creating the A2A tool via `create_a2a_tool()`. The callback bridges whatever cancellation mechanism the outer layer uses (a flag, a threading event, a frontend disconnect) into the A2A polling loop.

#### AG-UI

When the frontend disconnects the SSE stream, the server-side `StreamingResponse` loses its consumer. The ASGI framework can detect this (the send channel raises an exception), which propagates up through the adapter. If the adapter is currently awaiting sub-agent results, the cancellation callback can trigger, propagating the disconnect downstream as A2A task cancellations.


### Human-in-the-loop

Three mechanisms at three layers provide structured human interaction, each designed for different communication boundaries.

#### MCP elicitation

MCP elicitation, introduced in the MCP Features chapter, allows servers to request structured input from the user via the `elicitation/create` method. Form mode collects data through a flat JSON Schema, and URL mode directs the user to an external URL for sensitive interactions (credentials, OAuth flows) where the data must not pass through the MCP client. ([MCP Spec][9])

The response uses a three-action model: `accept` (with data for form mode), `decline`, or `cancel`. This gives the server enough information to distinguish between "user provided input", "user explicitly refused", and "user dismissed without deciding".

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "elicitation/create",
  "params": {
    "mode": "form",
    "message": "Please provide your database credentials",
    "requestedSchema": {
      "type": "object",
      "properties": {
        "host": {"type": "string"},
        "port": {"type": "integer", "minimum": 1, "maximum": 65535}
      },
      "required": ["host", "port"]
    }
  }
}
```

#### A2A input-required

A2A models human interaction as a task state. When an agent needs clarification, the task enters `input-required` -- an interrupted state, not a terminal one. In blocking mode, `input-required` breaks the blocking wait, returning control to the client. The client then sends a new message with the same `taskId` and `contextId` to continue the conversation. ([A2A Spec][10])

This mechanism is broader than MCP elicitation: it represents any situation where the remote agent cannot proceed without external input, whether that input comes from a human, another system, or the coordinating agent itself. The task remains in `input-required` until a new message arrives or the task is cancelled.

#### Project integration

The project's `create_a2a_tool()` returns `[INPUT_REQUIRED:task_id=xyz] question` when a sub-agent task enters the `input-required` state. The coordinator's system prompt, built by `build_coordinator_prompt()`, instructs the model to handle this:

```
When you see [INPUT_REQUIRED:task_id=...], ask the user for the
required information and call the tool again with the same task_id
to continue.
```

The coordinator model reads the question, presents it to the user through the normal chat flow, and when the user responds, calls the delegation tool again with the same `task_id` and the user's answer as the `prompt`. The `send_and_observe()` method sends this as a continuation message on the existing task, and the sub-agent resumes.

#### Interaction with timeouts

When a task is legitimately waiting for human input, that waiting time must not be confused with a hung operation. The `input-required` state breaks the polling loop in `send_and_observe()` immediately (it is handled alongside terminal states in the `match` block), so the timeout counter does not accumulate during the period the user is thinking. The timeout only applies to the active polling phases when the task is in `working` state.


### References

1. Model Context Protocol Contributors. *Tools*. Model Context Protocol Specification, 2025. [https://modelcontextprotocol.io/specification/2025-11-25/server/tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)
2. FastMCP Contributors. *Exceptions*. FastMCP Documentation, 2025. [https://gofastmcp.com/python-sdk/fastmcp-exceptions](https://gofastmcp.com/python-sdk/fastmcp-exceptions)
3. Pydantic Services Inc. *MCP toolset*. Pydantic AI Documentation, 2025. [https://ai.pydantic.dev/mcp/](https://ai.pydantic.dev/mcp/)
4. Pydantic Services Inc. *Exceptions*. Pydantic AI Documentation, 2025. [https://ai.pydantic.dev/api/exceptions/](https://ai.pydantic.dev/api/exceptions/)
5. A2A Protocol Contributors. *JSON-RPC Protocol Binding*. A2A Specification, 2025. [https://a2a-protocol.org/latest/specification/](https://a2a-protocol.org/latest/specification/)
6. Pydantic Services Inc. *Agent-User Interaction (AG-UI) Protocol*. Pydantic AI Documentation, 2025. [https://ai.pydantic.dev/ui/ag-ui/](https://ai.pydantic.dev/ui/ag-ui/)
7. Model Context Protocol Contributors. *Cancellation*. Model Context Protocol Specification, 2025. [https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/cancellation](https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/cancellation)
8. A2A Protocol Contributors. *Protocol Operations*. A2A Specification, 2025. [https://a2a-protocol.org/latest/specification/](https://a2a-protocol.org/latest/specification/)
9. Model Context Protocol Contributors. *Elicitation*. Model Context Protocol Specification, 2025. [https://modelcontextprotocol.io/specification/2025-11-25/client/elicitation](https://modelcontextprotocol.io/specification/2025-11-25/client/elicitation)
10. A2A Protocol Contributors. *Task Lifecycle and States*. A2A Specification, 2025. [https://a2a-protocol.org/latest/specification/](https://a2a-protocol.org/latest/specification/)

[1]: https://modelcontextprotocol.io/specification/2025-11-25/server/tools "MCP Tools"
[2]: https://gofastmcp.com/python-sdk/fastmcp-exceptions "FastMCP Exceptions"
[3]: https://ai.pydantic.dev/mcp/ "PydanticAI MCP"
[4]: https://ai.pydantic.dev/api/exceptions/ "PydanticAI Exceptions"
[5]: https://a2a-protocol.org/latest/specification/ "A2A Specification"
[6]: https://ai.pydantic.dev/ui/ag-ui/ "PydanticAI AG-UI"
[7]: https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/cancellation "MCP Cancellation"
[8]: https://a2a-protocol.org/latest/specification/ "A2A Specification"
[9]: https://modelcontextprotocol.io/specification/2025-11-25/client/elicitation "MCP Elicitation"
[10]: https://a2a-protocol.org/latest/specification/ "A2A Specification"
