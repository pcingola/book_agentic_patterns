# Tasks

## The Generic Concept

A task is a unit of work with a managed lifecycle. In agentic systems, tasks wrap sub-agent execution with durable state, observation channels, and explicit control. The pattern decouples submission from execution: a submitter creates a task, a broker dispatches it, and a worker executes it. The submitter never needs to know how work happens internally -- it only observes which state the task is in.

The core abstraction is a state machine. A task transitions through states (pending, running, completed, failed, input_required, cancelled), and terminal states end the lifecycle. This state machine is the contract between all participants: submitters, brokers, workers, and observers.

Three properties distinguish tasks from direct sub-agent calls:

**Durability.** Task state is persisted externally. If a worker crashes, the task remains in storage and can be re-dispatched. Direct sub-agent calls lose their state when the caller's process dies.

**Observability.** Tasks support multiple observation mechanisms: polling (ask for current state), streaming (subscribe to events), and notification (register callbacks for state changes). Direct sub-agent calls are opaque until they return.

**Control.** Tasks can be cancelled, paused (input_required), and resumed. Direct sub-agent calls are fire-and-forget.

These ideas appear across many systems. Message queues (Celery, SQS), workflow engines (Temporal, Airflow), and agent protocols (A2A) all implement variations of the same state-machine-plus-broker architecture. The A2A protocol formalizes tasks as a first-class concept with states, streaming via Server-Sent Events, push notifications via webhooks, and task storage as protocol requirements.

## Tasks in Claude Code

Claude Code popularized task management as a built-in agent primitive. Its task system (TaskCreate, TaskUpdate, TaskGet, TaskList) provides dependency-aware orchestration where tasks can block other tasks, persist across sessions, and be assigned to parallel sub-agents. Tasks are stored as JSON files in `~/.claude/tasks/` and can be shared across sessions via the `CLAUDE_CODE_TASK_LIST_ID` environment variable. The key innovation is making task dependencies a first-class concept: a task cannot start until all its blockers are completed, which prevents agents from working out of order.

## Our Implementation

The `core/tasks/` module implements the generic task concept for this project. It has five files:

`state.py` defines the `TaskState` enum (PENDING, RUNNING, COMPLETED, FAILED, INPUT_REQUIRED, CANCELLED) and the `TERMINAL_STATES` set.

`models.py` defines `Task` (input, result, error, events, metadata) and `TaskEvent` (state transitions, progress, logs). The metadata dictionary carries sub-agent configuration (system_prompt, config_name, agent_name).

`store.py` defines the `TaskStore` abstract interface (create, get, update_state, list_by_state, next_pending, add_event) with two implementations: `TaskStoreJson` (one JSON file per task, for development) and `TaskStoreMemory` (in-memory dict, for notebooks).

`worker.py` defines `Worker`, which executes tasks by running sub-agents. It supports both bare agents (via `get_agent()`/`run_agent()`) and `AgentSpec`-based execution (via `OrchestratorAgent`). The worker emits progress and log events via a node hook so observers can track sub-agent activity in real time.

`broker.py` defines `TaskBroker`, the coordination layer. It is an async context manager that starts a background dispatch loop on entry and cancels it on exit. It exposes five observation methods: `poll()`, `wait()`, `stream()`, `cancel()`, and `notify()`. The broker accepts an optional `asyncio.Event` for event-driven signaling when tasks reach terminal states.

The design follows the generic pattern exactly: submission is decoupled from execution, state lives in external storage, and observation is available through multiple mechanisms. Swapping `TaskStoreJson` for a database-backed implementation would support production use with multiple workers without changing any other code.
