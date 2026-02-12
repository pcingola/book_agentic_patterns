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
    COMPLETED = "completed"
    FAILED = "failed"
    INPUT_REQUIRED = "input-required"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
```

`TIMEOUT` is a client-side addition. The protocol itself does not define a timeout state, but real-world clients need a bounded wait.


### Observation Mechanisms

Three complementary mechanisms make task state observable. **Streaming** provides real-time push-based updates as typed events (status transitions, artifact chunks, messages). **Polling** is a simple, robust baseline: any client can query a task's current state at any time using its task ID, guaranteeing eventual visibility even across network interruptions. **Push notifications** extend observability to external systems via webhooks, enabling event-driven architectures without persistent connections.

These are protocol-level guarantees, not optional features. The [details section](./details.md) covers their wire-level format, `StreamResponse` envelope structure, chunked artifact semantics, and idempotency requirements.


### Execution Architecture

A2A servers typically decompose into three layers that separate protocol handling from task execution.

**Storage** persists task state, artifacts, and history so that tasks survive process restarts and can be re-queried or re-streamed. The core library's `core/tasks/` module defines `TaskStore` as an abstract interface with two implementations: `TaskStoreJson` persists one JSON file per task in `DATA_DIR/tasks/` for single-node deployments, while `TaskStoreMemory` uses an in-memory dictionary for notebooks and tests.

**Workers** are stateless executors that pick up tasks, run the agent logic, and emit progress updates. The core library's `Worker` class executes tasks by running agents via `OrchestratorAgent`, emits `PROGRESS` and `LOG` events for background tracking, and handles `CancelledError` for cooperative cancellation. Because all durable state lives in the store, workers can scale horizontally and restart safely.

**The broker** coordinates between task producers and workers. `TaskBroker` manages submission, observation (poll, stream, wait, cancel), and dispatch. It accepts an optional `asyncio.Event` for event-driven signaling when tasks reach terminal states, replacing polling-based coordination. An event-driven wait pattern using a clear-then-check sequence prevents race conditions between task completion and the coordinator checking for results.

This architecture mirrors established distributed systems patterns. The PydanticAI ecosystem reflects this directly: `agent.to_a2a()` creates the HTTP ingress layer, while the broker and worker handle scheduling and execution internally.


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

Tasks, observation mechanisms, storage, workers, and brokers form a coherent execution model. Tasks are created once, stored durably, executed by interchangeable workers, coordinated by a broker, and observed through streaming, polling, or push notifications. On the client side, `A2AClientExtended` encapsulates the retry, timeout, and cancellation logic needed for reliable communication. This layered design supports long-running workflows and enterprise-grade reliability while keeping each component independently testable and replaceable.
