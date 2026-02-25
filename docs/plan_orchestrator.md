# OrchestratorAgent Redesign

## Core Concept

The OrchestratorAgent is a planner. It manages a to-do list (a DAG of tasks) and decides how each task gets executed. Tasks are the central abstraction for planning and coordination.

## Six Capabilities

The OrchestratorAgent wires up six capabilities from the AgentSpec. All six remain in the redesign.

**Direct tools** (the agent uses these itself while working on any task):
- **Tools**: Explicit Python functions from the spec.
- **MCP**: Tools exposed by MCP servers.
- **Skills**: Discoverable capabilities with progressive disclosure. Three tools: `activate_skill` (load instructions into context), `run_skill_script` (execute bundled script in sandbox), `read_skill_resource` (read reference/asset files). Auto-discovered from SKILLS_DIR when none provided.

**Delegation and planning**:
- **Sub-agents**: Local agents defined via AgentSpec.
- **A2A**: Remote agents accessible over the network, with their own task lifecycle (`send_and_observe`: poll, retry with backoff, timeout with auto-cancel, INPUT_REQUIRED).
- **Tasks**: The agent's to-do list. Each task has a goal, optional agent assignment, optional dependencies, and a state. Tasks form a DAG.

All six are complementary and can be used simultaneously. Tools, MCP, and skills are orthogonal to the task layer -- the agent (or its sub-agents) uses them directly while working.

## Tasks as a To-Do List

A task is a work item in the agent's plan. Each task carries:
- **goal**: What needs to be done.
- **agent** (optional): Who should do it (a sub-agent or A2A agent name).
- **depends_on**: List of task IDs that must complete first.

The agent creates the plan upfront -- tasks with goals, agent assignments, and dependencies. The DAG encodes the execution order.

For each task, the agent decides the execution strategy:
- **Do it itself**: The agent tackles the task directly, using its tools/MCP/skills.
- **Delegate to a sub-agent**: The worker runs it via OrchestratorAgent with the registered AgentSpec.
- **Send via A2A**: The worker runs it via `A2AClientExtended.send_and_observe()` with poll/retry/timeout.

## The Agent Stays in the Loop

The agent is not just a planner that creates tasks and walks away. It is actively involved throughout:

- When dependencies complete, the **agent** sees the results and decides what context to pass to the dependent task. The orchestrator does not auto-inject anything.
- When a task fails, the agent sees the error and decides: retry, reassign, do it itself, skip, or replan.
- The agent can create new tasks mid-execution based on results it sees.
- The agent can tackle tasks itself at any point.

The orchestrator's job is to dispatch ready tasks, wait when the agent is idle, and bring the agent back in when there are results to review or decisions to make.

## No Broker

The broker is unnecessary indirection. The orchestrator owns the Tasks collection and the execution loop directly. `Tasks.next_pending()` handles dependency resolution. The worker handles execution. No broker in between.

## The run() Loop

The loop has four clear steps that repeat: collect results, consult the agent, dispatch work, wait.

```
async def run(prompt, timeout):
    deadline = now + timeout
    running: dict[str, asyncio.Task] = {}

    consult_agent(prompt)

    while not is_done(running):
        check_timeout(deadline, running)
        newly_done = collect_finished(running)
        if newly_done or needs_agent_attention():
            consult_agent(format_task_status(tasks))
        dispatch_ready(running)
        if running:
            await wait_for_progress(running, deadline)
```

### consult_agent(prompt)

Run the PydanticAI agent for one turn via `self._agent.iter(prompt, message_history=self._message_history)`. The agent sees the prompt, calls tools (submit, activate_skill, etc.), and produces a text response. Message history accumulates across calls. The agent creates/modifies tasks, tackles tasks itself, handles failures, fills in dependent tasks with context from completed results.

### collect_finished(running) -> list[str]

Reap completed `asyncio.Task`s from `running`. Return their task IDs. Exceptions are swallowed (the worker already marked the task FAILED).

### needs_agent_attention() -> bool

True when pending tasks exist but can't be dispatched -- either they have no assigned agent (the agent should do them itself or assign one), or tasks have failed and the agent needs to decide what to do.

### dispatch_ready(running)

Walk `tasks.next_pending()`. For each ready task with an assigned agent:
- Sub-agent name -> `asyncio.create_task(worker.execute(task.id))`
- A2A agent name -> `asyncio.create_task(execute_a2a(task))`

Stop when no more ready tasks with assigned agents remain.

### wait_for_progress(running, deadline)

```
await asyncio.wait(running.values(), timeout=deadline - now, return_when=FIRST_COMPLETED)
```

Block until at least one async task finishes or the deadline approaches.

### check_timeout(deadline, running)

If past deadline: cancel all running `asyncio.Task`s, mark remaining PENDING tasks as CANCELLED, raise `TimeoutError`.

### is_done(running) -> bool

True when `running` is empty and no PENDING tasks remain.

### A2A Execution

```
async def execute_a2a(task):
    tasks.update_state(task.id, RUNNING)

    client = a2a_clients[task.metadata["agent_name"]]
    status, result = await client.send_and_observe(task.input)

    # send_and_observe handles: poll loop, retry with backoff,
    # timeout with auto-cancel, INPUT_REQUIRED
    # Network errors during polling -> retry, not failure

    match status:
        case COMPLETED:
            text = extract_text(result)
            tasks.update_state(task.id, COMPLETED, result=text)
        case FAILED:
            tasks.update_state(task.id, FAILED, error=str(result))
        case TIMEOUT:
            tasks.update_state(task.id, FAILED, error="A2A timeout")
        case INPUT_REQUIRED:
            tasks.update_state(task.id, INPUT_REQUIRED)
        case CANCELLED:
            tasks.update_state(task.id, CANCELLED)
```

### Key Properties

- **Agent stays in control**: Every time async work finishes, the agent sees results and decides what to do next. The orchestrator never injects context or makes decisions on the agent's behalf.
- **Parallel dispatch**: All ready tasks with assigned agents are dispatched concurrently.
- **Auto-wait**: The orchestrator blocks on `asyncio.wait(FIRST_COMPLETED)` only when there's nothing else to do.
- **Agent handles failures**: No automatic cascade. The agent sees errors and decides.
- **Timeout**: A global deadline covers the entire run. On expiry, everything is cancelled cleanly.
- **on_update fires on every state change**: `tasks.update_state()` triggers the hook, so the to-do list display stays current.

## on_update Hook

Every task state change fires the `on_update` callback on the Tasks collection. This works uniformly for all execution mechanisms -- sub-agent completion, A2A status poll updates, or the agent completing a task itself.

## Task IDs

Sequential integers (1, 2, 3, ...) for readability. The LLM uses these IDs in `depends_on` references.

## To-Do List Display

Tasks render as a checklist:

```
  [x] 1. (researcher) Research particle physics discoveries...
  [x] 2. (researcher) Research cosmology discoveries...
  [~] 3. (writer) Write article connecting both fields...
       depends on: 1, 2
```

Markers: `[ ]` pending, `[~]` running, `[x]` completed, `[!]` failed, `[-]` cancelled.

## What Changes from Current Design

- TaskBroker is removed entirely. The orchestrator owns the loop.
- `delegate`, `submit_task`, `wait`, and per-A2A delegation tools collapse into one `submit` tool.
- `run()` becomes a loop: agent plans, orchestrator dispatches, agent reviews results, repeat.
- Worker gains an A2A execution path (via `send_and_observe`) alongside the local sub-agent path.
- Agent catalog merges sub_agents and a2a_clients into one flat list in the system prompt.
- No automatic cascade failure -- agent is consulted on every failure.
- Agent decides what context goes into each task, not the orchestrator.

## What Stays the Same

- Task model, TaskState, state machine, on_update hook.
- Tasks collection with `next_pending()` for dependency resolution.
- Worker for sub-agent execution (local OrchestratorAgent).
- TaskStoreMemory / TaskStoreJson for persistence.
- AgentSpec as the declarative spec.
- Tools, MCP, and skills -- fully unchanged.
- `__aenter__` still wires up all six capabilities.
- A2AClientExtended with its retry, timeout, poll, and cancellation behavior.
- A2A server side (to_a2a, AuthSessionMiddleware) is unaffected.
