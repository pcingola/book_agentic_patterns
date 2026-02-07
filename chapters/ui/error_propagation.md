## Error propagation, cancellation, and human-in-the-loop

When a user-facing run spans multiple layers—UI, main agent, skill execution, sub-agents, inter-agent protocols, and tool runtimes—basic UI semantics such as errors, cancellation, and user input become distributed concerns. Each layer introduces its own execution model, failure modes, and lifecycle, and the UI must present a coherent experience without exposing this internal topology.

Throughout this section we will use the same concrete execution chain as a running example:

**tool → MCP server → MCP client → sub-agent → A2A → skill → main agent → UI (AG-UI)**

The goal is not to prescribe a single “correct” implementation, but to show where semantic mismatches arise and how to structure translation layers so that UI behavior remains predictable.

### Error propagation

A practical error strategy starts by acknowledging that MCP, A2A, and Pydantic-AI do not mean the same thing by “tool failure”, and AG-UI expects a clean run-level termination signal (RunError) once recovery is no longer possible. In MCP, tool failures can surface either as JSON-RPC protocol errors (unknown tool, invalid arguments, server error) or as successful JSON-RPC responses whose tool result is marked with isError: true for execution failures. In A2A, failure is typically represented as a task reaching a terminal failed state rather than as an exception thrown across a call boundary. In Pydantic-AI, by contrast, exceptions raised by tools generally end the run unless the exception is a ModelRetry, which explicitly asks the model to try again; moreover, both the agent’s retries setting and the run context’s max_retries can allow repeated tool-call attempts.

These differences become visible in a common “stacked delegation” scenario: a main agent runs a Skill, delegates work to a sub-agent over A2A, the sub-agent calls a tool exposed by a FastMCP server, and the tool throws an exception. FastMCP provides middleware intended to convert server exceptions into MCP error responses, but the result still arrives at the client as an MCP-level error shape that must be interpreted and mapped upstream. If the sub-agent simply “raises whatever it got”, the main agent may interpret the failure as a generic exception and either abort immediately or, worse, trigger a retry policy intended for model/tool-call correction rather than for remote service failures.

In a single-process application, an error is usually an exception that unwinds the call stack. In a distributed agentic system, that assumption no longer holds. Failures cross protocol boundaries, process boundaries, and abstraction layers, and each layer encodes failure differently.

At the most general level, three questions must be answered at every boundary:

First, how is failure represented at this layer: as an exception, a structured response, or a state transition?
Second, does this failure imply that execution should stop, or can it be retried or recovered from?
Third, how should this failure be surfaced to the user-facing UI?

These questions become concrete when we follow a failure from the bottom of the stack upward.

#### Generic failure flow in a tool → MCP → A2A → agent → UI pipeline

Consider a tool invoked by a sub-agent. The tool may fail due to invalid input, business logic errors, resource exhaustion, or transient infrastructure problems. That failure is first observed inside the tool runtime. From there, it must be encoded into MCP, propagated to the sub-agent, forwarded over A2A to the main agent executing a Skill, and finally translated into a UI-level outcome.

At the MCP boundary, failures are not uniformly “exceptions”. The protocol distinguishes between protocol-level errors (for example, unknown tool, invalid arguments, server errors) and tool execution failures that are returned as successful responses but explicitly marked as errors. Both represent failure, but they carry different semantics: protocol errors indicate a failure to even perform the call, while execution errors indicate that the call ran and failed.

At the A2A boundary, failure is modeled primarily as a task lifecycle outcome. A sub-agent does not “throw” an exception to its caller; instead, the task transitions into a terminal failed state, optionally carrying a message or metadata describing the reason. This is a deliberate design choice: failure is an outcome, not a transport error.

At the agent framework boundary, failure is often represented again as an exception or as a control signal to the planner. At this point, the system must decide whether the failure is local and recoverable, or global and fatal to the current run.

Finally, at the UI boundary, protocols such as AG-UI expect a clean run-level signal indicating that execution has completed successfully, failed, or was canceled. Once recovery is no longer possible, the UI must receive a definitive termination event rather than a stream that silently stops.

The core challenge is that none of these representations are equivalent, even though they all describe “something went wrong”.

#### Why naïve propagation fails

If each layer simply forwards “whatever it got”, several pathologies appear.

A deterministic tool execution failure may be misinterpreted by the agent framework as a transient error and retried repeatedly, wasting tokens and time.
A protocol-level MCP error may be collapsed into a generic exception, losing the distinction between “bad call” and “tool ran and failed”.
A sub-agent task failure may be treated as an infrastructure failure rather than as a meaningful domain outcome.
The UI may receive an abrupt disconnect instead of a structured run error, leaving the user without feedback.

These problems are amplified when retries are involved, because retries exist at multiple layers and were designed independently.

#### A general design principle: normalize failures at boundaries

A robust approach is to treat each protocol boundary as a translation point. Instead of propagating raw failures, each boundary maps failures into a normalized internal representation that preserves intent while discarding protocol-specific noise.

Conceptually, the system benefits from an internal failure envelope that answers four questions:

Where did the failure originate?
What kind of failure is it (protocol, execution, logical)?
Is it retryable at this layer?
What message is safe and useful to surface upstream?

This normalization happens multiple times, but always in the same direction: from lower-level, more technical representations toward higher-level, more semantic ones.

```python
class FailureEnvelope(Exception):
    def __init__(self, *, source, kind, message, retryable, details=None):
        self.source = source
        self.kind = kind            # protocol | execution | logical
        self.message = message
        self.retryable = retryable
        self.details = details or {}
```

#### Mapping concrete frameworks onto this model

At the MCP layer, the normalization step distinguishes between protocol errors and execution errors and assigns retryability explicitly. FastMCP, for example, converts server-side exceptions into MCP error responses and enforces tool timeouts at the server boundary. Those timeouts are infrastructure failures and are often retryable, while execution failures usually are not.

```python
def call_tool_via_mcp(tool_name, args):
    response = mcp.call_tool(tool_name, args)

    if response.protocol_error:
        raise FailureEnvelope(
            source=f"mcp:{tool_name}",
            kind="protocol",
            message=response.protocol_error.message,
            retryable=is_transient(response.protocol_error),
        )

    if response.result.is_error:
        raise FailureEnvelope(
            source=f"mcp:{tool_name}",
            kind="execution",
            message=response.result.content,
            retryable=False,
        )

    return response.result.content
```

At the sub-agent boundary, this normalized failure should not escape as an exception. Instead, the sub-agent should translate it into a task-level outcome. In FastA2A-style servers, this typically means marking the task as failed and attaching a human-readable explanation. This aligns with the A2A model, where failure is an explicit state rather than an exception crossing the wire.

At the main agent boundary, the same failure envelope can now drive planning decisions. Here is where agent-specific behavior becomes relevant. In frameworks like Pydantic-AI, raising a generic exception usually ends the run, while raising a `ModelRetry` explicitly asks the model to attempt a corrected tool call. This is powerful, but dangerous if applied indiscriminately.

The key point is that retries should be a conscious decision made after normalization, not an accidental side effect of exception handling.

```python
def skill_tool_wrapper(args):
    try:
        return call_tool_via_mcp("analyze_data", args)
    except FailureEnvelope as e:
        if e.retryable:
            # Ask the model to reason and try again
            raise ModelRetry(e.message)
        # Non-retryable: propagate upward
        raise
```

Finally, when the main agent determines that no further recovery is possible, the failure must be translated into a run-level error for the UI. AG-UI expects a clean terminal signal indicating failure, not a partial stream that simply stops. The internal failure envelope is reduced one last time into a stable, user-facing error message.

#### Summary

The important lesson is not that any single framework is “right” or “wrong”, but that each was designed with different assumptions. MCP separates protocol and execution errors. A2A treats failure as a task outcome. Agent frameworks introduce retries and planning semantics. UI protocols expect clean lifecycle transitions. Without explicit normalization at boundaries, these assumptions collide.

### Cancellation

#### Cancellation as a distributed control signal

Cancellation is often treated as a UI concern, but in an agentic stack it is a cross-cutting control signal that must propagate through the same layers as execution itself. A user clicking “Cancel” in the UI should ideally stop the skill, the main agent, any delegated sub-agents, and any in-flight tool calls.

As with errors, each layer supports cancellation differently.

At the protocol level, MCP supports best-effort cancellation of in-flight requests via cancellation notifications. These notifications may arrive too late and are explicitly allowed to be ignored if the operation has already completed.

At the inter-agent level, A2A provides an explicit task cancellation request that transitions a task into a canceled state. This is a semantic cancellation: the task is no longer expected to produce a result.

At the agent and skill level, cancellation is usually implemented cooperatively, by checking a cancellation token between awaited operations.

At the UI level, AG-UI needs to reflect cancellation as a distinct terminal outcome, not as an error.

#### Coordinating cancellation across layers

A robust design treats cancellation as both a local and a remote concern. Locally, the main agent maintains a cancellation token that is checked at safe boundaries. Remotely, the agent issues best-effort cancellation requests to any downstream components that may still be running.

```python
class CancelToken:
    def __init__(self):
        self.cancelled = False

    def cancel(self):
        self.cancelled = True

    def check(self):
        if self.cancelled:
            raise Cancelled()


async def run_skill_with_cancellation(run_id, request):
    token = CancelToken()
    active_task_id = None

    ui.on_cancel(run_id, lambda: (
        token.cancel(),
        active_task_id and a2a.cancel_task(active_task_id),
    ))

    try:
        token.check()
        active_task_id = await a2a.send("sub-agent", request)

        async for update in a2a.stream(active_task_id):
            token.check()
            ui.emit(update)

        ui.emit_run_finished(run_id)
    except Cancelled:
        ui.emit_run_cancelled(run_id)
```

This pattern acknowledges that cancellation is inherently racy. A tool may finish just as a cancellation arrives. A sub-agent may already have produced a result. The system must tolerate these races and converge on a single user-visible outcome.

### Human in the loop

#### Human input as a first-class execution state

Human-in-the-loop interactions are the mirror image of cancellation. Instead of stopping execution, the system pauses and waits for external input. As with errors and cancellation, the challenge is to expose this pause cleanly at the UI level without leaking architectural details.

A2A models this explicitly: a task can enter an input-required state. Execution is suspended, not failed, and can resume when new input is sent to the same task. This is a semantic pause, not a timeout or error.

At the UI level, AG-UI naturally supports this interaction style by allowing agents to emit events that request user input and then continue streaming once input is provided.

#### Bridging sub-agent questions to the UI

The complication arises when the request for input originates in a sub-agent. The user should not be aware that a delegated agent is asking the question, nor should the UI need to know how to route responses through A2A.

The main agent therefore acts as a router. When it observes a sub-agent task entering an input-required state, it emits a UI-level prompt event and records a correlation between that prompt and the underlying task. When the user responds, the main agent uses that correlation to forward the answer back to the correct sub-agent task.

```python
prompt_routes = {}

def handle_subagent_update(run_id, task_update):
    if task_update.state == "input-required":
        prompt_id = new_id()
        prompt_routes[(run_id, prompt_id)] = task_update.task_id
        ui.emit_prompt(run_id, prompt_id, task_update.question)

def handle_user_response(run_id, prompt_id, answer):
    task_id = prompt_routes[(run_id, prompt_id)]
    a2a.send(task_id, answer)
```

This approach keeps the UI experience linear and conversational while preserving the correct continuation semantics inside the agentic system.

#### Interaction with retries and timeouts

One subtle integration issue is that agent frameworks often treat long delays as failures or trigger retries. If a sub-agent is legitimately waiting for human input, that waiting period must not be confused with a hung tool or a transient error. In practice, this means treating “input required” as an explicit state that suppresses retries and timeouts until the user responds.

### References

1. Model Context Protocol Contributors. *Tools*. Model Context Protocol Specification, 2025. [https://modelcontextprotocol.io/specification/2025-06-18/server/tools](https://modelcontextprotocol.io/specification/2025-06-18/server/tools)
2. Model Context Protocol Contributors. *Cancellation*. Model Context Protocol Specification, 2025. [https://modelcontextprotocol.io/specification/2025-06-18/basic/utilities/cancellation](https://modelcontextprotocol.io/specification/2025-06-18/basic/utilities/cancellation)
3. A2A Protocol Contributors. *Task Lifecycle and States*. Agent-to-Agent Protocol Documentation, 2025. [https://agent2agent.info/docs/concepts/task/](https://agent2agent.info/docs/concepts/task/)
4. Pydantic Services Inc. *ModelRetry and retry semantics*. Pydantic-AI Documentation, 2024–2025. [https://ai.pydantic.dev/api/exceptions/](https://ai.pydantic.dev/api/exceptions/)
5. Pydantic Services Inc. *FastA2A*. Pydantic-AI Documentation, 2024–2025. [https://ai.pydantic.dev/api/fasta2a/](https://ai.pydantic.dev/api/fasta2a/)
6. FastMCP Contributors. *Server error handling and timeouts*. FastMCP Documentation, 2025. [https://gofastmcp.com/python-sdk/fastmcp-server-middleware-error_handling](https://gofastmcp.com/python-sdk/fastmcp-server-middleware-error_handling)
7. AG-UI Contributors. *Events and run lifecycle*. AG-UI Documentation, 2025. [https://docs.ag-ui.com/concepts/events](https://docs.ag-ui.com/concepts/events)
