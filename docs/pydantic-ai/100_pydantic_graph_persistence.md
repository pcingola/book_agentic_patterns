# `pydantic_graph.persistence`

### SnapshotStatus

```python
SnapshotStatus = Literal[
    "created", "pending", "running", "success", "error"
]
```

The status of a snapshot.

- `'created'`: The snapshot has been created but not yet run.
- `'pending'`: The snapshot has been retrieved with load_next but not yet run.
- `'running'`: The snapshot is currently running.
- `'success'`: The snapshot has been run successfully.
- `'error'`: The snapshot has been run but an error occurred.

### NodeSnapshot

Bases: `Generic[StateT, RunEndT]`

History step describing the execution of a node in a graph.

Source code in `pydantic_graph/pydantic_graph/persistence/__init__.py`

```python
@dataclass(kw_only=True)
class NodeSnapshot(Generic[StateT, RunEndT]):
    """History step describing the execution of a node in a graph."""

    state: StateT
    """The state of the graph before the node is run."""
    node: Annotated[BaseNode[StateT, Any, RunEndT], _utils.CustomNodeSchema()]
    """The node to run next."""
    start_ts: datetime | None = None
    """The timestamp when the node started running, `None` until the run starts."""
    duration: float | None = None
    """The duration of the node run in seconds, if the node has been run."""
    status: SnapshotStatus = 'created'
    """The status of the snapshot."""
    kind: Literal['node'] = 'node'
    """The kind of history step, can be used as a discriminator when deserializing history."""

    id: str = UNSET_SNAPSHOT_ID
    """Unique ID of the snapshot."""

    def __post_init__(self) -> None:
        if self.id == UNSET_SNAPSHOT_ID:
            self.id = self.node.get_snapshot_id()
```

#### state

```python
state: StateT
```

The state of the graph before the node is run.

#### node

```python
node: Annotated[
    BaseNode[StateT, Any, RunEndT], CustomNodeSchema()
]
```

The node to run next.

#### start_ts

```python
start_ts: datetime | None = None
```

The timestamp when the node started running, `None` until the run starts.

#### duration

```python
duration: float | None = None
```

The duration of the node run in seconds, if the node has been run.

#### status

```python
status: SnapshotStatus = 'created'
```

The status of the snapshot.

#### kind

```python
kind: Literal['node'] = 'node'
```

The kind of history step, can be used as a discriminator when deserializing history.

#### id

```python
id: str = UNSET_SNAPSHOT_ID
```

Unique ID of the snapshot.

### EndSnapshot

Bases: `Generic[StateT, RunEndT]`

History step describing the end of a graph run.

Source code in `pydantic_graph/pydantic_graph/persistence/__init__.py`

```python
@dataclass(kw_only=True)
class EndSnapshot(Generic[StateT, RunEndT]):
    """History step describing the end of a graph run."""

    state: StateT
    """The state of the graph at the end of the run."""
    result: End[RunEndT]
    """The result of the graph run."""
    ts: datetime = field(default_factory=_utils.now_utc)
    """The timestamp when the graph run ended."""
    kind: Literal['end'] = 'end'
    """The kind of history step, can be used as a discriminator when deserializing history."""

    id: str = UNSET_SNAPSHOT_ID
    """Unique ID of the snapshot."""

    def __post_init__(self) -> None:
        if self.id == UNSET_SNAPSHOT_ID:
            self.id = self.node.get_snapshot_id()

    @property
    def node(self) -> End[RunEndT]:
        """Shim to get the [`result`][pydantic_graph.persistence.EndSnapshot.result].

        Useful to allow `[snapshot.node for snapshot in persistence.history]`.
        """
        return self.result
```

#### state

```python
state: StateT
```

The state of the graph at the end of the run.

#### result

```python
result: End[RunEndT]
```

The result of the graph run.

#### ts

```python
ts: datetime = field(default_factory=now_utc)
```

The timestamp when the graph run ended.

#### kind

```python
kind: Literal['end'] = 'end'
```

The kind of history step, can be used as a discriminator when deserializing history.

#### id

```python
id: str = UNSET_SNAPSHOT_ID
```

Unique ID of the snapshot.

#### node

```python
node: End[RunEndT]
```

Shim to get the result.

Useful to allow `[snapshot.node for snapshot in persistence.history]`.

### Snapshot

```python
Snapshot = (
    NodeSnapshot[StateT, RunEndT]
    | EndSnapshot[StateT, RunEndT]
)
```

A step in the history of a graph run.

Graph.run returns a list of these steps describing the execution of the graph, together with the run return value.

### BaseStatePersistence

Bases: `ABC`, `Generic[StateT, RunEndT]`

Abstract base class for storing the state of a graph run.

Each instance of a `BaseStatePersistence` subclass should be used for a single graph run.

Source code in `pydantic_graph/pydantic_graph/persistence/__init__.py`

```python
class BaseStatePersistence(ABC, Generic[StateT, RunEndT]):
    """Abstract base class for storing the state of a graph run.

    Each instance of a `BaseStatePersistence` subclass should be used for a single graph run.
    """

    @abstractmethod
    async def snapshot_node(self, state: StateT, next_node: BaseNode[StateT, Any, RunEndT]) -> None:
        """Snapshot the state of a graph, when the next step is to run a node.

        This method should add a [`NodeSnapshot`][pydantic_graph.persistence.NodeSnapshot] to persistence.

        Args:
            state: The state of the graph.
            next_node: The next node to run.
        """
        raise NotImplementedError

    @abstractmethod
    async def snapshot_node_if_new(
        self, snapshot_id: str, state: StateT, next_node: BaseNode[StateT, Any, RunEndT]
    ) -> None:
        """Snapshot the state of a graph if the snapshot ID doesn't already exist in persistence.

        This method will generally call [`snapshot_node`][pydantic_graph.persistence.BaseStatePersistence.snapshot_node]
        but should do so in an atomic way.

        Args:
            snapshot_id: The ID of the snapshot to check.
            state: The state of the graph.
            next_node: The next node to run.
        """
        raise NotImplementedError

    @abstractmethod
    async def snapshot_end(self, state: StateT, end: End[RunEndT]) -> None:
        """Snapshot the state of a graph when the graph has ended.

        This method should add an [`EndSnapshot`][pydantic_graph.persistence.EndSnapshot] to persistence.

        Args:
            state: The state of the graph.
            end: data from the end of the run.
        """
        raise NotImplementedError

    @abstractmethod
    def record_run(self, snapshot_id: str) -> AbstractAsyncContextManager[None]:
        """Record the run of the node, or error if the node is already running.

        Args:
            snapshot_id: The ID of the snapshot to record.

        Raises:
            GraphNodeRunningError: if the node status it not `'created'` or `'pending'`.
            LookupError: if the snapshot ID is not found in persistence.

        Returns:
            An async context manager that records the run of the node.

        In particular this should set:

        - [`NodeSnapshot.status`][pydantic_graph.persistence.NodeSnapshot.status] to `'running'` and
          [`NodeSnapshot.start_ts`][pydantic_graph.persistence.NodeSnapshot.start_ts] when the run starts.
        - [`NodeSnapshot.status`][pydantic_graph.persistence.NodeSnapshot.status] to `'success'` or `'error'` and
          [`NodeSnapshot.duration`][pydantic_graph.persistence.NodeSnapshot.duration] when the run finishes.
        """
        raise NotImplementedError

    @abstractmethod
    async def load_next(self) -> NodeSnapshot[StateT, RunEndT] | None:
        """Retrieve a node snapshot with status `'created`' and set its status to `'pending'`.

        This is used by [`Graph.iter_from_persistence`][pydantic_graph.graph.Graph.iter_from_persistence]
        to get the next node to run.

        Returns: The snapshot, or `None` if no snapshot with status `'created`' exists.
        """
        raise NotImplementedError

    @abstractmethod
    async def load_all(self) -> list[Snapshot[StateT, RunEndT]]:
        """Load the entire history of snapshots.

        `load_all` is not used by pydantic-graph itself, instead it's provided to make it convenient to
        get all [snapshots][pydantic_graph.persistence.Snapshot] from persistence.

        Returns: The list of snapshots.
        """
        raise NotImplementedError

    def set_graph_types(self, graph: Graph[StateT, Any, RunEndT]) -> None:
        """Set the types of the state and run end from a graph.

        You generally won't need to customise this method, instead implement
        [`set_types`][pydantic_graph.persistence.BaseStatePersistence.set_types] and
        [`should_set_types`][pydantic_graph.persistence.BaseStatePersistence.should_set_types].
        """
        if self.should_set_types():
            with _utils.set_nodes_type_context(graph.get_nodes()):
                self.set_types(*graph.inferred_types)

    def should_set_types(self) -> bool:
        """Whether types need to be set.

        Implementations should override this method to return `True` when types have not been set if they are needed.
        """
        return False

    def set_types(self, state_type: type[StateT], run_end_type: type[RunEndT]) -> None:
        """Set the types of the state and run end.

        This can be used to create [type adapters][pydantic.TypeAdapter] for serializing and deserializing snapshots,
        e.g. with [`build_snapshot_list_type_adapter`][pydantic_graph.persistence.build_snapshot_list_type_adapter].

        Args:
            state_type: The state type.
            run_end_type: The run end type.
        """
        pass
```

#### snapshot_node

```python
snapshot_node(
    state: StateT, next_node: BaseNode[StateT, Any, RunEndT]
) -> None
```

Snapshot the state of a graph, when the next step is to run a node.

This method should add a NodeSnapshot to persistence.

Parameters:

| Name        | Type                             | Description             | Default    |
| ----------- | -------------------------------- | ----------------------- | ---------- |
| `state`     | `StateT`                         | The state of the graph. | *required* |
| `next_node` | `BaseNode[StateT, Any, RunEndT]` | The next node to run.   | *required* |

Source code in `pydantic_graph/pydantic_graph/persistence/__init__.py`

```python
@abstractmethod
async def snapshot_node(self, state: StateT, next_node: BaseNode[StateT, Any, RunEndT]) -> None:
    """Snapshot the state of a graph, when the next step is to run a node.

    This method should add a [`NodeSnapshot`][pydantic_graph.persistence.NodeSnapshot] to persistence.

    Args:
        state: The state of the graph.
        next_node: The next node to run.
    """
    raise NotImplementedError
```

#### snapshot_node_if_new

```python
snapshot_node_if_new(
    snapshot_id: str,
    state: StateT,
    next_node: BaseNode[StateT, Any, RunEndT],
) -> None
```

Snapshot the state of a graph if the snapshot ID doesn't already exist in persistence.

This method will generally call snapshot_node but should do so in an atomic way.

Parameters:

| Name          | Type                             | Description                      | Default    |
| ------------- | -------------------------------- | -------------------------------- | ---------- |
| `snapshot_id` | `str`                            | The ID of the snapshot to check. | *required* |
| `state`       | `StateT`                         | The state of the graph.          | *required* |
| `next_node`   | `BaseNode[StateT, Any, RunEndT]` | The next node to run.            | *required* |

Source code in `pydantic_graph/pydantic_graph/persistence/__init__.py`

```python
@abstractmethod
async def snapshot_node_if_new(
    self, snapshot_id: str, state: StateT, next_node: BaseNode[StateT, Any, RunEndT]
) -> None:
    """Snapshot the state of a graph if the snapshot ID doesn't already exist in persistence.

    This method will generally call [`snapshot_node`][pydantic_graph.persistence.BaseStatePersistence.snapshot_node]
    but should do so in an atomic way.

    Args:
        snapshot_id: The ID of the snapshot to check.
        state: The state of the graph.
        next_node: The next node to run.
    """
    raise NotImplementedError
```

#### snapshot_end

```python
snapshot_end(state: StateT, end: End[RunEndT]) -> None
```

Snapshot the state of a graph when the graph has ended.

This method should add an EndSnapshot to persistence.

Parameters:

| Name    | Type           | Description                   | Default    |
| ------- | -------------- | ----------------------------- | ---------- |
| `state` | `StateT`       | The state of the graph.       | *required* |
| `end`   | `End[RunEndT]` | data from the end of the run. | *required* |

Source code in `pydantic_graph/pydantic_graph/persistence/__init__.py`

```python
@abstractmethod
async def snapshot_end(self, state: StateT, end: End[RunEndT]) -> None:
    """Snapshot the state of a graph when the graph has ended.

    This method should add an [`EndSnapshot`][pydantic_graph.persistence.EndSnapshot] to persistence.

    Args:
        state: The state of the graph.
        end: data from the end of the run.
    """
    raise NotImplementedError
```

#### record_run

```python
record_run(
    snapshot_id: str,
) -> AbstractAsyncContextManager[None]
```

Record the run of the node, or error if the node is already running.

Parameters:

| Name          | Type  | Description                       | Default    |
| ------------- | ----- | --------------------------------- | ---------- |
| `snapshot_id` | `str` | The ID of the snapshot to record. | *required* |

Raises:

| Type                    | Description                                       |
| ----------------------- | ------------------------------------------------- |
| `GraphNodeRunningError` | if the node status it not 'created' or 'pending'. |
| `LookupError`           | if the snapshot ID is not found in persistence.   |

Returns:

| Type                                | Description                                                |
| ----------------------------------- | ---------------------------------------------------------- |
| `AbstractAsyncContextManager[None]` | An async context manager that records the run of the node. |

In particular this should set:

- NodeSnapshot.status to `'running'` and NodeSnapshot.start_ts when the run starts.
- NodeSnapshot.status to `'success'` or `'error'` and NodeSnapshot.duration when the run finishes.

Source code in `pydantic_graph/pydantic_graph/persistence/__init__.py`

```python
@abstractmethod
def record_run(self, snapshot_id: str) -> AbstractAsyncContextManager[None]:
    """Record the run of the node, or error if the node is already running.

    Args:
        snapshot_id: The ID of the snapshot to record.

    Raises:
        GraphNodeRunningError: if the node status it not `'created'` or `'pending'`.
        LookupError: if the snapshot ID is not found in persistence.

    Returns:
        An async context manager that records the run of the node.

    In particular this should set:

    - [`NodeSnapshot.status`][pydantic_graph.persistence.NodeSnapshot.status] to `'running'` and
      [`NodeSnapshot.start_ts`][pydantic_graph.persistence.NodeSnapshot.start_ts] when the run starts.
    - [`NodeSnapshot.status`][pydantic_graph.persistence.NodeSnapshot.status] to `'success'` or `'error'` and
      [`NodeSnapshot.duration`][pydantic_graph.persistence.NodeSnapshot.duration] when the run finishes.
    """
    raise NotImplementedError
```

#### load_next

```python
load_next() -> NodeSnapshot[StateT, RunEndT] | None
```

Retrieve a node snapshot with status `'created`' and set its status to `'pending'`.

This is used by Graph.iter_from_persistence to get the next node to run.

Returns: The snapshot, or `None` if no snapshot with status `'created`' exists.

Source code in `pydantic_graph/pydantic_graph/persistence/__init__.py`

```python
@abstractmethod
async def load_next(self) -> NodeSnapshot[StateT, RunEndT] | None:
    """Retrieve a node snapshot with status `'created`' and set its status to `'pending'`.

    This is used by [`Graph.iter_from_persistence`][pydantic_graph.graph.Graph.iter_from_persistence]
    to get the next node to run.

    Returns: The snapshot, or `None` if no snapshot with status `'created`' exists.
    """
    raise NotImplementedError
```

#### load_all

```python
load_all() -> list[Snapshot[StateT, RunEndT]]
```

Load the entire history of snapshots.

`load_all` is not used by pydantic-graph itself, instead it's provided to make it convenient to get all snapshots from persistence.

Returns: The list of snapshots.

Source code in `pydantic_graph/pydantic_graph/persistence/__init__.py`

```python
@abstractmethod
async def load_all(self) -> list[Snapshot[StateT, RunEndT]]:
    """Load the entire history of snapshots.

    `load_all` is not used by pydantic-graph itself, instead it's provided to make it convenient to
    get all [snapshots][pydantic_graph.persistence.Snapshot] from persistence.

    Returns: The list of snapshots.
    """
    raise NotImplementedError
```

#### set_graph_types

```python
set_graph_types(graph: Graph[StateT, Any, RunEndT]) -> None
```

Set the types of the state and run end from a graph.

You generally won't need to customise this method, instead implement set_types and should_set_types.

Source code in `pydantic_graph/pydantic_graph/persistence/__init__.py`

```python
def set_graph_types(self, graph: Graph[StateT, Any, RunEndT]) -> None:
    """Set the types of the state and run end from a graph.

    You generally won't need to customise this method, instead implement
    [`set_types`][pydantic_graph.persistence.BaseStatePersistence.set_types] and
    [`should_set_types`][pydantic_graph.persistence.BaseStatePersistence.should_set_types].
    """
    if self.should_set_types():
        with _utils.set_nodes_type_context(graph.get_nodes()):
            self.set_types(*graph.inferred_types)
```

#### should_set_types

```python
should_set_types() -> bool
```

Whether types need to be set.

Implementations should override this method to return `True` when types have not been set if they are needed.

Source code in `pydantic_graph/pydantic_graph/persistence/__init__.py`

```python
def should_set_types(self) -> bool:
    """Whether types need to be set.

    Implementations should override this method to return `True` when types have not been set if they are needed.
    """
    return False
```

#### set_types

```python
set_types(
    state_type: type[StateT], run_end_type: type[RunEndT]
) -> None
```

Set the types of the state and run end.

This can be used to create type adapters for serializing and deserializing snapshots, e.g. with build_snapshot_list_type_adapter.

Parameters:

| Name           | Type            | Description       | Default    |
| -------------- | --------------- | ----------------- | ---------- |
| `state_type`   | `type[StateT]`  | The state type.   | *required* |
| `run_end_type` | `type[RunEndT]` | The run end type. | *required* |

Source code in `pydantic_graph/pydantic_graph/persistence/__init__.py`

```python
def set_types(self, state_type: type[StateT], run_end_type: type[RunEndT]) -> None:
    """Set the types of the state and run end.

    This can be used to create [type adapters][pydantic.TypeAdapter] for serializing and deserializing snapshots,
    e.g. with [`build_snapshot_list_type_adapter`][pydantic_graph.persistence.build_snapshot_list_type_adapter].

    Args:
        state_type: The state type.
        run_end_type: The run end type.
    """
    pass
```

### build_snapshot_list_type_adapter

```python
build_snapshot_list_type_adapter(
    state_t: type[StateT], run_end_t: type[RunEndT]
) -> TypeAdapter[list[Snapshot[StateT, RunEndT]]]
```

Build a type adapter for a list of snapshots.

This method should be called from within set_types where context variables will be set such that Pydantic can create a schema for NodeSnapshot.node.

Source code in `pydantic_graph/pydantic_graph/persistence/__init__.py`

```python
def build_snapshot_list_type_adapter(
    state_t: type[StateT], run_end_t: type[RunEndT]
) -> pydantic.TypeAdapter[list[Snapshot[StateT, RunEndT]]]:
    """Build a type adapter for a list of snapshots.

    This method should be called from within
    [`set_types`][pydantic_graph.persistence.BaseStatePersistence.set_types]
    where context variables will be set such that Pydantic can create a schema for
    [`NodeSnapshot.node`][pydantic_graph.persistence.NodeSnapshot.node].
    """
    return pydantic.TypeAdapter(list[Annotated[Snapshot[state_t, run_end_t], pydantic.Discriminator('kind')]])
```

In memory state persistence.

This module provides simple in memory state persistence for graphs.

### SimpleStatePersistence

Bases: `BaseStatePersistence[StateT, RunEndT]`

Simple in memory state persistence that just hold the latest snapshot.

If no state persistence implementation is provided when running a graph, this is used by default.

Source code in `pydantic_graph/pydantic_graph/persistence/in_mem.py`

```python
@dataclass
class SimpleStatePersistence(BaseStatePersistence[StateT, RunEndT]):
    """Simple in memory state persistence that just hold the latest snapshot.

    If no state persistence implementation is provided when running a graph, this is used by default.
    """

    last_snapshot: Snapshot[StateT, RunEndT] | None = None
    """The last snapshot."""

    async def snapshot_node(self, state: StateT, next_node: BaseNode[StateT, Any, RunEndT]) -> None:
        self.last_snapshot = NodeSnapshot(state=state, node=next_node)

    async def snapshot_node_if_new(
        self, snapshot_id: str, state: StateT, next_node: BaseNode[StateT, Any, RunEndT]
    ) -> None:
        if self.last_snapshot and self.last_snapshot.id == snapshot_id:
            return  # pragma: no cover
        else:
            await self.snapshot_node(state, next_node)

    async def snapshot_end(self, state: StateT, end: End[RunEndT]) -> None:
        self.last_snapshot = EndSnapshot(state=state, result=end)

    @asynccontextmanager
    async def record_run(self, snapshot_id: str) -> AsyncIterator[None]:
        if self.last_snapshot is None or snapshot_id != self.last_snapshot.id:
            raise LookupError(f'No snapshot found with id={snapshot_id!r}')

        assert isinstance(self.last_snapshot, NodeSnapshot), 'Only NodeSnapshot can be recorded'
        exceptions.GraphNodeStatusError.check(self.last_snapshot.status)
        self.last_snapshot.status = 'running'
        self.last_snapshot.start_ts = _utils.now_utc()

        start = perf_counter()
        try:
            yield
        except Exception:  # pragma: no cover
            self.last_snapshot.duration = perf_counter() - start
            self.last_snapshot.status = 'error'
            raise
        else:
            self.last_snapshot.duration = perf_counter() - start
            self.last_snapshot.status = 'success'

    async def load_next(self) -> NodeSnapshot[StateT, RunEndT] | None:
        if isinstance(self.last_snapshot, NodeSnapshot) and self.last_snapshot.status == 'created':
            self.last_snapshot.status = 'pending'
            return copy.deepcopy(self.last_snapshot)

    async def load_all(self) -> list[Snapshot[StateT, RunEndT]]:
        raise NotImplementedError('load is not supported for SimpleStatePersistence')
```

#### last_snapshot

```python
last_snapshot: Snapshot[StateT, RunEndT] | None = None
```

The last snapshot.

### FullStatePersistence

Bases: `BaseStatePersistence[StateT, RunEndT]`

In memory state persistence that hold a list of snapshots.

Source code in `pydantic_graph/pydantic_graph/persistence/in_mem.py`

```python
@dataclass
class FullStatePersistence(BaseStatePersistence[StateT, RunEndT]):
    """In memory state persistence that hold a list of snapshots."""

    deep_copy: bool = True
    """Whether to deep copy the state and nodes when storing them.

    Defaults to `True` so even if nodes or state are modified after the snapshot is taken,
    the persistence history will record the value at the time of the snapshot.
    """
    history: list[Snapshot[StateT, RunEndT]] = field(default_factory=list[Snapshot[StateT, RunEndT]])
    """List of snapshots taken during the graph run."""
    _snapshots_type_adapter: pydantic.TypeAdapter[list[Snapshot[StateT, RunEndT]]] | None = field(
        default=None, init=False, repr=False
    )

    async def snapshot_node(self, state: StateT, next_node: BaseNode[StateT, Any, RunEndT]) -> None:
        snapshot = NodeSnapshot(
            state=self._prep_state(state),
            node=next_node.deep_copy() if self.deep_copy else next_node,
        )
        self.history.append(snapshot)

    async def snapshot_node_if_new(
        self, snapshot_id: str, state: StateT, next_node: BaseNode[StateT, Any, RunEndT]
    ) -> None:
        if not any(s.id == snapshot_id for s in self.history):
            await self.snapshot_node(state, next_node)

    async def snapshot_end(self, state: StateT, end: End[RunEndT]) -> None:
        snapshot = EndSnapshot(
            state=self._prep_state(state),
            result=end.deep_copy_data() if self.deep_copy else end,
        )
        self.history.append(snapshot)

    @asynccontextmanager
    async def record_run(self, snapshot_id: str) -> AsyncIterator[None]:
        try:
            snapshot = next(s for s in self.history if s.id == snapshot_id)
        except StopIteration as e:
            raise LookupError(f'No snapshot found with id={snapshot_id!r}') from e

        assert isinstance(snapshot, NodeSnapshot), 'Only NodeSnapshot can be recorded'
        exceptions.GraphNodeStatusError.check(snapshot.status)
        snapshot.status = 'running'
        snapshot.start_ts = _utils.now_utc()
        start = perf_counter()
        try:
            yield
        except Exception:
            snapshot.duration = perf_counter() - start
            snapshot.status = 'error'
            raise
        else:
            snapshot.duration = perf_counter() - start
            snapshot.status = 'success'

    async def load_next(self) -> NodeSnapshot[StateT, RunEndT] | None:
        if snapshot := next((s for s in self.history if isinstance(s, NodeSnapshot) and s.status == 'created'), None):
            snapshot.status = 'pending'
            return copy.deepcopy(snapshot)

    async def load_all(self) -> list[Snapshot[StateT, RunEndT]]:
        return self.history

    def should_set_types(self) -> bool:
        return self._snapshots_type_adapter is None

    def set_types(self, state_type: type[StateT], run_end_type: type[RunEndT]) -> None:
        self._snapshots_type_adapter = build_snapshot_list_type_adapter(state_type, run_end_type)

    def dump_json(self, *, indent: int | None = None) -> bytes:
        """Dump the history to JSON bytes."""
        assert self._snapshots_type_adapter is not None, 'type adapter must be set to use `dump_json`'
        return self._snapshots_type_adapter.dump_json(self.history, indent=indent)

    def load_json(self, json_data: str | bytes | bytearray) -> None:
        """Load the history from JSON."""
        assert self._snapshots_type_adapter is not None, 'type adapter must be set to use `load_json`'
        self.history = self._snapshots_type_adapter.validate_json(json_data)

    def _prep_state(self, state: StateT) -> StateT:
        """Prepare state for snapshot, uses [`copy.deepcopy`][copy.deepcopy] by default."""
        if not self.deep_copy or state is None:
            return state
        else:
            return copy.deepcopy(state)
```

#### deep_copy

```python
deep_copy: bool = True
```

Whether to deep copy the state and nodes when storing them.

Defaults to `True` so even if nodes or state are modified after the snapshot is taken, the persistence history will record the value at the time of the snapshot.

#### history

```python
history: list[Snapshot[StateT, RunEndT]] = field(
    default_factory=list[Snapshot[StateT, RunEndT]]
)
```

List of snapshots taken during the graph run.

#### dump_json

```python
dump_json(*, indent: int | None = None) -> bytes
```

Dump the history to JSON bytes.

Source code in `pydantic_graph/pydantic_graph/persistence/in_mem.py`

```python
def dump_json(self, *, indent: int | None = None) -> bytes:
    """Dump the history to JSON bytes."""
    assert self._snapshots_type_adapter is not None, 'type adapter must be set to use `dump_json`'
    return self._snapshots_type_adapter.dump_json(self.history, indent=indent)
```

#### load_json

```python
load_json(json_data: str | bytes | bytearray) -> None
```

Load the history from JSON.

Source code in `pydantic_graph/pydantic_graph/persistence/in_mem.py`

```python
def load_json(self, json_data: str | bytes | bytearray) -> None:
    """Load the history from JSON."""
    assert self._snapshots_type_adapter is not None, 'type adapter must be set to use `load_json`'
    self.history = self._snapshots_type_adapter.validate_json(json_data)
```

### FileStatePersistence

Bases: `BaseStatePersistence[StateT, RunEndT]`

File based state persistence that hold graph run state in a JSON file.

Source code in `pydantic_graph/pydantic_graph/persistence/file.py`

````python
@dataclass
class FileStatePersistence(BaseStatePersistence[StateT, RunEndT]):
    """File based state persistence that hold graph run state in a JSON file."""

    json_file: Path
    """Path to the JSON file where the snapshots are stored.

    You should use a different file for each graph run, but a single file should be reused for multiple
    steps of the same run.

    For example if you have a run ID of the form `run_123abc`, you might create a `FileStatePersistence` thus:

    ```py
    from pathlib import Path

    from pydantic_graph import FullStatePersistence

    run_id = 'run_123abc'
    persistence = FullStatePersistence(Path('runs') / f'{run_id}.json')
    ```
    """
    _snapshots_type_adapter: pydantic.TypeAdapter[list[Snapshot[StateT, RunEndT]]] | None = field(
        default=None, init=False, repr=False
    )

    async def snapshot_node(self, state: StateT, next_node: BaseNode[StateT, Any, RunEndT]) -> None:
        await self._append_save(NodeSnapshot(state=state, node=next_node))

    async def snapshot_node_if_new(
        self, snapshot_id: str, state: StateT, next_node: BaseNode[StateT, Any, RunEndT]
    ) -> None:
        async with self._lock():
            snapshots = await self.load_all()
            if not any(s.id == snapshot_id for s in snapshots):  # pragma: no branch
                await self._append_save(NodeSnapshot(state=state, node=next_node), lock=False)

    async def snapshot_end(self, state: StateT, end: End[RunEndT]) -> None:
        await self._append_save(EndSnapshot(state=state, result=end))

    @asynccontextmanager
    async def record_run(self, snapshot_id: str) -> AsyncIterator[None]:
        async with self._lock():
            snapshots = await self.load_all()
            try:
                snapshot = next(s for s in snapshots if s.id == snapshot_id)
            except StopIteration as e:
                raise LookupError(f'No snapshot found with id={snapshot_id!r}') from e

            assert isinstance(snapshot, NodeSnapshot), 'Only NodeSnapshot can be recorded'
            exceptions.GraphNodeStatusError.check(snapshot.status)
            snapshot.status = 'running'
            snapshot.start_ts = _utils.now_utc()
            await self._save(snapshots)

        start = perf_counter()
        try:
            yield
        except Exception:
            duration = perf_counter() - start
            async with self._lock():
                await _graph_utils.run_in_executor(self._after_run_sync, snapshot_id, duration, 'error')
            raise
        else:
            snapshot.duration = perf_counter() - start
            async with self._lock():
                await _graph_utils.run_in_executor(self._after_run_sync, snapshot_id, snapshot.duration, 'success')

    async def load_next(self) -> NodeSnapshot[StateT, RunEndT] | None:
        async with self._lock():
            snapshots = await self.load_all()
            if snapshot := next((s for s in snapshots if isinstance(s, NodeSnapshot) and s.status == 'created'), None):
                snapshot.status = 'pending'
                await self._save(snapshots)
                return snapshot

    def should_set_types(self) -> bool:
        """Whether types need to be set."""
        return self._snapshots_type_adapter is None

    def set_types(self, state_type: type[StateT], run_end_type: type[RunEndT]) -> None:
        self._snapshots_type_adapter = build_snapshot_list_type_adapter(state_type, run_end_type)

    async def load_all(self) -> list[Snapshot[StateT, RunEndT]]:
        return await _graph_utils.run_in_executor(self._load_sync)

    def _load_sync(self) -> list[Snapshot[StateT, RunEndT]]:
        assert self._snapshots_type_adapter is not None, 'snapshots type adapter must be set'
        try:
            content = self.json_file.read_bytes()
        except FileNotFoundError:
            return []
        else:
            return self._snapshots_type_adapter.validate_json(content)

    def _after_run_sync(self, snapshot_id: str, duration: float, status: SnapshotStatus) -> None:
        snapshots = self._load_sync()
        snapshot = next(s for s in snapshots if s.id == snapshot_id)
        assert isinstance(snapshot, NodeSnapshot), 'Only NodeSnapshot can be recorded'
        snapshot.duration = duration
        snapshot.status = status
        self._save_sync(snapshots)

    async def _save(self, snapshots: list[Snapshot[StateT, RunEndT]]) -> None:
        await _graph_utils.run_in_executor(self._save_sync, snapshots)

    def _save_sync(self, snapshots: list[Snapshot[StateT, RunEndT]]) -> None:
        assert self._snapshots_type_adapter is not None, 'snapshots type adapter must be set'
        self.json_file.write_bytes(self._snapshots_type_adapter.dump_json(snapshots, indent=2))

    async def _append_save(self, snapshot: Snapshot[StateT, RunEndT], *, lock: bool = True) -> None:
        assert self._snapshots_type_adapter is not None, 'snapshots type adapter must be set'
        async with AsyncExitStack() as stack:
            if lock:
                await stack.enter_async_context(self._lock())
            snapshots = await self.load_all()
            snapshots.append(snapshot)
            await self._save(snapshots)

    @asynccontextmanager
    async def _lock(self, *, timeout: float = 1.0) -> AsyncIterator[None]:
        """Lock a file by checking and writing a `.pydantic-graph-persistence-lock` to it.

        Args:
            timeout: how long to wait for the lock

        Returns: an async context manager that holds the lock
        """
        lock_file = self.json_file.parent / f'{self.json_file.name}.pydantic-graph-persistence-lock'
        lock_id = secrets.token_urlsafe().encode()

        with anyio.fail_after(timeout):
            while not await _file_append_check(lock_file, lock_id):
                await anyio.sleep(0.01)

        try:
            yield
        finally:
            await _graph_utils.run_in_executor(lock_file.unlink, missing_ok=True)
````

#### json_file

```python
json_file: Path
```

Path to the JSON file where the snapshots are stored.

You should use a different file for each graph run, but a single file should be reused for multiple steps of the same run.

For example if you have a run ID of the form `run_123abc`, you might create a `FileStatePersistence` thus:

```py
from pathlib import Path

from pydantic_graph import FullStatePersistence

run_id = 'run_123abc'
persistence = FullStatePersistence(Path('runs') / f'{run_id}.json')
```

#### should_set_types

```python
should_set_types() -> bool
```

Whether types need to be set.

Source code in `pydantic_graph/pydantic_graph/persistence/file.py`

```python
def should_set_types(self) -> bool:
    """Whether types need to be set."""
    return self._snapshots_type_adapter is None
```
