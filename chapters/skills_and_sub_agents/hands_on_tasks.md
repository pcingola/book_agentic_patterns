## Hands-On: Tasks

This hands-on explores `example_tasks.ipynb` and the `core/tasks/` module, which implements the task lifecycle concepts from the previous section. The module has five files: `state.py` (the state enum), `models.py` (data models), `store.py` (persistence), `worker.py` (sub-agent execution), and `broker.py` (coordination).

#### State and Models

The state machine is an enum with a set of terminal states:

```python
class TaskState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    INPUT_REQUIRED = "input_required"
    CANCELLED = "cancelled"

TERMINAL_STATES = {TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED}
```

A `Task` carries the input, result, error, events, and metadata. The metadata dictionary is the bridge to sub-agents -- it carries `system_prompt` and `config_name` so the worker knows how to configure the sub-agent:

```python
class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    state: TaskState = TaskState.PENDING
    input: str
    result: str | None = None
    error: str | None = None
    events: list[TaskEvent] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
```

`TaskEvent` records state transitions and progress for the observation layer:

```python
class TaskEvent(BaseModel):
    task_id: str
    event_type: EventType  # STATE_CHANGE, PROGRESS, LOG
    payload: dict = Field(default_factory=dict)
    timestamp: datetime
```

#### Storage

`TaskStore` is the abstract interface. The contract is small -- six methods:

```python
class TaskStore(ABC):
    async def create(self, task: Task) -> Task: ...
    async def get(self, task_id: str) -> Task | None: ...
    async def update_state(self, task_id: str, state: TaskState, ...) -> Task | None: ...
    async def list_by_state(self, state: TaskState) -> list[Task]: ...
    async def next_pending(self) -> Task | None: ...
    async def add_event(self, task_id: str, event: TaskEvent) -> None: ...
```

`TaskStoreJson` implements this with one JSON file per task, using `pathlib.Path` for file operations and `asyncio.Lock` for concurrency safety. The implementation is intentionally simple -- production use would swap in a database-backed store without changing any other code.

#### Worker

The worker is where sub-agents meet the task lifecycle. `Worker.execute()` maps directly to the dynamic sub-agent pattern:

```python
async def execute(self, task_id: str) -> None:
    task = await self._store.get(task_id)
    await self._store.update_state(task_id, TaskState.RUNNING)

    system_prompt = task.metadata.get("system_prompt", "You are a helpful assistant.")
    config_name = task.metadata.get("config_name", "default")
    agent = get_agent(model=self._model, config_name=config_name, system_prompt=system_prompt)
    agent_run, _ = await run_agent(agent, task.input)

    result = str(agent_run.result.output)
    await self._store.update_state(task_id, TaskState.COMPLETED, result=result)
```

Read the metadata, create an agent, run it, write the result. If the agent raises an exception, the worker catches it and transitions the task to `FAILED` with the error message. The worker itself is stateless -- it holds a reference to the store but maintains no task-specific data. The actual implementation also supports `AgentSpec`-based execution for composition with `OrchestratorAgent`, and emits progress and log events via a node hook so that observers can track what the sub-agent is doing in real time.

#### Broker

`TaskBroker` ties everything together as an async context manager. On entry it starts a background dispatch loop; on exit it cancels it:

```python
async with TaskBroker() as broker:
    task_id = await broker.submit("Explain quantum entanglement", system_prompt="You are a physicist.")
    task = await broker.wait(task_id)
    print(task.result)
```

The dispatch loop is a simple polling loop: check for pending tasks, hand them to the worker, fire callbacks when done. The broker exposes five observation methods: `poll()` returns current state, `wait()` blocks until terminal, `stream()` yields events, `cancel()` stops execution, and `notify()` registers callbacks for specific state changes.

#### Sub-Agent to Task Mapping

The following table shows how sub-agent concepts map to the task lifecycle:

| Sub-agent concept | Task equivalent |
|-------------------|-----------------|
| `get_agent(system_prompt=...)` | `task.metadata["system_prompt"]` |
| `run_agent(agent, input)` | `worker.execute(task_id)` |
| `result.output` | `task.result` |
| Exception handling | `task.state = FAILED`, `task.error` |
| Fire-and-forget call | `broker.submit()` + `broker.wait()` |
| No observation | `broker.poll()`, `broker.stream()`, `broker.notify()` |
| No persistence | `TaskStore` with durable backend |
| No cancellation | `broker.cancel()` |
