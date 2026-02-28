## Hands-On: Tasks

This hands-on explores `example_tasks.ipynb` and the `core/tasks/` module, which implements the task coordination concepts from the previous section. The module has four files: `task_status.py` (the status enum), `task.py` (data model), `task_list.py` (persistence and dependency management), and `task_tools.py` (agent-facing tools).

#### Status and Model

The status enum has four values:

```python
class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DELETED = "deleted"
```

A `Task` carries the subject, description, ownership, and dependency information. Dependencies use bidirectional `blocks` / `blocked_by` fields:

```python
class Task(BaseModel):
    id: str = ""
    subject: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    active_form: str | None = None    # Present-continuous label shown during work
    owner: str | None = None
    blocks: list[str] = []            # Tasks that cannot start until this completes
    blocked_by: list[str] = []        # Tasks that must complete before this can start
    metadata: dict = {}
```

Task IDs are auto-assigned as incrementing integers ("1", "2", "3"). The `active_form` field provides a human-readable label for progress display (e.g., "Analyzing dataset" while status is `in_progress`).

#### TaskList

`TaskList` is the storage and coordination layer, persisting each task as an individual JSON file with file-level locking (`fcntl`) for concurrency safety:

```python
class TaskList:
    async def create(subject, description, *, active_form=None, metadata=None) -> Task
    async def get(task_id) -> Task | None
    async def list_all() -> list[Task]
    async def update(task_id, *, status=None, subject=None, owner=None,
                     add_blocks=None, add_blocked_by=None, ...) -> Task | None
    async def next_available(*, owner=None) -> Task | None
```

`next_available()` is dependency-aware: it returns the first pending task (sorted by ID) whose every `blocked_by` entry has reached `completed`. The `update()` method enforces that blocked tasks cannot transition to `in_progress` -- it raises a `ValueError` if attempted. Dependency additions via `add_blocks` and `add_blocked_by` are append-only and automatically synchronized bidirectionally: adding task B to A's `blocked_by` adds A to B's `blocks`.

The `list_all()` method returns a summary view with metadata stripped, keeping responses compact when agents just need to see what work exists.

#### Agent Tools

Four async tools are exposed via `get_task_tools(task_list)`:

```python
async def task_create(ctx, subject, description, *, active_form=None, metadata=None) -> str
async def task_get(ctx, task_id) -> str
async def task_list_all(ctx) -> str
async def task_update(ctx, task_id, *, status=None, subject=None, owner=None,
                      add_blocks=None, add_blocked_by=None, metadata=None, ...) -> str
```

All return formatted strings. `task_update` accepts a status string ("pending", "in_progress", "completed", "deleted") that gets parsed into the enum. Metadata merge semantics: keys with non-null values are added or updated; keys with `null` values are deleted.

#### Agent Workflow

The typical agent workflow using tasks:

1. Call `task_list_all()` to see available work
2. Find a pending, unblocked task
3. Call `task_update(task_id, status="in_progress")` to claim it
4. Do the work
5. Call `task_update(task_id, status="completed")` when done
6. Repeat until no tasks remain

If the agent encounters errors, it keeps the task as `in_progress` and can create a new blocking task describing what needs to be resolved.

#### Sub-Agent to Task Mapping

The following table shows how sub-agent concepts map to the task system:

| Sub-agent concept | Task equivalent |
|-------------------|-----------------|
| `get_agent(system_prompt=...)` | `task_create(subject=..., description=...)` |
| `run_agent(agent, input)` | `task_update(task_id, status="in_progress")` + do work |
| `result.output` | `task_update(task_id, status="completed")` |
| Exception handling | Keep task `in_progress`, create blocker task |
| Fire-and-forget call | `task_launch(agent_name, prompt, run_in_background=True)` |
| No observation | `task_list_all()`, `task_get(task_id)` |
| No persistence | `TaskList` with file-backed storage |
| No dependency ordering | `blocked_by` / `blocks` with DAG-aware dispatch |
