# Task Lifecycle Implementation Plan

## Overview

Implement the task lifecycle system described in `chapters/a2a/tasks.md` as a new `core/tasks/` module. The design borrows directly from the sub-agents pattern: workers execute tasks as sub-agents, and the broker coordinates them like a coordinator with added lifecycle management (persistence, observation, cancellation).


## Module: `agentic_patterns/core/tasks/`

### `state.py` -- Task State (~15 lines)

`TaskState(str, Enum)` with states: PENDING, RUNNING, COMPLETED, FAILED, INPUT_REQUIRED, CANCELLED. A `TERMINAL_STATES` set for lifecycle checks.


### `models.py` -- Data Models (~50 lines)

Two Pydantic models.

`Task`: id (uuid), state, input text, result (str | None), error (str | None), events list, created_at, updated_at, metadata dict. The metadata dict carries agent configuration (system_prompt, model_name) so the worker knows how to execute the task.

`TaskEvent`: task_id, event_type (state_change | progress | log), payload dict, timestamp. Records state transitions and progress for observation.


### `store.py` -- Task Storage (~80 lines)

`TaskStore`: abstract base class defining the storage contract.

Methods: `create(task)`, `get(task_id)`, `update_state(task_id, state, result?, error?)`, `list_by_state(state)`, `add_event(task_id, event)`, `next_pending()`.

`TaskStoreJson`: JSON file-backed implementation. One JSON file per task under a configurable directory (default: `data/tasks/`). Uses pathlib for all file operations, asyncio.Lock for safe concurrent access. Each task file is `{task_id}.json`. Provides real persistence across restarts without external dependencies.


### `worker.py` -- Task Executor (~50 lines)

`Worker` executes individual tasks by running sub-agents. This is the direct borrowing from the dynamic sub-agent pattern:

1. Read system_prompt and model_name from `task.metadata`
2. Create agent via `get_agent(system_prompt=..., model_name=...)`
3. Run agent via `run_agent(agent, task.input)`
4. Write result or error back to the store

Worker is stateless with respect to task identity -- all durable state lives in the store. This mirrors the chapter's description and allows horizontal scaling.


### `broker.py` -- Coordination Hub (~90 lines)

`TaskBroker` is the coordination layer exposed as an async context manager (matches `OrchestratorAgent` pattern).

Submission: `submit(input, **metadata) -> str` creates a Task, persists it, returns task_id.

Observation:
- `poll(task_id) -> Task` returns current task state (baseline mechanism).
- `stream(task_id) -> AsyncIterator[TaskEvent]` yields events as they arrive (push-based streaming).
- `wait(task_id) -> Task` polls until terminal state (convenience wrapper).
- `notify(task_id, states, callback)` registers an async callable for specific state changes (push notification concept).

Control: `cancel(task_id)` cancels a running or pending task.

Background loop: an asyncio task that picks up pending tasks from the store and dispatches them to the worker, FIFO order.


## Connection to Sub-Agents

| Sub-Agent Pattern | Task Lifecycle Equivalent |
|---|---|
| `run_sub_agent(prompt, system_prompt)` | `broker.submit(input=prompt, system_prompt=...)` |
| Awaiting result inline | `broker.poll(task_id)` or `broker.wait(task_id)` |
| Fire-and-forget execution | Observable via `broker.stream(task_id)` |
| Coordinator decides what to run | Broker dispatches to workers |
| Result returned to tool caller | Result persisted in JSON store, observable via any channel |


## Not Included (intentionally)

- No multiple worker types or routing logic (one worker, FIFO dispatch)
- No HTTP-based push notifications (async callables teach the concept)
- No integration changes to the existing `core/a2a/` module
