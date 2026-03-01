## Tasks

Sub-agents are fire-and-forget: the coordinator calls, awaits, and moves on. This works for short tasks but breaks down when work is long-running, involves multiple agents with dependencies, or needs structured tracking. The task system provides a lightweight coordination layer: durable state, dependency management, and structured progress tracking for multi-step agent work.

### State Machine

A task moves through a small set of states: `pending`, `in_progress`, `completed`, `deleted`. Tasks are created as `pending`. When an agent starts working on a task, it transitions to `in_progress`. When the work is done, the task moves to `completed`. The `deleted` status permanently removes a task that is no longer relevant.

```
pending --> in_progress --> completed
                       \-> deleted
        \-> deleted
```

The state machine enforces one key constraint: a task with unresolved dependencies (non-empty `blocked_by` where at least one blocker is incomplete) cannot transition to `in_progress`. This prevents agents from starting work whose prerequisites are not yet met.

### Task Model

A `Task` carries the information agents need to coordinate work:

```python
class Task(BaseModel):
    id: str                              # Auto-assigned ("1", "2", ...)
    subject: str                         # Brief imperative title
    description: str                     # Detailed requirements and context
    status: TaskStatus = TaskStatus.PENDING
    active_form: str | None = None       # Present-continuous label (e.g., "Running tests")
    owner: str | None = None             # Agent assigned to this task
    blocks: list[str] = []               # Task IDs that cannot start until this completes
    blocked_by: list[str] = []           # Task IDs that must complete before this can start
    metadata: dict = {}                  # Arbitrary key/value data
```

Dependencies are bidirectional: adding task B to task A's `blocked_by` automatically adds A to task B's `blocks`. This keeps the dependency graph consistent without requiring agents to maintain both sides manually.

### TaskList

`TaskList` is the storage and coordination layer. It persists each task as an individual JSON file, using file-level locking for concurrency safety. The interface is small:

```python
class TaskList:
    async def create(subject, description, *, active_form=None, metadata=None) -> Task
    async def get(task_id) -> Task | None
    async def list_all() -> list[Task]          # Summary view, metadata stripped
    async def update(task_id, *, status=None, subject=None, owner=None,
                     add_blocks=None, add_blocked_by=None, ...) -> Task | None
    async def next_available(*, owner=None) -> Task | None  # First pending, unblocked task
```

`next_available()` is dependency-aware: it returns the first pending task (lowest ID) whose every `blocked_by` entry has reached `completed`. If an owner is specified, it filters for tasks assigned to that agent. This enables multiple agents to pull work from the same list without conflicts.

### Agent-Facing Tools

Four tools expose the `TaskList` to agents:

`task_create(subject, description, *, active_form, metadata)` creates a new task and returns its ID. `task_get(task_id)` retrieves full details including dependencies. `task_list_all()` returns a summary of all tasks with status, owner, and blocked-by info. `task_update(task_id, *, status, subject, owner, add_blocks, add_blocked_by, metadata, ...)` modifies any aspect of a task -- status transitions, dependency additions, metadata merges. Setting a metadata key to `null` deletes it.

### Dependencies and Parallel Execution

Tasks declare dependencies via `blocked_by`, a list of task IDs that must reach `completed` before the task can start. Independent tasks (no blockers, or all blockers completed) can run in parallel. Tasks whose dependencies are not yet met remain `pending` -- the system prevents them from transitioning to `in_progress`.

A research task must complete before the writing task that uses its findings. Two independent research tasks can run in parallel, but the summary that combines them must wait for both. These relationships form a directed acyclic graph (DAG) that the `TaskList` enforces through its blocking logic.

### Connection to Sub-Agents and A2A

Tasks and sub-agents are orthogonal systems that work together. Tasks track what needs to be done and in what order. Sub-agents (via `AgentRunner`) handle execution. `OrchestratorAgent` -- introduced fully in the chapter *The Complete Agent* -- wires both into the same agent: task tools for planning and tracking, agent runner tools (`task_launch`, `task_output`, `task_stop`) for delegation.

The same coordination concepts appear in A2A as protocol-level guarantees. A2A defines task states, streaming via Server-Sent Events, push notifications via webhooks, and task storage as protocol requirements. The `core/tasks/` module is the local implementation of those ideas -- lightweight coordination within a single process rather than across a network.
