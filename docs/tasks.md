# Tasks

A dependency-aware task orchestration system for coordinating complex, multi-step work across agents and sessions.

This specification is compiled from three sources:

- [Tasks announcement](./tasks/tasks_announcement.md): high-level motivation and concepts.
- [Tasks implementation details](./tasks/tasks_details.md): technical deep-dive into the system.
- [Claude Code system prompt definitions](./tasks/tasks_claude_code_system_prompt.md): verbatim tool definitions and behavioral guidance from Claude code's system prompt.


## Motivation

Flat to-do lists break down when work involves dependencies, multiple agents, or spans several sessions. An agent working on step 4 may forget that step 2 was a prerequisite, or start work that depends on something unfinished. Context gets lost as conversations grow.

Tasks solve this by introducing a dependency-aware orchestration layer. Tasks can block other tasks, are persisted to the filesystem so multiple agents or sessions can collaborate on them, and support ownership for parallel delegation.

IMPORTANT: Tasks definition and orchestration are separate (but complementary) layers.

Nomenclature: `SYSTEM_PROMPT` indicates these are from "Claude code's system prompt", not from the original posts.

## Core Concepts

A **Task** is a unit of work with a subject, description, status, owner, dependency relationships, and arbitrary metadata. Tasks are grouped into a **Task List**, identified by an opaque ID. All agents and sessions sharing the same Task List ID operate on the same set of tasks. When one agent updates a task, that change is broadcasted to all agents currently working on the same list.

Each task is stored as an individual JSON file inside a directory named after the Task List ID:

```
<tasks-root>/<list-id>/
  1.json
  2.json
  3.json
  ...
```

The `<list-id>` is either generated automatically (e.g. a session UUID) for ephemeral use, or set explicitly for persistent, cross-session collaboration.


## Task Schema

Each task is a JSON object with the following fields:

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | Yes (auto) | Unique identifier within the task list (auto-assigned on creation). |
| `subject` | string | Yes | Brief title in imperative form (e.g. "Set up database connection"). |
| `description` | string | Yes | Detailed requirements, context, and acceptance criteria. |
| `status` | string | Yes | Current state: `"pending"`, `"in_progress"`, or `"completed"`. Defaults to `"pending"` on creation. |
| `activeForm` | string | No | Present-continuous label shown while the task is in progress (e.g. "Setting up database connection"). Used by UIs for progress display. |
| `owner` | string | No | Name of the agent assigned to this task. A label for filtering, not an automatic dispatch mechanism. |
| `blocks` | string[] | No | IDs of tasks that cannot start until this task is completed. |
| `blockedBy` | string[] | No | IDs of tasks that must be completed before this task can start. |
| `metadata` | object | No | Arbitrary key/value data. Stored in the task file but not returned in query responses (TaskGet, TaskList). |

Example stored JSON:

```json
{
  "id": "23",
  "subject": "Test metadata functionality",
  "description": "Testing if metadata gets stored and what it does",
  "activeForm": "Testing metadata",
  "owner": "backend-dev",
  "status": "pending",
  "blocks": ["24", "25"],
  "blockedBy": ["1", "2"],
  "metadata": {
    "priority": "high",
    "estimate": "30min",
    "tags": ["test", "experiment"]
  }
}
```


## Task State Machine

A task progresses through three statuses:

```
pending  -->  in_progress  -->  completed
```

A `"deleted"` status can also be supported to permanently remove a task from the list (this is not in the original specification but is a practical addition for implementations).

Rules:
- A task is created with status `"pending"` and no owner.
- A blocked task (one with non-empty `blockedBy` where at least one blocker is not `"completed"`) should not transition to `"in_progress"`.
- When a task is marked `"completed"`, all tasks that list it in their `blockedBy` should re-evaluate whether they are now unblocked (i.e. all their blockers are completed).
- `SYSTEM_PROMPT`: Mark a task as `"in_progress"` BEFORE beginning work on it.
- `SYSTEM_PROMPT`: A task should ONLY be marked `"completed"` when it has been fully accomplished. Never mark a task as completed if: tests are failing, implementation is partial, there are unresolved errors, or required dependencies could not be found.
- `SYSTEM_PROMPT`: After completing a task, add any new follow-up tasks discovered during implementation.
- `SYSTEM_PROMPT`: If a task encounters errors, blockers, or cannot be finished, it should remain `"in_progress"`. The agent should create a new task describing what needs to be resolved, and add it as a blocker to the stuck task. This way, errors are handled through the dependency graph rather than through a dedicated error status.


## The Four Core Tools

The system exposes four tools for agents to manage tasks.

### TaskCreate

Verbatim definition: [TaskCreate](./tasks/tasks_claude_code_system_prompt.md#taskcreate).

Creates a new task in the task list. The task is assigned the next available ID, starts with status `"pending"`, and has no owner. Always provide `activeForm` when creating tasks -- it is displayed to the user while the agent works on the task.

`SYSTEM_PROMPT`: When to use: complex multi-step tasks (3+ steps), non-trivial tasks that require planning, when the user provides multiple tasks, after receiving new instructions that involve several steps.

`SYSTEM_PROMPT`: When not to use: single straightforward task, trivial task that can be completed in fewer than 3 steps, purely conversational or informational requests.

Input:

| Field | Required | Description |
|---|---|---|
| `subject` | Yes | Brief title in imperative form. |
| `description` | Yes | Detailed requirements and context. |
| `activeForm` | No | Present-continuous text for progress display. |
| `metadata` | No | Arbitrary key/value data. |

Example:

```json
{
  "subject": "Set up database connection",
  "description": "Configure PostgreSQL connection pool, create users table",
  "activeForm": "Setting up database connection",
  "metadata": {
    "priority": "high",
    "estimate": "30min"
  }
}
```

### TaskUpdate

Verbatim definition: [TaskUpdate](./tasks/tasks_claude_code_system_prompt.md#taskupdate).

Modifies any aspect of an existing task. All fields except `taskId` are optional; only provided fields are changed. 

`SYSTEM_PROMPT`: Before updating, the agent should read the task's latest state using TaskGet to avoid stale updates.

| Field | Required | Description |
|---|---|---|
| `taskId` | Yes | The ID of the task to update. |
| `status` | No | New status: `"pending"`, `"in_progress"`, `"completed"` (or `"deleted"` if supported). |
| `subject` | No | New title. |
| `description` | No | New description. |
| `activeForm` | No | New progress display text. |
| `owner` | No | Assign to a named agent. |
| `metadata` | No | Keys to merge into existing metadata. Set a key to `null` to delete it. |
| `addBlocks` | No | Task IDs to append to this task's `blocks` list. |
| `addBlockedBy` | No | Task IDs to append to this task's `blockedBy` list. |

Important: `addBlocks` and `addBlockedBy` **append** to the existing arrays -- they do not replace them. Blocked tasks can only become unblocked when the blocking tasks are marked as `"completed"`.

Example:

```json
{
  "taskId": "3",
  "status": "in_progress",
  "owner": "backend-dev",
  "addBlockedBy": ["1", "2"]
}
```

### TaskGet

Verbatim definition: [TaskGet](./tasks/tasks_claude_code_system_prompt.md#taskget).

Retrieves the full details of a single task by ID: subject, description, status, `blocks`, and `blockedBy`.

`SYSTEM_PROMPT`: Use TaskGet to read the full description and context before starting work on a task, to understand its dependencies, and to verify its `blockedBy` list is empty before beginning work. Also use it before calling TaskUpdate, to ensure the task's state is not stale.

Input:

| Field | Required | Description |
|---|---|---|
| `taskId` | Yes | The ID of the task to retrieve. |

### TaskList

Verbatim definition: [TaskList](./tasks/tasks_claude_code_system_prompt.md#tasklist).

Returns a summary of all tasks in the task list. Each entry includes: `id`, `subject`, `status`, `owner`, and `blockedBy`. Useful for discovering available work (tasks that are `"pending"`, unblocked, and unowned). Use TaskGet to retrieve full details for a specific task.

`SYSTEM_PROMPT`: After completing a task, call TaskList to check for newly unblocked work or claim the next available task. When multiple tasks are available, prefer working on them in ID order (lowest ID first), as earlier tasks often set up context for later ones.


## Dependency Management

Dependencies are the central feature of the system. When `addBlockedBy: ["1", "2"]` is set on task #3, it means:

> Task #3 cannot start until tasks #1 AND #2 are both completed.

This is enforced as follows:
- A task with a non-empty `blockedBy` list where at least one blocker has status other than `"completed"` is considered **blocked**.
- When a task is marked `"completed"`, all tasks listing it in their `blockedBy` should be re-evaluated. If all their blockers are now `"completed"`, they become **unblocked** and available for work.
- The `blocks` and `blockedBy` fields are kept in sync bidirectionally: adding task #1 to task #3's `blockedBy` also adds task #3 to task #1's `blocks`.

Example dependency graph:

```
[completed]  #1 Define article topic and angle
[completed]  #2 Assign writer and set deadline
[in_progress] #3 Writer completes first draft
[blocked]    #4 Conduct fact-checking         -- blocked by #3
[blocked]    #5 Perform substantive edit       -- blocked by #3
[blocked]    #6 Writer completes revisions     -- blocked by #4, #5
```

When #3 completes, tasks #4 and #5 automatically become unblocked and available for work. Task #6 remains blocked until both #4 and #5 are completed.


## Orchestration

The Tasks system has two distinct layers: **task management** and **orchestration**.

Task management is what the four tools (TaskCreate, TaskUpdate, TaskGet, TaskList) provide: structured storage, status tracking, and dependency enforcement. This layer is purely data -- it never executes, dispatches, or spawns anything.

Orchestration is what the agent does *on top of* task management: deciding what to work on next, performing the work (directly or via sub-agents), and updating task status accordingly. The original describes the system as *"not just a list -- it's a dependency-aware orchestration layer that understands what blocks what, persists across sessions, and can delegate work to parallel agents"* (details post, "What Makes This Different"). The orchestration capability comes from the combination of dependency enforcement and shared state, not from a built-in dispatch mechanism. Dependency enforcement is what makes this more than a to-do list: *"Task #3 literally cannot begin until #1 and #2 are done"* (details post, "Full Dependency Management"), and when a blocker completes, dependent tasks automatically become available -- *"When #3 completes, tasks #4 and #5 automatically become unblocked and available for work"* (details post, "How Dependencies Work").

### Execution modes

The agent working through a task list decides how to execute each task.

**Direct execution.** The agent performs the work itself. This is the simplest mode -- the agent picks the next available task, does the work, and marks it completed. The original describes this workflow: *"1. Calls TaskList to see all tasks, 2. Filters for tasks where owner matches its name, 3. Calls TaskUpdate to mark task in_progress, 4. Does the work, 5. Calls TaskUpdate to mark task completed"* (details post, "Agent Assignment", Step 3).

**Delegation to sub-agents.** The agent spawns sub-agents to handle tasks. Reasons to delegate include:
- **Parallelism**: multiple independent tasks can be worked simultaneously. The original shows multiple agents *"running at once, all updating the same task list. No conflicts"* (details post, "Parallel Agents").
- **Specialization**: different tasks may require different capabilities or roles (e.g. fact-checker, editor, test runner as shown in the original examples).
- **Isolation**: a complex task may benefit from a dedicated context window.

Sub-agent spawning is done through a mechanism external to the task system. The task system provides the shared state that makes coordination possible.

### Spawning sub-agents

See the Claude Code system prompt definitions for the verbatim tool definitions used to launch and manage sub-agents: [Task](./tasks/tasks_claude_code_system_prompt.md#task-sub-agent-launcher), [TaskOutput](./tasks/tasks_claude_code_system_prompt.md#taskoutput), [TaskStop](./tasks/tasks_claude_code_system_prompt.md#taskstop).

### Agent assignment

The `owner` field enables coordination between the orchestrator and its sub-agents. The original states: *"The owner field is a label for filtering, not automatic spawning"* (details post, "Agent Assignment").

The orchestrator assigns owners via TaskUpdate, then spawns sub-agents instructing each to find tasks matching its name. Multiple sub-agents can be spawned simultaneously -- they all read from and write to the same task list without conflicts, enabling parallel execution of independent tasks.

The workflow for each worker (whether the orchestrator itself or a sub-agent):

1. Call TaskList to find tasks that are `"pending"` and not blocked. `SYSTEM_PROMPT`: Prefer lowest ID first.
2. Filter for tasks matching the worker's name (if using ownership).
3. Pick a task. `SYSTEM_PROMPT`: Call TaskGet to read its full description, context, and verify `blockedBy` is clear.
4. Call TaskUpdate to set status to `"in_progress"`.
5. Perform the work.
6. Call TaskUpdate to set status to `"completed"`. `SYSTEM_PROMPT`: If errors or blockers are encountered, keep the task `"in_progress"` and create a new blocker task describing what needs to be resolved.
7. Repeat until no tasks remain.


## Persistence

Tasks are persisted to the filesystem as individual JSON files (one per task). This means:

- Multiple agents or sessions sharing the same Task List ID see the same state.
- Task state survives agent restarts and context window resets.
- External tooling can read, write, backup, or template task files directly.

A Task List ID can be set explicitly to enable cross-session persistence. Without an explicit ID, each session gets its own ephemeral task list.


## Examples

### Linear: Adding a Feature

*"Add a logout button to the navbar"*

```json
{ "subject": "Add logout button to navbar component",
  "description": "Add button with onClick handler in NavBar.tsx" }

{ "subject": "Implement logout API call",
  "description": "Clear session, revoke token, redirect to login",
  "addBlockedBy": ["1"] }

{ "subject": "Test logout flow",
  "description": "Verify session cleared, redirect works, edge cases handled",
  "addBlockedBy": ["2"] }
```

Three tasks, strictly sequential.

### Diamond: Investigation Before Implementation

*"Refactor the auth system to use JWT instead of sessions"*

```json
// Investigation -- no dependencies, can run in parallel
{ "subject": "Investigate current session implementation" }
{ "subject": "Research JWT best practices" }

// Planning -- blocked by both investigation tasks
{ "subject": "Design JWT implementation plan", "addBlockedBy": ["1", "2"] }

// Implementation -- blocked by planning
{ "subject": "Implement JWT authentication", "addBlockedBy": ["3"] }
{ "subject": "Update all protected routes", "addBlockedBy": ["4"] }
{ "subject": "Add token refresh mechanism", "addBlockedBy": ["4"] }

// Testing -- blocked by implementation
{ "subject": "Write integration tests", "addBlockedBy": ["5", "6"] }
```

Tasks #1 and #2 run in parallel; #3 waits for both. Tasks #5 and #6 also run in parallel once #4 completes.

### Complex Graph: Event Planning

```json
// #1 - No dependencies
{ "subject": "Book venue", "owner": "couple" }

// #2 - Venue determines available dates
{ "subject": "Set wedding date", "addBlockedBy": ["1"], "owner": "couple" }

// #3 - Independent, parallel with #1 and #2
{ "subject": "Create guest list", "owner": "couple" }

// #4 - Needs venue specs and date
{ "subject": "Book caterer", "addBlockedBy": ["1", "2"], "owner": "planner" }

// #5 - Needs date for printing and guest list for addresses
{ "subject": "Send invitations", "addBlockedBy": ["2", "3"], "owner": "couple" }

// #6 - Needs invitations sent first
{ "subject": "Collect RSVPs", "addBlockedBy": ["5"] }

// #7 - Needs caterer capacity and RSVP counts
{ "subject": "Finalize seating chart", "addBlockedBy": ["4", "6"], "owner": "planner" }

// #8 - Needs RSVP count to confirm with caterer
{ "subject": "Confirm final headcount", "addBlockedBy": ["6"], "owner": "planner" }
```

The dependency graph enforces that invitations go out only after date and guest list are ready, seating is finalized only after RSVPs are collected, and so on.


## Best Practices

When to use tasks: multi-step work (3+ steps), work with dependencies between steps, work spanning multiple sessions or agents, complex features or refactors, delegating to multiple parallel agents.

When to skip: quick one-off questions, simple single-file edits, anything you'll finish in one shot.

Guidelines:
- Use imperative form for `subject` ("Run tests") and present continuous for `activeForm` ("Running tests"). The activeForm quality matters -- good: "Running database migrations"; bad: "Doing stuff".
- Use meaningful owner names that describe the agent's role ("backend-dev", "fact-checker") rather than generic labels ("agent1").
- Let the orchestrator break down work into tasks. Dependencies prevent starting work that depends on unfinished prerequisites.
- Use TaskList as the source of truth for progress and to discover the next available task.
