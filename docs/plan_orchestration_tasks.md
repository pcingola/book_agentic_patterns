# Plan: Unified Orchestration via TaskBroker

Deliverable: write this plan to `docs/plan_orchestration_tasks.md`, then implement it.

## Context

Agent V5 (The Full Agent) adds async task execution to the monolithic agent. The original plan adds task tools as simple wrappers. But the current `delegate` tool in OrchestratorAgent and the TaskBroker are two independent execution paths for sub-agent work. A delegation is just a "single-item task." Both should flow through the TaskBroker, giving us concurrent execution, progress events, error handling, and cancellation propagation.

## The Two Current Paths

**Path 1 -- delegate tool** (orchestrator.py:205-220): Inline `OrchestratorAgent` creation, blocks until done, no events, no cancellation, no visibility.

**Path 2 -- TaskBroker** (tasks/broker.py): Async queue with events/cancellation, but Worker uses bare `get_agent()` (no tools, skills, or sub-agents) and dispatch is sequential (one task at a time).

## Unified Design

### Execution Model

All sub-agent work goes through the TaskBroker. The broker holds AgentSpecs in memory. The Worker resolves specs and runs sub-agents via OrchestratorAgent.

```
delegate("sql_analyst", "query books")
  -> broker.submit("query books", agent_name="sql_analyst")
  -> dispatch loop picks task, spawns asyncio.Task
  -> Worker resolves AgentSpec for "sql_analyst"
  -> Worker creates OrchestratorAgent(spec), runs it
  -> on_node hook emits PROGRESS events to broker
  -> COMPLETED -> delegate returns result string

submit_task("sql_analyst", "query books")
  -> broker.submit(...), returns task_id immediately
  -> agent continues with other tool calls
  -> check_tasks() polls status + progress events
  -> between turns: orchestrator prepends completed results to next prompt
```

### Agent-Facing Tools

Created by OrchestratorAgent when `sub_agents` are present:

- **`delegate(agent_name, prompt)`** -- submit + wait. Same interface as today, but routed through broker.
- **`submit_task(agent_name, prompt)`** -- fire-and-forget. Returns task_id.
- **`check_tasks()`** -- returns status of all tasks with recent progress events.

### Progress Events

Worker creates OrchestratorAgent with `on_node` hook that emits TaskEvents to the store:
- ToolCallPart -> PROGRESS event with tool name and arg preview
- TextPart -> LOG event with reasoning snippet

Visible via `check_tasks()` and between-turn injection.

### Between-Turn Injection

After each `run()`, OrchestratorAgent checks broker for tasks completed since last check. Before next `run()`, prepends to the prompt:

```
[BACKGROUND TASK COMPLETED: sql_analyst (task_id=abc123)]
Result: The bookstore has 150 books across 8 genres...

<user's actual prompt>
```

### Cancellation

```
User interrupts -> OrchestratorAgent.__aexit__()
  -> broker.cancel_all()
  -> each running asyncio.Task cancelled
  -> Worker catches CancelledError, sets task CANCELLED
  -> broker __aexit__ stops dispatch loop
```

### Error Handling

Sub-agent exception -> Worker catches it, marks task FAILED with error message -> `delegate` returns `"Delegation failed: {error}"` -> `check_tasks` reports the failure. Main agent decides what to do.

### Usage Tracking

Worker stores usage in a COMPLETED event's payload. `delegate` extracts it and calls `ctx.usage.incr()`.

## Files to Change (in order)

### Phase 1: In-Memory Store + Concurrent Dispatch

**`core/tasks/store.py`** -- Add `TaskStoreMemory` (dict-backed, no filesystem). Same ABC, simpler for notebooks.

**`core/tasks/broker.py`**:
- Add `_agent_specs: dict[str, AgentSpec]` and `register_agents(specs)` method
- Add `_running: dict[str, asyncio.Task]` for tracking running work
- `_dispatch_loop`: `asyncio.create_task()` instead of `await` (concurrent dispatch)
- New `_run_and_notify(task_id)` wrapper: runs worker, fires callbacks, handles CancelledError
- `cancel()`: also cancel the asyncio.Task if running
- Add `cancel_all()`: cancel all running tasks

**`core/tasks/worker.py`**:
- Accept `agent_specs: dict[str, AgentSpec]` at init (passed from broker)
- When task has `agent_name` in metadata, resolve spec -> OrchestratorAgent
- Fallback to `get_agent()`/`run_agent()` when no spec (backward compat)
- `_make_node_hook(task_id)`: emits PROGRESS/LOG events to store
- Store usage in COMPLETED event payload

### Phase 2: OrchestratorAgent Integration

**`core/agents/orchestrator.py`**:
- In `__aenter__`: when `sub_agents` present, create `TaskBroker(store=TaskStoreMemory())`, register specs, enter broker context (starts dispatch loop)
- Replace inline `delegate` closure with broker-backed version (submit + wait)
- Add `submit_task(agent_name, prompt)` tool (submit, return task_id)
- Add `check_tasks()` tool (poll all submitted tasks, return formatted status with events)
- Track `_submitted_task_ids` and `_reported_task_ids` for between-turn injection
- In `run()`: after iteration completes, check for newly completed tasks
- Add `_inject_completed_tasks(prompt)` that prepends completion info to next prompt
- In `__aexit__`: `broker.cancel_all()`, exit broker context

### Phase 3: V5 Prompt and Notebook

**`prompts/the_complete_agent/agent_full.md`** -- Extends coordinator prompt with async tasks section explaining submit_task/check_tasks and when to use them vs delegate.

**`agentic_patterns/examples/the_complete_agent/example_agent_full.ipynb`** -- Demo with:
- Turn 1: Agent uses delegate (synchronous) for a SQL query
- Turn 2: Agent uses submit_task for parallel work, does direct work, then check_tasks

### Phase 4: Update Plan Doc

**`docs/plan_monolithic_agents.md`** -- Mark V5 as done, update tool count and description.

## Backward Compatibility

- Worker fallback to `get_agent()`/`run_agent()` when no AgentSpec (existing tests pass)
- TaskBroker API unchanged (submit/poll/stream/wait/cancel still work as before)
- OrchestratorAgent without sub_agents: no broker created, works exactly as before
- AgentSpec model: no changes

## What Does NOT Change

- AgentSpec, TaskState, TaskEvent, EventType models
- Sub-agent specs (data_analysis.py, sql.py, vocabulary.py)
- Agent tools (file, sandbox, todo, skills, format_conversion)
- Prompt template system
- The V3 (Skilled) and V4 (Coordinator) notebooks

## Verification

1. Existing tests pass: `scripts/test_unit.sh`
2. V4 coordinator notebook still works (delegate now goes through broker, same behavior)
3. V5 notebook works: both delegate and submit_task/check_tasks patterns
4. Cancellation: interrupt during task execution -> all tasks cleaned up
