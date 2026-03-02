## Task Lifecycle in Agent-to-Agent (A2A) Systems

In A2A systems, a task is a durable, observable unit of work whose lifecycle is decoupled from synchronous execution through explicit state management, multiple observation channels, and a layered execution architecture.


### Asynchronous Execution as a First-Class Concept

A2A tasks are explicitly designed to be asynchronous. Once a task is created, the initiating agent does not assume immediate completion. Instead, progress and results are exposed incrementally through well-defined observation mechanisms. This makes tasks suitable for long-running reasoning, external tool calls, delegation chains, and human approval steps.

Asynchrony in A2A is not an implementation detail but a protocol-level guarantee: every task can be observed, resumed, or completed independently of the original request-response channel.


### Task States

Tasks progress through well-defined states: `working` (in progress), `completed` (terminal), `failed` (terminal), `canceled` (terminal), `rejected` (terminal), and `input-required` (the agent needs additional information to proceed). A special `auth-required` state signals authentication issues. The full state machine and transition semantics are covered in [A2A in Detail](./details.md).

The core library defines a `TaskStatus` enum (`core/a2a/client.py`) that maps protocol states to client-side outcomes:

```python
class TaskStatus(str, Enum):
    AUTH_REQUIRED = "auth-required"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"
    INPUT_REQUIRED = "input-required"
    TIMEOUT = "timeout"
```

`AUTH_REQUIRED` maps directly to the protocol's `auth-required` state, signaling that the agent needs authentication before proceeding. `TIMEOUT` is a client-side addition -- the protocol itself does not define a timeout state, but real-world clients need a bounded wait.


### Observation Mechanisms

Three complementary mechanisms make task state observable. **Streaming** provides real-time push-based updates as typed events (status transitions, artifact chunks, messages). **Polling** is a simple, robust baseline: any client can query a task's current state at any time using its task ID, guaranteeing eventual visibility even across network interruptions. **Push notifications** extend observability to external systems via webhooks, enabling event-driven architectures without persistent connections.

These are protocol-level guarantees, not optional features. The [details section](./details.md) covers their wire-level format, `StreamResponse` envelope structure, chunked artifact semantics, and idempotency requirements.


### Execution Architecture

A2A servers are built using PydanticAI's `agent.to_a2a()`, which creates a complete ASGI application that handles protocol ingress, task state management, agent execution, and result delivery. The server-side lifecycle -- receiving requests, running the agent, tracking state transitions, and emitting streaming updates -- is handled internally by the framework.

```python
from agentic_patterns.agents.vocabulary import get_agent
agent = get_agent()
app = agent.to_a2a(name="vocabulary", description="Resolves vocabulary terms", ...)
```

On the client side, the `AgentRunner` in `core/agents/orchestrator/` provides a unified interface for launching both local sub-agents and remote A2A agents. When an `OrchestratorAgent` delegates to a remote agent, the runner uses `A2AClientExtended` to send the request, poll for results, and map A2A protocol states to `AgentStatus` values (`RUNNING`, `COMPLETED`, `FAILED`, `INPUT_REQUIRED`, `CANCELLED`, `TIMEOUT`). From the orchestrator's perspective, local and remote agents look identical -- the same `task_launch`, `task_output`, and `task_stop` tools work for both.

For local task coordination (planning, dependency tracking, work assignment), the `core/tasks/` module provides `TaskList` -- a lightweight, file-backed storage layer. `TaskList` is separate from A2A's protocol-level task management; it handles the "what needs to be done and in what order" coordination within a single agent hierarchy, while A2A handles the "how agents communicate across network boundaries" concern.


### Client-Side Resilience

Reliable A2A communication requires handling network failures, timeouts, and cancellation on the client side. The core library's `A2AClientExtended` (`core/a2a/client.py`) wraps the base `fasta2a.A2AClient` with production-ready behavior:

**Retry with exponential backoff.** Transient `ConnectionError` and `TimeoutError` on both sends and polls are retried with configurable delay and maximum attempts.

**Timeout with auto-cancel.** A configurable deadline bounds the total wait time. When exceeded, the client cancels the remote task before returning a `TIMEOUT` status.

**Cooperative cancellation.** An `is_cancelled` callback is checked on every poll cycle, allowing callers to abort long-running operations gracefully.

**`send_and_observe()`** encapsulates the complete send-then-poll loop and returns a `(TaskStatus, task)` tuple:

```python
from agentic_patterns.core.a2a import A2AClientExtended, A2AClientConfig

client = A2AClientExtended(A2AClientConfig(url="http://billing-agent:8000", timeout=300))
status, task = await client.send_and_observe("Reconcile invoice #4812")
```

Client configuration is loaded from YAML (`config.yaml` under `a2a.clients`) with `${VAR}` environment variable expansion, following the same pattern used by MCP and model configurations elsewhere in the platform.


### Putting It All Together

Tasks, observation mechanisms, and the `to_a2a()` execution layer form a coherent model. Tasks are created once, managed by the A2A server, and observed through streaming, polling, or push notifications. On the client side, `A2AClientExtended` encapsulates the retry, timeout, and cancellation logic needed for reliable communication. The `AgentRunner` unifies local and remote delegation behind the same tool interface. This layered design supports long-running workflows and enterprise-grade reliability while keeping each component independently testable and replaceable.
