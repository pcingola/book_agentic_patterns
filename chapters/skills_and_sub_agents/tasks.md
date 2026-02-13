## Tasks

Sub-agents are fire-and-forget: the coordinator calls, awaits, and moves on. This works for short tasks but breaks down when work is long-running, needs mid-flight observation, or should survive process restarts. The task lifecycle wraps sub-agent execution with durable state, observation channels, and explicit control.

#### State Machine

A task moves through a small set of states: pending, running, completed, failed, input_required, cancelled. Terminal states (completed, failed, cancelled) end the lifecycle. No transitions out of a terminal state are allowed. The `input_required` state is non-terminal -- it signals that the worker needs external input before it can continue, and the task resumes once that input is provided.

```
pending --> running --> completed
                   \-> failed
                   \-> input_required --> running
         \-> cancelled
```

The state machine is the contract between submission and execution. The submitter does not need to know how work happens internally -- it only needs to observe which state the task is in. This decoupling is what makes the pattern useful: any consumer that understands the state machine can interact with the lifecycle, regardless of what the worker does internally.

#### Submission and Execution

The key design decision is decoupling who submits work from who executes it. A broker receives tasks and places them in a queue. A worker picks tasks from the queue and runs them. This separation means the submitter does not need a reference to the executor, and the executor does not need to know who submitted the work.

The worker is a sub-agent executor: it reads task metadata (system prompt, model configuration), creates a sub-agent, runs it, and writes the result back to storage. The worker itself is stateless -- all durable state lives in external storage. If the worker crashes, a new one can pick up where the old one left off because the task's state is persisted.

```
submitter -> broker -> store -> worker -> sub-agent
                 ^                  |
                 |------ result ----|
```

#### Observation

Once a task is submitted, the submitter needs to know what happens to it. Three complementary mechanisms serve different use cases.

**Polling** is the simplest: ask for the current state at any time. It requires no infrastructure beyond the storage layer. The consumer decides when to check and how often. Polling is robust and works across process boundaries, but introduces latency proportional to the polling interval.

**Streaming** subscribes to events as they happen. The consumer iterates over an event stream and receives state changes, progress updates, and log messages as the worker produces them. Streaming provides low latency but requires the consumer to maintain a connection for the duration of the task.

**Notification** registers callbacks for specific state changes. The consumer says "call me when this task completes or fails" and the broker fires the callback when the condition is met. Push-based observation is useful when the consumer has other work to do and does not want to poll or hold a stream open.

These are not alternatives -- they serve different use cases and can coexist within the same system. A UI might stream events for real-time display, while a monitoring system polls periodically for health checks, and an alerting system uses notifications for failures.

#### Storage and Persistence

Task state must outlive the process that created it. If the broker restarts, it should find all pending and running tasks and resume dispatch. If a worker crashes mid-execution, the task should be recoverable.

A storage abstraction decouples the lifecycle from any specific backend. The contract is small: create a task, read a task, update its state, list tasks by state, and append events. A JSON file implementation works for development and single-machine scenarios. A database-backed implementation works for production with multiple workers.

Persistence enables three things beyond basic durability. Recovery after failure: a restarted broker can scan for tasks stuck in `running` state and re-dispatch them. Replay for auditing: the full event history of a task is preserved and can be inspected after the fact. Coordination across workers: multiple workers can compete for pending tasks through the storage layer without direct communication.

#### Connection to Sub-Agents and A2A

The worker IS a sub-agent executor with lifecycle management around it. It reads metadata, calls `get_agent()` and `run_agent()`, and writes results back -- exactly the dynamic sub-agent pattern from the previous section, wrapped in state tracking and persistence.

The same concepts appear in A2A as protocol-level guarantees. A2A defines task states, streaming via Server-Sent Events, push notifications via webhooks, and task storage as protocol requirements. The `core/tasks/` module is the local implementation of those ideas -- the same architecture applied within a single process instead of across a network.
