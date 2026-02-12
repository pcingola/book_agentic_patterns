# Plan: Event-driven wait for background work

## Problem

The orchestrator has multiple sources of background work (broker tasks, A2A, sub-agents). The LLM needs results from them. The current mechanism is `check_tasks`, which polls the broker in a non-blocking busy loop -- unbounded LLM round-trips with no new information, wasting tokens and latency. It also only covers one source (the broker).

## Solution

### Unified event

`OrchestratorAgent` owns a single `asyncio.Event` (`_activity`). Any background source signals it when it has new results -- broker tasks, A2A responses, anything future. The orchestrator does not care who signaled.

### `wait` tool

Replaces `check_tasks`. Source-agnostic. Blocks on the event until something happens. Returns results from ALL sources that completed. Every call returns actionable information.

The LLM controls how long to wait via a `timeout` parameter. When timeout fires, `wait` returns whatever status exists (some completed, some still running). The LLM decides what to do -- report partial results, wait more, or give up.

### Event arrives, nobody waiting

`asyncio.Event.set()` is sticky -- the event stays set until explicitly cleared. If a task completes before the LLM calls `wait`, the event stays set. When `wait` is called later, the clear/re-check pattern finds the completed task in the store and returns immediately. No events are lost.

Two paths for results to reach the LLM:

1. Within a turn: LLM calls `wait`, gets results (immediately if already available, or blocks until event).
2. Between turns: `_inject_completed_tasks` picks up anything that completed between `run()` calls.

### Race condition safety

The `wait` tool follows this pattern:

```
clear event
re-check store (store is updated BEFORE event is set, so this catches completions that happened between clear and await)
if any newly terminal: return immediately
await event (blocks until signaled)
collect and return all results
```

All orderings of clear/set/check are safe because the store is always updated before the event is signaled.

### Timeouts

Each source has its own execution timeout (worker timeout, A2A client timeout). When a source times out, it marks its work as FAILED -- that is a real event that wakes up `wait`.

A safety-net timeout on the event wait itself catches catastrophic failures (all A2A servers killed, bugs, missing source-level timeouts). When it fires, `wait` returns current status so the LLM can act.

## Changes

### `core/agents/orchestrator.py`

- Add `_activity: asyncio.Event` to `__init__`.
- Pass `_activity` to the broker in `_add_task_tools`.
- Replace `_make_check_tasks_tool` with `_make_wait_tool`. The `wait` tool accepts `timeout: int` (seconds, with a default). It clears the event, re-checks the store, awaits the event if needed, then collects results from all sources.
- Update docstring (check_tasks -> wait).

### `core/tasks/broker.py`

- Accept optional `activity: asyncio.Event` in `__init__`.
- Signal it in `_run_and_notify` finally block (after task reaches terminal state).

### `prompts/the_complete_agent/agent_full.md`

- Replace `check_tasks` with `wait` in the "Background tasks" section.
- Clarify that `wait` blocks until results are ready (not a polling tool).
- Update the workflow step that referenced `check_tasks`.

### `examples/the_complete_agent/example_agent_full.ipynb`

- Update markdown cells: replace references to `check_tasks` with `wait`.
- Update the notebook description (cell 0) and Turn 2 description.
