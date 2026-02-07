# `pydantic_graph.beta.graph`

Core graph execution engine for the next version of the pydantic-graph library.

This module provides the main `Graph` class and `GraphRun` execution engine that handles the orchestration of nodes, edges, and parallel execution paths in the graph-based workflow system.

### StateT

```python
StateT = TypeVar('StateT', infer_variance=True)
```

Type variable for graph state.

### DepsT

```python
DepsT = TypeVar('DepsT', infer_variance=True)
```

Type variable for graph dependencies.

### InputT

```python
InputT = TypeVar('InputT', infer_variance=True)
```

Type variable for graph inputs.

### OutputT

```python
OutputT = TypeVar('OutputT', infer_variance=True)
```

Type variable for graph outputs.

### EndMarker

Bases: `Generic[OutputT]`

A marker indicating the end of graph execution with a final value.

EndMarker is used internally to signal that the graph has completed execution and carries the final output value.

Class Type Parameters:

| Name      | Bound or Constraints | Description                        | Default    |
| --------- | -------------------- | ---------------------------------- | ---------- |
| `OutputT` |                      | The type of the final output value | *required* |

Source code in `pydantic_graph/pydantic_graph/beta/graph.py`

```python
@dataclass(init=False)
class EndMarker(Generic[OutputT]):
    """A marker indicating the end of graph execution with a final value.

    EndMarker is used internally to signal that the graph has completed
    execution and carries the final output value.

    Type Parameters:
        OutputT: The type of the final output value
    """

    _value: OutputT
    """The final output value from the graph execution."""

    def __init__(self, value: OutputT):
        # This manually-defined initializer is necessary due to https://github.com/python/mypy/issues/17623.
        self._value = value

    @property
    def value(self) -> OutputT:
        return self._value
```

### JoinItem

An item representing data flowing into a join operation.

JoinItem carries input data from a parallel execution path to a join node, along with metadata about which execution 'fork' it originated from.

Source code in `pydantic_graph/pydantic_graph/beta/graph.py`

```python
@dataclass
class JoinItem:
    """An item representing data flowing into a join operation.

    JoinItem carries input data from a parallel execution path to a join
    node, along with metadata about which execution 'fork' it originated from.
    """

    join_id: JoinID
    """The ID of the join node this item is targeting."""

    inputs: Any
    """The input data for the join operation."""

    fork_stack: ForkStack
    """The stack of ForkStackItems that led to producing this join item."""
```

#### join_id

```python
join_id: JoinID
```

The ID of the join node this item is targeting.

#### inputs

```python
inputs: Any
```

The input data for the join operation.

#### fork_stack

```python
fork_stack: ForkStack
```

The stack of ForkStackItems that led to producing this join item.

### Graph

Bases: `Generic[StateT, DepsT, InputT, OutputT]`

A complete graph definition ready for execution.

The Graph class represents a complete workflow graph with typed inputs, outputs, state, and dependencies. It contains all nodes, edges, and metadata needed for execution.

Class Type Parameters:

| Name      | Bound or Constraints | Description                  | Default    |
| --------- | -------------------- | ---------------------------- | ---------- |
| `StateT`  |                      | The type of the graph state  | *required* |
| `DepsT`   |                      | The type of the dependencies | *required* |
| `InputT`  |                      | The type of the input data   | *required* |
| `OutputT` |                      | The type of the output data  | *required* |

Source code in `pydantic_graph/pydantic_graph/beta/graph.py`

```python
@dataclass(repr=False)
class Graph(Generic[StateT, DepsT, InputT, OutputT]):
    """A complete graph definition ready for execution.

    The Graph class represents a complete workflow graph with typed inputs,
    outputs, state, and dependencies. It contains all nodes, edges, and
    metadata needed for execution.

    Type Parameters:
        StateT: The type of the graph state
        DepsT: The type of the dependencies
        InputT: The type of the input data
        OutputT: The type of the output data
    """

    name: str | None
    """Optional name for the graph, if not provided the name will be inferred from the calling frame on the first call to a graph method."""

    state_type: type[StateT]
    """The type of the graph state."""

    deps_type: type[DepsT]
    """The type of the dependencies."""

    input_type: type[InputT]
    """The type of the input data."""

    output_type: type[OutputT]
    """The type of the output data."""

    auto_instrument: bool
    """Whether to automatically create instrumentation spans."""

    nodes: dict[NodeID, AnyNode]
    """All nodes in the graph indexed by their ID."""

    edges_by_source: dict[NodeID, list[Path]]
    """Outgoing paths from each source node."""

    parent_forks: dict[JoinID, ParentFork[NodeID]]
    """Parent fork information for each join node."""

    intermediate_join_nodes: dict[JoinID, set[JoinID]]
    """For each join, the set of other joins that appear between it and its parent fork.

    Used to determine which joins are "final" (have no other joins as intermediates) and
    which joins should preserve fork stacks when proceeding downstream."""

    def get_parent_fork(self, join_id: JoinID) -> ParentFork[NodeID]:
        """Get the parent fork information for a join node.

        Args:
            join_id: The ID of the join node

        Returns:
            The parent fork information for the join

        Raises:
            RuntimeError: If the join ID is not found or has no parent fork
        """
        result = self.parent_forks.get(join_id)
        if result is None:
            raise RuntimeError(f'Node {join_id} is not a join node or did not have a dominating fork (this is a bug)')
        return result

    def is_final_join(self, join_id: JoinID) -> bool:
        """Check if a join is 'final' (has no downstream joins with the same parent fork).

        A join is non-final if it appears as an intermediate node for another join
        with the same parent fork.

        Args:
            join_id: The ID of the join node

        Returns:
            True if the join is final, False if it's non-final
        """
        # Check if this join appears in any other join's intermediate_join_nodes
        for intermediate_joins in self.intermediate_join_nodes.values():
            if join_id in intermediate_joins:
                return False
        return True

    async def run(
        self,
        *,
        state: StateT = None,
        deps: DepsT = None,
        inputs: InputT = None,
        span: AbstractContextManager[AbstractSpan] | None = None,
        infer_name: bool = True,
    ) -> OutputT:
        """Execute the graph and return the final output.

        This is the main entry point for graph execution. It runs the graph
        to completion and returns the final output value.

        Args:
            state: The graph state instance
            deps: The dependencies instance
            inputs: The input data for the graph
            span: Optional span for tracing/instrumentation
            infer_name: Whether to infer the graph name from the calling frame.

        Returns:
            The final output from the graph execution
        """
        if infer_name and self.name is None:
            inferred_name = infer_obj_name(self, depth=2)
            if inferred_name is not None:  # pragma: no branch
                self.name = inferred_name

        async with self.iter(state=state, deps=deps, inputs=inputs, span=span, infer_name=False) as graph_run:
            # Note: This would probably be better using `async for _ in graph_run`, but this tests the `next` method,
            # which I'm less confident will be implemented correctly if not used on the critical path. We can change it
            # once we have tests, etc.
            event: Any = None
            while True:
                try:
                    event = await graph_run.next(event)
                except StopAsyncIteration:
                    assert isinstance(event, EndMarker), 'Graph run should end with an EndMarker.'
                    return cast(EndMarker[OutputT], event).value

    @asynccontextmanager
    async def iter(
        self,
        *,
        state: StateT = None,
        deps: DepsT = None,
        inputs: InputT = None,
        span: AbstractContextManager[AbstractSpan] | None = None,
        infer_name: bool = True,
    ) -> AsyncIterator[GraphRun[StateT, DepsT, OutputT]]:
        """Create an iterator for step-by-step graph execution.

        This method allows for more fine-grained control over graph execution,
        enabling inspection of intermediate states and results.

        Args:
            state: The graph state instance
            deps: The dependencies instance
            inputs: The input data for the graph
            span: Optional span for tracing/instrumentation
            infer_name: Whether to infer the graph name from the calling frame.

        Yields:
            A GraphRun instance that can be iterated for step-by-step execution
        """
        if infer_name and self.name is None:
            inferred_name = infer_obj_name(self, depth=3)  # depth=3 because asynccontextmanager adds one
            if inferred_name is not None:  # pragma: no branch
                self.name = inferred_name

        with ExitStack() as stack:
            entered_span: AbstractSpan | None = None
            if span is None:
                if self.auto_instrument:
                    entered_span = stack.enter_context(logfire_span('run graph {graph.name}', graph=self))
            else:
                entered_span = stack.enter_context(span)
            traceparent = None if entered_span is None else get_traceparent(entered_span)
            async with GraphRun[StateT, DepsT, OutputT](
                graph=self,
                state=state,
                deps=deps,
                inputs=inputs,
                traceparent=traceparent,
            ) as graph_run:
                yield graph_run

    def render(self, *, title: str | None = None, direction: StateDiagramDirection | None = None) -> str:
        """Render the graph as a Mermaid diagram string.

        Args:
            title: Optional title for the diagram
            direction: Optional direction for the diagram layout

        Returns:
            A string containing the Mermaid diagram representation
        """
        from pydantic_graph.beta.mermaid import build_mermaid_graph

        return build_mermaid_graph(self.nodes, self.edges_by_source).render(title=title, direction=direction)

    def __repr__(self) -> str:
        super_repr = super().__repr__()  # include class and memory address
        # Insert the result of calling `__str__` before the final '>' in the repr
        return f'{super_repr[:-1]}\n{self}\n{super_repr[-1]}'

    def __str__(self) -> str:
        """Return a Mermaid diagram representation of the graph.

        Returns:
            A string containing the Mermaid diagram of the graph
        """
        return self.render()
```

#### name

```python
name: str | None
```

Optional name for the graph, if not provided the name will be inferred from the calling frame on the first call to a graph method.

#### state_type

```python
state_type: type[StateT]
```

The type of the graph state.

#### deps_type

```python
deps_type: type[DepsT]
```

The type of the dependencies.

#### input_type

```python
input_type: type[InputT]
```

The type of the input data.

#### output_type

```python
output_type: type[OutputT]
```

The type of the output data.

#### auto_instrument

```python
auto_instrument: bool
```

Whether to automatically create instrumentation spans.

#### nodes

```python
nodes: dict[NodeID, AnyNode]
```

All nodes in the graph indexed by their ID.

#### edges_by_source

```python
edges_by_source: dict[NodeID, list[Path]]
```

Outgoing paths from each source node.

#### parent_forks

```python
parent_forks: dict[JoinID, ParentFork[NodeID]]
```

Parent fork information for each join node.

#### intermediate_join_nodes

```python
intermediate_join_nodes: dict[JoinID, set[JoinID]]
```

For each join, the set of other joins that appear between it and its parent fork.

Used to determine which joins are "final" (have no other joins as intermediates) and which joins should preserve fork stacks when proceeding downstream.

#### get_parent_fork

```python
get_parent_fork(join_id: JoinID) -> ParentFork[NodeID]
```

Get the parent fork information for a join node.

Parameters:

| Name      | Type     | Description             | Default    |
| --------- | -------- | ----------------------- | ---------- |
| `join_id` | `JoinID` | The ID of the join node | *required* |

Returns:

| Type                 | Description                              |
| -------------------- | ---------------------------------------- |
| `ParentFork[NodeID]` | The parent fork information for the join |

Raises:

| Type           | Description                                       |
| -------------- | ------------------------------------------------- |
| `RuntimeError` | If the join ID is not found or has no parent fork |

Source code in `pydantic_graph/pydantic_graph/beta/graph.py`

```python
def get_parent_fork(self, join_id: JoinID) -> ParentFork[NodeID]:
    """Get the parent fork information for a join node.

    Args:
        join_id: The ID of the join node

    Returns:
        The parent fork information for the join

    Raises:
        RuntimeError: If the join ID is not found or has no parent fork
    """
    result = self.parent_forks.get(join_id)
    if result is None:
        raise RuntimeError(f'Node {join_id} is not a join node or did not have a dominating fork (this is a bug)')
    return result
```

#### is_final_join

```python
is_final_join(join_id: JoinID) -> bool
```

Check if a join is 'final' (has no downstream joins with the same parent fork).

A join is non-final if it appears as an intermediate node for another join with the same parent fork.

Parameters:

| Name      | Type     | Description             | Default    |
| --------- | -------- | ----------------------- | ---------- |
| `join_id` | `JoinID` | The ID of the join node | *required* |

Returns:

| Type   | Description                                        |
| ------ | -------------------------------------------------- |
| `bool` | True if the join is final, False if it's non-final |

Source code in `pydantic_graph/pydantic_graph/beta/graph.py`

```python
def is_final_join(self, join_id: JoinID) -> bool:
    """Check if a join is 'final' (has no downstream joins with the same parent fork).

    A join is non-final if it appears as an intermediate node for another join
    with the same parent fork.

    Args:
        join_id: The ID of the join node

    Returns:
        True if the join is final, False if it's non-final
    """
    # Check if this join appears in any other join's intermediate_join_nodes
    for intermediate_joins in self.intermediate_join_nodes.values():
        if join_id in intermediate_joins:
            return False
    return True
```

#### run

```python
run(
    *,
    state: StateT = None,
    deps: DepsT = None,
    inputs: InputT = None,
    span: (
        AbstractContextManager[AbstractSpan] | None
    ) = None,
    infer_name: bool = True
) -> OutputT
```

Execute the graph and return the final output.

This is the main entry point for graph execution. It runs the graph to completion and returns the final output value.

Parameters:

| Name         | Type                                   | Description                                             | Default                                   |
| ------------ | -------------------------------------- | ------------------------------------------------------- | ----------------------------------------- |
| `state`      | `StateT`                               | The graph state instance                                | `None`                                    |
| `deps`       | `DepsT`                                | The dependencies instance                               | `None`                                    |
| `inputs`     | `InputT`                               | The input data for the graph                            | `None`                                    |
| `span`       | \`AbstractContextManager[AbstractSpan] | None\`                                                  | Optional span for tracing/instrumentation |
| `infer_name` | `bool`                                 | Whether to infer the graph name from the calling frame. | `True`                                    |

Returns:

| Type      | Description                               |
| --------- | ----------------------------------------- |
| `OutputT` | The final output from the graph execution |

Source code in `pydantic_graph/pydantic_graph/beta/graph.py`

```python
async def run(
    self,
    *,
    state: StateT = None,
    deps: DepsT = None,
    inputs: InputT = None,
    span: AbstractContextManager[AbstractSpan] | None = None,
    infer_name: bool = True,
) -> OutputT:
    """Execute the graph and return the final output.

    This is the main entry point for graph execution. It runs the graph
    to completion and returns the final output value.

    Args:
        state: The graph state instance
        deps: The dependencies instance
        inputs: The input data for the graph
        span: Optional span for tracing/instrumentation
        infer_name: Whether to infer the graph name from the calling frame.

    Returns:
        The final output from the graph execution
    """
    if infer_name and self.name is None:
        inferred_name = infer_obj_name(self, depth=2)
        if inferred_name is not None:  # pragma: no branch
            self.name = inferred_name

    async with self.iter(state=state, deps=deps, inputs=inputs, span=span, infer_name=False) as graph_run:
        # Note: This would probably be better using `async for _ in graph_run`, but this tests the `next` method,
        # which I'm less confident will be implemented correctly if not used on the critical path. We can change it
        # once we have tests, etc.
        event: Any = None
        while True:
            try:
                event = await graph_run.next(event)
            except StopAsyncIteration:
                assert isinstance(event, EndMarker), 'Graph run should end with an EndMarker.'
                return cast(EndMarker[OutputT], event).value
```

#### iter

```python
iter(
    *,
    state: StateT = None,
    deps: DepsT = None,
    inputs: InputT = None,
    span: (
        AbstractContextManager[AbstractSpan] | None
    ) = None,
    infer_name: bool = True
) -> AsyncIterator[GraphRun[StateT, DepsT, OutputT]]
```

Create an iterator for step-by-step graph execution.

This method allows for more fine-grained control over graph execution, enabling inspection of intermediate states and results.

Parameters:

| Name         | Type                                   | Description                                             | Default                                   |
| ------------ | -------------------------------------- | ------------------------------------------------------- | ----------------------------------------- |
| `state`      | `StateT`                               | The graph state instance                                | `None`                                    |
| `deps`       | `DepsT`                                | The dependencies instance                               | `None`                                    |
| `inputs`     | `InputT`                               | The input data for the graph                            | `None`                                    |
| `span`       | \`AbstractContextManager[AbstractSpan] | None\`                                                  | Optional span for tracing/instrumentation |
| `infer_name` | `bool`                                 | Whether to infer the graph name from the calling frame. | `True`                                    |

Yields:

| Type                                              | Description                                                         |
| ------------------------------------------------- | ------------------------------------------------------------------- |
| `AsyncIterator[GraphRun[StateT, DepsT, OutputT]]` | A GraphRun instance that can be iterated for step-by-step execution |

Source code in `pydantic_graph/pydantic_graph/beta/graph.py`

```python
@asynccontextmanager
async def iter(
    self,
    *,
    state: StateT = None,
    deps: DepsT = None,
    inputs: InputT = None,
    span: AbstractContextManager[AbstractSpan] | None = None,
    infer_name: bool = True,
) -> AsyncIterator[GraphRun[StateT, DepsT, OutputT]]:
    """Create an iterator for step-by-step graph execution.

    This method allows for more fine-grained control over graph execution,
    enabling inspection of intermediate states and results.

    Args:
        state: The graph state instance
        deps: The dependencies instance
        inputs: The input data for the graph
        span: Optional span for tracing/instrumentation
        infer_name: Whether to infer the graph name from the calling frame.

    Yields:
        A GraphRun instance that can be iterated for step-by-step execution
    """
    if infer_name and self.name is None:
        inferred_name = infer_obj_name(self, depth=3)  # depth=3 because asynccontextmanager adds one
        if inferred_name is not None:  # pragma: no branch
            self.name = inferred_name

    with ExitStack() as stack:
        entered_span: AbstractSpan | None = None
        if span is None:
            if self.auto_instrument:
                entered_span = stack.enter_context(logfire_span('run graph {graph.name}', graph=self))
        else:
            entered_span = stack.enter_context(span)
        traceparent = None if entered_span is None else get_traceparent(entered_span)
        async with GraphRun[StateT, DepsT, OutputT](
            graph=self,
            state=state,
            deps=deps,
            inputs=inputs,
            traceparent=traceparent,
        ) as graph_run:
            yield graph_run
```

#### render

```python
render(
    *,
    title: str | None = None,
    direction: StateDiagramDirection | None = None
) -> str
```

Render the graph as a Mermaid diagram string.

Parameters:

| Name        | Type                    | Description | Default                                   |
| ----------- | ----------------------- | ----------- | ----------------------------------------- |
| `title`     | \`str                   | None\`      | Optional title for the diagram            |
| `direction` | \`StateDiagramDirection | None\`      | Optional direction for the diagram layout |

Returns:

| Type  | Description                                            |
| ----- | ------------------------------------------------------ |
| `str` | A string containing the Mermaid diagram representation |

Source code in `pydantic_graph/pydantic_graph/beta/graph.py`

```python
def render(self, *, title: str | None = None, direction: StateDiagramDirection | None = None) -> str:
    """Render the graph as a Mermaid diagram string.

    Args:
        title: Optional title for the diagram
        direction: Optional direction for the diagram layout

    Returns:
        A string containing the Mermaid diagram representation
    """
    from pydantic_graph.beta.mermaid import build_mermaid_graph

    return build_mermaid_graph(self.nodes, self.edges_by_source).render(title=title, direction=direction)
```

#### __str__

```python
__str__() -> str
```

Return a Mermaid diagram representation of the graph.

Returns:

| Type  | Description                                          |
| ----- | ---------------------------------------------------- |
| `str` | A string containing the Mermaid diagram of the graph |

Source code in `pydantic_graph/pydantic_graph/beta/graph.py`

```python
def __str__(self) -> str:
    """Return a Mermaid diagram representation of the graph.

    Returns:
        A string containing the Mermaid diagram of the graph
    """
    return self.render()
```

### GraphTaskRequest

A request to run a task representing the execution of a node in the graph.

GraphTaskRequest encapsulates all the information needed to execute a specific node, including its inputs and the fork context it's executing within.

Source code in `pydantic_graph/pydantic_graph/beta/graph.py`

```python
@dataclass
class GraphTaskRequest:
    """A request to run a task representing the execution of a node in the graph.

    GraphTaskRequest encapsulates all the information needed to execute a specific
    node, including its inputs and the fork context it's executing within.
    """

    node_id: NodeID
    """The ID of the node to execute."""

    inputs: Any
    """The input data for the node."""

    fork_stack: ForkStack = field(repr=False)
    """Stack of forks that have been entered.

    Used by the GraphRun to decide when to proceed through joins.
    """
```

#### node_id

```python
node_id: NodeID
```

The ID of the node to execute.

#### inputs

```python
inputs: Any
```

The input data for the node.

#### fork_stack

```python
fork_stack: ForkStack = field(repr=False)
```

Stack of forks that have been entered.

Used by the GraphRun to decide when to proceed through joins.

### GraphTask

Bases: `GraphTaskRequest`

A task representing the execution of a node in the graph.

GraphTask encapsulates all the information needed to execute a specific node, including its inputs and the fork context it's executing within, and has a unique ID to identify the task within the graph run.

Source code in `pydantic_graph/pydantic_graph/beta/graph.py`

```python
@dataclass
class GraphTask(GraphTaskRequest):
    """A task representing the execution of a node in the graph.

    GraphTask encapsulates all the information needed to execute a specific
    node, including its inputs and the fork context it's executing within,
    and has a unique ID to identify the task within the graph run.
    """

    task_id: TaskID = field(repr=False)
    """Unique identifier for this task."""

    @staticmethod
    def from_request(request: GraphTaskRequest, get_task_id: Callable[[], TaskID]) -> GraphTask:
        # Don't call the get_task_id callable, this is already a task
        if isinstance(request, GraphTask):
            return request
        return GraphTask(request.node_id, request.inputs, request.fork_stack, get_task_id())
```

#### task_id

```python
task_id: TaskID = field(repr=False)
```

Unique identifier for this task.

### GraphRun

Bases: `Generic[StateT, DepsT, OutputT]`

A single execution instance of a graph.

GraphRun manages the execution state for a single run of a graph, including task scheduling, fork/join coordination, and result tracking.

Class Type Parameters:

| Name      | Bound or Constraints | Description                  | Default    |
| --------- | -------------------- | ---------------------------- | ---------- |
| `StateT`  |                      | The type of the graph state  | *required* |
| `DepsT`   |                      | The type of the dependencies | *required* |
| `OutputT` |                      | The type of the output data  | *required* |

Source code in `pydantic_graph/pydantic_graph/beta/graph.py`

```python
class GraphRun(Generic[StateT, DepsT, OutputT]):
    """A single execution instance of a graph.

    GraphRun manages the execution state for a single run of a graph,
    including task scheduling, fork/join coordination, and result tracking.

    Type Parameters:
        StateT: The type of the graph state
        DepsT: The type of the dependencies
        OutputT: The type of the output data
    """

    def __init__(
        self,
        graph: Graph[StateT, DepsT, InputT, OutputT],
        *,
        state: StateT,
        deps: DepsT,
        inputs: InputT,
        traceparent: str | None,
    ):
        """Initialize a graph run.

        Args:
            graph: The graph to execute
            state: The graph state instance
            deps: The dependencies instance
            inputs: The input data for the graph
            traceparent: Optional trace parent for instrumentation
        """
        self.graph = graph
        """The graph being executed."""

        self.state = state
        """The graph state instance."""

        self.deps = deps
        """The dependencies instance."""

        self.inputs = inputs
        """The initial input data."""

        self._active_reducers: dict[tuple[JoinID, NodeRunID], JoinState] = {}
        """Active reducers for join operations."""

        self._next: EndMarker[OutputT] | Sequence[GraphTask] | None = None
        """The next item to be processed."""

        self._next_task_id = 0
        self._next_node_run_id = 0
        initial_fork_stack: ForkStack = (ForkStackItem(StartNode.id, self._get_next_node_run_id(), 0),)
        self._first_task = GraphTask(
            node_id=StartNode.id, inputs=inputs, fork_stack=initial_fork_stack, task_id=self._get_next_task_id()
        )
        self._iterator_task_group = create_task_group()
        self._iterator_instance = _GraphIterator[StateT, DepsT, OutputT](
            self.graph,
            self.state,
            self.deps,
            self._iterator_task_group,
            self._get_next_node_run_id,
            self._get_next_task_id,
        )
        self._iterator = self._iterator_instance.iter_graph(self._first_task)

        self.__traceparent = traceparent
        self._async_exit_stack = AsyncExitStack()

    async def __aenter__(self):
        self._async_exit_stack.enter_context(_unwrap_exception_groups())
        await self._async_exit_stack.enter_async_context(self._iterator_task_group)
        await self._async_exit_stack.enter_async_context(self._iterator_context())
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any):
        await self._async_exit_stack.__aexit__(exc_type, exc_val, exc_tb)

    @asynccontextmanager
    async def _iterator_context(self):
        try:
            yield
        finally:
            self._iterator_instance.iter_stream_sender.close()
            self._iterator_instance.iter_stream_receiver.close()
            await self._iterator.aclose()

    @overload
    def _traceparent(self, *, required: Literal[False]) -> str | None: ...
    @overload
    def _traceparent(self) -> str: ...
    def _traceparent(self, *, required: bool = True) -> str | None:
        """Get the trace parent for instrumentation.

        Args:
            required: Whether to raise an error if no traceparent exists

        Returns:
            The traceparent string, or None if not required and not set

        Raises:
            GraphRuntimeError: If required is True and no traceparent exists
        """
        if self.__traceparent is None and required:  # pragma: no cover
            raise exceptions.GraphRuntimeError('No span was created for this graph run')
        return self.__traceparent

    def __aiter__(self) -> AsyncIterator[EndMarker[OutputT] | Sequence[GraphTask]]:
        """Return self as an async iterator.

        Returns:
            Self for async iteration
        """
        return self

    async def __anext__(self) -> EndMarker[OutputT] | Sequence[GraphTask]:
        """Get the next item in the async iteration.

        Returns:
            The next execution result from the graph
        """
        if self._next is None:
            self._next = await anext(self._iterator)
        else:
            self._next = await self._iterator.asend(self._next)
        return self._next

    async def next(
        self, value: EndMarker[OutputT] | Sequence[GraphTaskRequest] | None = None
    ) -> EndMarker[OutputT] | Sequence[GraphTask]:
        """Advance the graph execution by one step.

        This method allows for sending a value to the iterator, which is useful
        for resuming iteration or overriding intermediate results.

        Args:
            value: Optional value to send to the iterator

        Returns:
            The next execution result: either an EndMarker, or sequence of GraphTasks
        """
        if self._next is None:
            # Prevent `TypeError: can't send non-None value to a just-started async generator`
            # if `next` is called before the `first_node` has run.
            await anext(self)
        if value is not None:
            if isinstance(value, EndMarker):
                self._next = value
            else:
                self._next = [GraphTask.from_request(gtr, self._get_next_task_id) for gtr in value]
        return await anext(self)

    @property
    def next_task(self) -> EndMarker[OutputT] | Sequence[GraphTask]:
        """Get the next task(s) to be executed.

        Returns:
            The next execution item, or the initial task if none is set
        """
        return self._next or [self._first_task]

    @property
    def output(self) -> OutputT | None:
        """Get the final output if the graph has completed.

        Returns:
            The output value if execution is complete, None otherwise
        """
        if isinstance(self._next, EndMarker):
            return self._next.value
        return None

    def _get_next_task_id(self) -> TaskID:
        next_id = TaskID(f'task:{self._next_task_id}')
        self._next_task_id += 1
        return next_id

    def _get_next_node_run_id(self) -> NodeRunID:
        next_id = NodeRunID(f'task:{self._next_node_run_id}')
        self._next_node_run_id += 1
        return next_id
```

#### __init__

```python
__init__(
    graph: Graph[StateT, DepsT, InputT, OutputT],
    *,
    state: StateT,
    deps: DepsT,
    inputs: InputT,
    traceparent: str | None
)
```

Initialize a graph run.

Parameters:

| Name          | Type                                    | Description                  | Default                                   |
| ------------- | --------------------------------------- | ---------------------------- | ----------------------------------------- |
| `graph`       | `Graph[StateT, DepsT, InputT, OutputT]` | The graph to execute         | *required*                                |
| `state`       | `StateT`                                | The graph state instance     | *required*                                |
| `deps`        | `DepsT`                                 | The dependencies instance    | *required*                                |
| `inputs`      | `InputT`                                | The input data for the graph | *required*                                |
| `traceparent` | \`str                                   | None\`                       | Optional trace parent for instrumentation |

Source code in `pydantic_graph/pydantic_graph/beta/graph.py`

```python
def __init__(
    self,
    graph: Graph[StateT, DepsT, InputT, OutputT],
    *,
    state: StateT,
    deps: DepsT,
    inputs: InputT,
    traceparent: str | None,
):
    """Initialize a graph run.

    Args:
        graph: The graph to execute
        state: The graph state instance
        deps: The dependencies instance
        inputs: The input data for the graph
        traceparent: Optional trace parent for instrumentation
    """
    self.graph = graph
    """The graph being executed."""

    self.state = state
    """The graph state instance."""

    self.deps = deps
    """The dependencies instance."""

    self.inputs = inputs
    """The initial input data."""

    self._active_reducers: dict[tuple[JoinID, NodeRunID], JoinState] = {}
    """Active reducers for join operations."""

    self._next: EndMarker[OutputT] | Sequence[GraphTask] | None = None
    """The next item to be processed."""

    self._next_task_id = 0
    self._next_node_run_id = 0
    initial_fork_stack: ForkStack = (ForkStackItem(StartNode.id, self._get_next_node_run_id(), 0),)
    self._first_task = GraphTask(
        node_id=StartNode.id, inputs=inputs, fork_stack=initial_fork_stack, task_id=self._get_next_task_id()
    )
    self._iterator_task_group = create_task_group()
    self._iterator_instance = _GraphIterator[StateT, DepsT, OutputT](
        self.graph,
        self.state,
        self.deps,
        self._iterator_task_group,
        self._get_next_node_run_id,
        self._get_next_task_id,
    )
    self._iterator = self._iterator_instance.iter_graph(self._first_task)

    self.__traceparent = traceparent
    self._async_exit_stack = AsyncExitStack()
```

#### graph

```python
graph = graph
```

The graph being executed.

#### state

```python
state = state
```

The graph state instance.

#### deps

```python
deps = deps
```

The dependencies instance.

#### inputs

```python
inputs = inputs
```

The initial input data.

#### __aiter__

```python
__aiter__() -> (
    AsyncIterator[EndMarker[OutputT] | Sequence[GraphTask]]
)
```

Return self as an async iterator.

Returns:

| Type                                | Description             |
| ----------------------------------- | ----------------------- |
| \`AsyncIterator\[EndMarker[OutputT] | Sequence[GraphTask]\]\` |

Source code in `pydantic_graph/pydantic_graph/beta/graph.py`

```python
def __aiter__(self) -> AsyncIterator[EndMarker[OutputT] | Sequence[GraphTask]]:
    """Return self as an async iterator.

    Returns:
        Self for async iteration
    """
    return self
```

#### __anext__

```python
__anext__() -> EndMarker[OutputT] | Sequence[GraphTask]
```

Get the next item in the async iteration.

Returns:

| Type                 | Description           |
| -------------------- | --------------------- |
| \`EndMarker[OutputT] | Sequence[GraphTask]\` |

Source code in `pydantic_graph/pydantic_graph/beta/graph.py`

```python
async def __anext__(self) -> EndMarker[OutputT] | Sequence[GraphTask]:
    """Get the next item in the async iteration.

    Returns:
        The next execution result from the graph
    """
    if self._next is None:
        self._next = await anext(self._iterator)
    else:
        self._next = await self._iterator.asend(self._next)
    return self._next
```

#### next

```python
next(
    value: (
        EndMarker[OutputT]
        | Sequence[GraphTaskRequest]
        | None
    ) = None,
) -> EndMarker[OutputT] | Sequence[GraphTask]
```

Advance the graph execution by one step.

This method allows for sending a value to the iterator, which is useful for resuming iteration or overriding intermediate results.

Parameters:

| Name    | Type                 | Description                | Default |
| ------- | -------------------- | -------------------------- | ------- |
| `value` | \`EndMarker[OutputT] | Sequence[GraphTaskRequest] | None\`  |

Returns:

| Type                 | Description           |
| -------------------- | --------------------- |
| \`EndMarker[OutputT] | Sequence[GraphTask]\` |

Source code in `pydantic_graph/pydantic_graph/beta/graph.py`

```python
async def next(
    self, value: EndMarker[OutputT] | Sequence[GraphTaskRequest] | None = None
) -> EndMarker[OutputT] | Sequence[GraphTask]:
    """Advance the graph execution by one step.

    This method allows for sending a value to the iterator, which is useful
    for resuming iteration or overriding intermediate results.

    Args:
        value: Optional value to send to the iterator

    Returns:
        The next execution result: either an EndMarker, or sequence of GraphTasks
    """
    if self._next is None:
        # Prevent `TypeError: can't send non-None value to a just-started async generator`
        # if `next` is called before the `first_node` has run.
        await anext(self)
    if value is not None:
        if isinstance(value, EndMarker):
            self._next = value
        else:
            self._next = [GraphTask.from_request(gtr, self._get_next_task_id) for gtr in value]
    return await anext(self)
```

#### next_task

```python
next_task: EndMarker[OutputT] | Sequence[GraphTask]
```

Get the next task(s) to be executed.

Returns:

| Type                 | Description           |
| -------------------- | --------------------- |
| \`EndMarker[OutputT] | Sequence[GraphTask]\` |

#### output

```python
output: OutputT | None
```

Get the final output if the graph has completed.

Returns:

| Type      | Description |
| --------- | ----------- |
| \`OutputT | None\`      |
