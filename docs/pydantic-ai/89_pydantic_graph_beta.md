# `pydantic_graph.beta`

The next version of the pydantic-graph framework with enhanced graph execution capabilities.

This module provides a parallel control flow graph execution framework with support for:

- 'Step' nodes for task execution
- 'Decision' nodes for conditional branching
- 'Fork' nodes for parallel execution coordination
- 'Join' nodes and 'Reducer's for re-joining parallel executions
- Mermaid diagram generation for graph visualization

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

### GraphBuilder

Bases: `Generic[StateT, DepsT, GraphInputT, GraphOutputT]`

A builder for constructing executable graph definitions.

GraphBuilder provides a fluent interface for defining nodes, edges, and routing in a graph workflow. It supports typed state, dependencies, and input/output validation.

Class Type Parameters:

| Name           | Bound or Constraints | Description                       | Default    |
| -------------- | -------------------- | --------------------------------- | ---------- |
| `StateT`       |                      | The type of the graph state       | *required* |
| `DepsT`        |                      | The type of the dependencies      | *required* |
| `GraphInputT`  |                      | The type of the graph input data  | *required* |
| `GraphOutputT` |                      | The type of the graph output data | *required* |

Source code in `pydantic_graph/pydantic_graph/beta/graph_builder.py`

```python
@dataclass(init=False)
class GraphBuilder(Generic[StateT, DepsT, GraphInputT, GraphOutputT]):
    """A builder for constructing executable graph definitions.

    GraphBuilder provides a fluent interface for defining nodes, edges, and
    routing in a graph workflow. It supports typed state, dependencies, and
    input/output validation.

    Type Parameters:
        StateT: The type of the graph state
        DepsT: The type of the dependencies
        GraphInputT: The type of the graph input data
        GraphOutputT: The type of the graph output data
    """

    name: str | None
    """Optional name for the graph, if not provided the name will be inferred from the calling frame on the first call to a graph method."""

    state_type: TypeOrTypeExpression[StateT]
    """The type of the graph state."""

    deps_type: TypeOrTypeExpression[DepsT]
    """The type of the dependencies."""

    input_type: TypeOrTypeExpression[GraphInputT]
    """The type of the graph input data."""

    output_type: TypeOrTypeExpression[GraphOutputT]
    """The type of the graph output data."""

    auto_instrument: bool
    """Whether to automatically create instrumentation spans."""

    _nodes: dict[NodeID, AnyNode]
    """Internal storage for nodes in the graph."""

    _edges_by_source: dict[NodeID, list[Path]]
    """Internal storage for edges by source node."""

    _decision_index: int
    """Counter for generating unique decision node IDs."""

    Source = TypeAliasType('Source', SourceNode[StateT, DepsT, OutputT], type_params=(OutputT,))
    Destination = TypeAliasType('Destination', DestinationNode[StateT, DepsT, InputT], type_params=(InputT,))

    def __init__(
        self,
        *,
        name: str | None = None,
        state_type: TypeOrTypeExpression[StateT] = NoneType,
        deps_type: TypeOrTypeExpression[DepsT] = NoneType,
        input_type: TypeOrTypeExpression[GraphInputT] = NoneType,
        output_type: TypeOrTypeExpression[GraphOutputT] = NoneType,
        auto_instrument: bool = True,
    ):
        """Initialize a graph builder.

        Args:
            name: Optional name for the graph, if not provided the name will be inferred from the calling frame on the first call to a graph method.
            state_type: The type of the graph state
            deps_type: The type of the dependencies
            input_type: The type of the graph input data
            output_type: The type of the graph output data
            auto_instrument: Whether to automatically create instrumentation spans
        """
        self.name = name

        self.state_type = state_type
        self.deps_type = deps_type
        self.input_type = input_type
        self.output_type = output_type

        self.auto_instrument = auto_instrument

        self._nodes = {}
        self._edges_by_source = defaultdict(list)
        self._decision_index = 1

        self._start_node = StartNode[GraphInputT]()
        self._end_node = EndNode[GraphOutputT]()

    # Node building
    @property
    def start_node(self) -> StartNode[GraphInputT]:
        """Get the start node for the graph.

        Returns:
            The start node that receives the initial graph input
        """
        return self._start_node

    @property
    def end_node(self) -> EndNode[GraphOutputT]:
        """Get the end node for the graph.

        Returns:
            The end node that produces the final graph output
        """
        return self._end_node

    @overload
    def step(
        self,
        *,
        node_id: str | None = None,
        label: str | None = None,
    ) -> Callable[[StepFunction[StateT, DepsT, InputT, OutputT]], Step[StateT, DepsT, InputT, OutputT]]: ...
    @overload
    def step(
        self,
        call: StepFunction[StateT, DepsT, InputT, OutputT],
        *,
        node_id: str | None = None,
        label: str | None = None,
    ) -> Step[StateT, DepsT, InputT, OutputT]: ...
    def step(
        self,
        call: StepFunction[StateT, DepsT, InputT, OutputT] | None = None,
        *,
        node_id: str | None = None,
        label: str | None = None,
    ) -> (
        Step[StateT, DepsT, InputT, OutputT]
        | Callable[[StepFunction[StateT, DepsT, InputT, OutputT]], Step[StateT, DepsT, InputT, OutputT]]
    ):
        """Create a step from a step function.

        This method can be used as a decorator or called directly to create
        a step node from an async function.

        Args:
            call: The step function to wrap
            node_id: Optional ID for the node
            label: Optional human-readable label

        Returns:
            Either a Step instance or a decorator function
        """
        if call is None:

            def decorator(
                func: StepFunction[StateT, DepsT, InputT, OutputT],
            ) -> Step[StateT, DepsT, InputT, OutputT]:
                return self.step(call=func, node_id=node_id, label=label)

            return decorator

        node_id = node_id or get_callable_name(call)

        step = Step[StateT, DepsT, InputT, OutputT](id=NodeID(node_id), call=call, label=label)

        return step

    @overload
    def stream(
        self,
        *,
        node_id: str | None = None,
        label: str | None = None,
    ) -> Callable[
        [StreamFunction[StateT, DepsT, InputT, OutputT]], Step[StateT, DepsT, InputT, AsyncIterable[OutputT]]
    ]: ...
    @overload
    def stream(
        self,
        call: StreamFunction[StateT, DepsT, InputT, OutputT],
        *,
        node_id: str | None = None,
        label: str | None = None,
    ) -> Step[StateT, DepsT, InputT, AsyncIterable[OutputT]]: ...
    @overload
    def stream(
        self,
        call: StreamFunction[StateT, DepsT, InputT, OutputT] | None = None,
        *,
        node_id: str | None = None,
        label: str | None = None,
    ) -> (
        Step[StateT, DepsT, InputT, AsyncIterable[OutputT]]
        | Callable[
            [StreamFunction[StateT, DepsT, InputT, OutputT]],
            Step[StateT, DepsT, InputT, AsyncIterable[OutputT]],
        ]
    ): ...
    def stream(
        self,
        call: StreamFunction[StateT, DepsT, InputT, OutputT] | None = None,
        *,
        node_id: str | None = None,
        label: str | None = None,
    ) -> (
        Step[StateT, DepsT, InputT, AsyncIterable[OutputT]]
        | Callable[
            [StreamFunction[StateT, DepsT, InputT, OutputT]],
            Step[StateT, DepsT, InputT, AsyncIterable[OutputT]],
        ]
    ):
        """Create a step from an async iterator (which functions like a "stream").

        This method can be used as a decorator or called directly to create
        a step node from an async function.

        Args:
            call: The step function to wrap
            node_id: Optional ID for the node
            label: Optional human-readable label

        Returns:
            Either a Step instance or a decorator function
        """
        if call is None:

            def decorator(
                func: StreamFunction[StateT, DepsT, InputT, OutputT],
            ) -> Step[StateT, DepsT, InputT, AsyncIterable[OutputT]]:
                return self.stream(call=func, node_id=node_id, label=label)

            return decorator

        # We need to wrap the call so that we can call `await` even though the result is an async iterator
        async def wrapper(ctx: StepContext[StateT, DepsT, InputT]):
            return call(ctx)

        node_id = node_id or get_callable_name(call)

        return self.step(call=wrapper, node_id=node_id, label=label)

    @overload
    def join(
        self,
        reducer: ReducerFunction[StateT, DepsT, InputT, OutputT],
        *,
        initial: OutputT,
        node_id: str | None = None,
        parent_fork_id: str | None = None,
        preferred_parent_fork: Literal['farthest', 'closest'] = 'farthest',
    ) -> Join[StateT, DepsT, InputT, OutputT]: ...
    @overload
    def join(
        self,
        reducer: ReducerFunction[StateT, DepsT, InputT, OutputT],
        *,
        initial_factory: Callable[[], OutputT],
        node_id: str | None = None,
        parent_fork_id: str | None = None,
        preferred_parent_fork: Literal['farthest', 'closest'] = 'farthest',
    ) -> Join[StateT, DepsT, InputT, OutputT]: ...

    def join(
        self,
        reducer: ReducerFunction[StateT, DepsT, InputT, OutputT],
        *,
        initial: OutputT | Unset = UNSET,
        initial_factory: Callable[[], OutputT] | Unset = UNSET,
        node_id: str | None = None,
        parent_fork_id: str | None = None,
        preferred_parent_fork: Literal['farthest', 'closest'] = 'farthest',
    ) -> Join[StateT, DepsT, InputT, OutputT]:
        if initial_factory is UNSET:
            initial_factory = lambda: initial  # pyright: ignore[reportAssignmentType]  # noqa: E731

        return Join[StateT, DepsT, InputT, OutputT](
            id=JoinID(NodeID(node_id or generate_placeholder_node_id(get_callable_name(reducer)))),
            reducer=reducer,
            initial_factory=cast(Callable[[], OutputT], initial_factory),
            parent_fork_id=ForkID(parent_fork_id) if parent_fork_id is not None else None,
            preferred_parent_fork=preferred_parent_fork,
        )

    # Edge building
    def add(self, *edges: EdgePath[StateT, DepsT]) -> None:  # noqa: C901
        """Add one or more edge paths to the graph.

        This method processes edge paths and automatically creates any necessary
        fork nodes for broadcasts and maps.

        Args:
            *edges: The edge paths to add to the graph
        """

        def _handle_path(p: Path):
            """Process a path and create necessary fork nodes.

            Args:
                p: The path to process
            """
            for item in p.items:
                if isinstance(item, BroadcastMarker):
                    new_node = Fork[Any, Any](id=item.fork_id, is_map=False, downstream_join_id=None)
                    self._insert_node(new_node)
                    for path in item.paths:
                        _handle_path(Path(items=[*path.items]))
                elif isinstance(item, MapMarker):
                    new_node = Fork[Any, Any](id=item.fork_id, is_map=True, downstream_join_id=item.downstream_join_id)
                    self._insert_node(new_node)
                elif isinstance(item, DestinationMarker):
                    pass

        def _handle_destination_node(d: AnyDestinationNode):
            if id(d) in destination_ids:
                return  # prevent infinite recursion if there is a cycle of decisions

            destination_ids.add(id(d))
            destinations.append(d)
            self._insert_node(d)
            if isinstance(d, Decision):
                for branch in d.branches:
                    _handle_path(branch.path)
                    for d2 in branch.destinations:
                        _handle_destination_node(d2)

        destination_ids = set[int]()
        destinations: list[AnyDestinationNode] = []
        for edge in edges:
            for source_node in edge.sources:
                self._insert_node(source_node)
                self._edges_by_source[source_node.id].append(edge.path)
            for destination_node in edge.destinations:
                _handle_destination_node(destination_node)
            _handle_path(edge.path)

        # Automatically create edges from step function return hints including `BaseNode`s
        for destination in destinations:
            if not isinstance(destination, Step) or isinstance(destination, NodeStep):
                continue
            parent_namespace = _utils.get_parent_namespace(inspect.currentframe())
            type_hints = get_type_hints(destination.call, localns=parent_namespace, include_extras=True)
            try:
                return_hint = type_hints['return']
            except KeyError:
                pass
            else:
                edge = self._edge_from_return_hint(destination, return_hint)
                if edge is not None:
                    self.add(edge)

    def add_edge(self, source: Source[T], destination: Destination[T], *, label: str | None = None) -> None:
        """Add a simple edge between two nodes.

        Args:
            source: The source node
            destination: The destination node
            label: Optional label for the edge
        """
        builder = self.edge_from(source)
        if label is not None:
            builder = builder.label(label)
        self.add(builder.to(destination))

    def add_mapping_edge(
        self,
        source: Source[Iterable[T]],
        map_to: Destination[T],
        *,
        pre_map_label: str | None = None,
        post_map_label: str | None = None,
        fork_id: ForkID | None = None,
        downstream_join_id: JoinID | None = None,
    ) -> None:
        """Add an edge that maps iterable data across parallel paths.

        Args:
            source: The source node that produces iterable data
            map_to: The destination node that receives individual items
            pre_map_label: Optional label before the map operation
            post_map_label: Optional label after the map operation
            fork_id: Optional ID for the fork node produced for this map operation
            downstream_join_id: Optional ID of a join node that will always be downstream of this map.
                Specifying this ensures correct handling if you try to map an empty iterable.
        """
        builder = self.edge_from(source)
        if pre_map_label is not None:
            builder = builder.label(pre_map_label)
        builder = builder.map(fork_id=fork_id, downstream_join_id=downstream_join_id)
        if post_map_label is not None:
            builder = builder.label(post_map_label)
        self.add(builder.to(map_to))

    # TODO(DavidM): Support adding subgraphs; I think this behaves like a step with the same inputs/outputs but gets rendered as a subgraph in mermaid

    def edge_from(self, *sources: Source[SourceOutputT]) -> EdgePathBuilder[StateT, DepsT, SourceOutputT]:
        """Create an edge path builder starting from the given source nodes.

        Args:
            *sources: The source nodes to start the edge path from

        Returns:
            An EdgePathBuilder for constructing the complete edge path
        """
        return EdgePathBuilder[StateT, DepsT, SourceOutputT](
            sources=sources, path_builder=PathBuilder(working_items=[])
        )

    def decision(self, *, note: str | None = None, node_id: str | None = None) -> Decision[StateT, DepsT, Never]:
        """Create a new decision node.

        Args:
            note: Optional note to describe the decision logic
            node_id: Optional ID for the node produced for this decision logic

        Returns:
            A new Decision node with no branches
        """
        return Decision(id=NodeID(node_id or generate_placeholder_node_id('decision')), branches=[], note=note)

    def match(
        self,
        source: TypeOrTypeExpression[SourceT],
        *,
        matches: Callable[[Any], bool] | None = None,
    ) -> DecisionBranchBuilder[StateT, DepsT, SourceT, SourceT, Never]:
        """Create a decision branch matcher.

        Args:
            source: The type or type expression to match against
            matches: Optional custom matching function

        Returns:
            A DecisionBranchBuilder for constructing the branch
        """
        # Note, the following node_id really is just a placeholder and shouldn't end up in the final graph
        # This is why we don't expose a way for end users to override the value used here.
        node_id = NodeID(generate_placeholder_node_id('match_decision'))
        decision = Decision[StateT, DepsT, Never](id=node_id, branches=[], note=None)
        new_path_builder = PathBuilder[StateT, DepsT, SourceT](working_items=[])
        return DecisionBranchBuilder(decision=decision, source=source, matches=matches, path_builder=new_path_builder)

    def match_node(
        self,
        source: type[SourceNodeT],
        *,
        matches: Callable[[Any], bool] | None = None,
    ) -> DecisionBranch[SourceNodeT]:
        """Create a decision branch for BaseNode subclasses.

        This is similar to match() but specifically designed for matching
        against BaseNode types from the v1 system.

        Args:
            source: The BaseNode subclass to match against
            matches: Optional custom matching function

        Returns:
            A DecisionBranch for the BaseNode type
        """
        node = NodeStep(source)
        path = Path(items=[DestinationMarker(node.id)])
        return DecisionBranch(source=source, matches=matches, path=path, destinations=[node])

    def node(
        self,
        node_type: type[BaseNode[StateT, DepsT, GraphOutputT]],
    ) -> EdgePath[StateT, DepsT]:
        """Create an edge path from a BaseNode class.

        This method integrates v1-style BaseNode classes into the v2 graph
        system by analyzing their type hints and creating appropriate edges.

        Args:
            node_type: The BaseNode subclass to integrate

        Returns:
            An EdgePath representing the node and its connections

        Raises:
            GraphSetupError: If the node type is missing required type hints
        """
        parent_namespace = _utils.get_parent_namespace(inspect.currentframe())
        type_hints = get_type_hints(node_type.run, localns=parent_namespace, include_extras=True)
        try:
            return_hint = type_hints['return']
        except KeyError as e:  # pragma: no cover
            raise exceptions.GraphSetupError(
                f'Node {node_type} is missing a return type hint on its `run` method'
            ) from e

        node = NodeStep(node_type)

        edge = self._edge_from_return_hint(node, return_hint)
        if not edge:  # pragma: no cover
            raise exceptions.GraphSetupError(f'Node {node_type} is missing a return type hint on its `run` method')

        return edge

    # Helpers
    def _insert_node(self, node: AnyNode) -> None:
        """Insert a node into the graph, checking for ID conflicts.

        Args:
            node: The node to insert

        Raises:
            ValueError: If a different node with the same ID already exists
        """
        existing = self._nodes.get(node.id)
        if existing is None:
            self._nodes[node.id] = node
        elif isinstance(existing, NodeStep) and isinstance(node, NodeStep) and existing.node_type is node.node_type:
            pass
        elif existing is not node:
            raise GraphBuildingError(
                f'All nodes must have unique node IDs. {node.id!r} was the ID for {existing} and {node}'
            )

    def _edge_from_return_hint(
        self, node: SourceNode[StateT, DepsT, Any], return_hint: TypeOrTypeExpression[Any]
    ) -> EdgePath[StateT, DepsT] | None:
        """Create edges from a return type hint.

        This method analyzes return type hints from step functions or node methods
        to automatically create appropriate edges in the graph.

        Args:
            node: The source node
            return_hint: The return type hint to analyze

        Returns:
            An EdgePath if edges can be inferred, None otherwise

        Raises:
            GraphSetupError: If the return type hint is invalid or incomplete
        """
        destinations: list[AnyDestinationNode] = []
        union_args = _utils.get_union_args(return_hint)
        for return_type in union_args:
            return_type, annotations = _utils.unpack_annotated(return_type)
            return_type_origin = get_origin(return_type) or return_type
            if return_type_origin is End:
                destinations.append(self.end_node)
            elif return_type_origin is BaseNode:
                raise exceptions.GraphSetupError(  # pragma: no cover
                    f'Node {node} return type hint includes a plain `BaseNode`. '
                    'Edge inference requires each possible returned `BaseNode` subclass to be listed explicitly.'
                )
            elif return_type_origin is StepNode:
                step = cast(
                    Step[StateT, DepsT, Any, Any] | None,
                    next((a for a in annotations if isinstance(a, Step)), None),  # pyright: ignore[reportUnknownArgumentType]
                )
                if step is None:
                    raise exceptions.GraphSetupError(  # pragma: no cover
                        f'Node {node} return type hint includes a `StepNode` without a `Step` annotation. '
                        'When returning `my_step.as_node()`, use `Annotated[StepNode[StateT, DepsT], my_step]` as the return type hint.'
                    )
                destinations.append(step)
            elif return_type_origin is JoinNode:
                join = cast(
                    Join[StateT, DepsT, Any, Any] | None,
                    next((a for a in annotations if isinstance(a, Join)), None),  # pyright: ignore[reportUnknownArgumentType]
                )
                if join is None:
                    raise exceptions.GraphSetupError(  # pragma: no cover
                        f'Node {node} return type hint includes a `JoinNode` without a `Join` annotation. '
                        'When returning `my_join.as_node()`, use `Annotated[JoinNode[StateT, DepsT], my_join]` as the return type hint.'
                    )
                destinations.append(join)
            elif inspect.isclass(return_type_origin) and issubclass(return_type_origin, BaseNode):
                destinations.append(NodeStep(return_type))

        if len(destinations) < len(union_args):
            # Only build edges if all the return types are nodes
            return None

        edge = self.edge_from(node)
        if len(destinations) == 1:
            return edge.to(destinations[0])
        else:
            decision = self.decision()
            for destination in destinations:
                # We don't actually use this decision mechanism, but we need to build the edges for parent-fork finding
                decision = decision.branch(self.match(NoneType).to(destination))
            return edge.to(decision)

    # Graph building
    def build(self, validate_graph_structure: bool = True) -> Graph[StateT, DepsT, GraphInputT, GraphOutputT]:
        """Build the final executable graph from the accumulated nodes and edges.

        This method performs validation, normalization, and analysis of the graph
        structure to create a complete, executable graph instance.

        Args:
            validate_graph_structure: whether to perform validation of the graph structure
                See the docstring of _validate_graph_structure below for more details.

        Returns:
            A complete Graph instance ready for execution

        Raises:
            ValueError: If the graph structure is invalid (e.g., join without parent fork)
        """
        nodes = self._nodes
        edges_by_source = self._edges_by_source

        nodes, edges_by_source = _replace_placeholder_node_ids(nodes, edges_by_source)
        nodes, edges_by_source = _flatten_paths(nodes, edges_by_source)
        nodes, edges_by_source = _normalize_forks(nodes, edges_by_source)
        if validate_graph_structure:
            _validate_graph_structure(nodes, edges_by_source)
        parent_forks = _collect_dominating_forks(nodes, edges_by_source)
        intermediate_join_nodes = _compute_intermediate_join_nodes(nodes, parent_forks)

        return Graph[StateT, DepsT, GraphInputT, GraphOutputT](
            name=self.name,
            state_type=unpack_type_expression(self.state_type),
            deps_type=unpack_type_expression(self.deps_type),
            input_type=unpack_type_expression(self.input_type),
            output_type=unpack_type_expression(self.output_type),
            nodes=nodes,
            edges_by_source=edges_by_source,
            parent_forks=parent_forks,
            intermediate_join_nodes=intermediate_join_nodes,
            auto_instrument=self.auto_instrument,
        )
```

#### name

```python
name: str | None = name
```

Optional name for the graph, if not provided the name will be inferred from the calling frame on the first call to a graph method.

#### state_type

```python
state_type: TypeOrTypeExpression[StateT] = state_type
```

The type of the graph state.

#### deps_type

```python
deps_type: TypeOrTypeExpression[DepsT] = deps_type
```

The type of the dependencies.

#### input_type

```python
input_type: TypeOrTypeExpression[GraphInputT] = input_type
```

The type of the graph input data.

#### output_type

```python
output_type: TypeOrTypeExpression[GraphOutputT] = (
    output_type
)
```

The type of the graph output data.

#### auto_instrument

```python
auto_instrument: bool = auto_instrument
```

Whether to automatically create instrumentation spans.

#### __init__

```python
__init__(
    *,
    name: str | None = None,
    state_type: TypeOrTypeExpression[StateT] = NoneType,
    deps_type: TypeOrTypeExpression[DepsT] = NoneType,
    input_type: TypeOrTypeExpression[
        GraphInputT
    ] = NoneType,
    output_type: TypeOrTypeExpression[
        GraphOutputT
    ] = NoneType,
    auto_instrument: bool = True
)
```

Initialize a graph builder.

Parameters:

| Name              | Type                                 | Description                                           | Default                                                                                                                            |
| ----------------- | ------------------------------------ | ----------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| `name`            | \`str                                | None\`                                                | Optional name for the graph, if not provided the name will be inferred from the calling frame on the first call to a graph method. |
| `state_type`      | `TypeOrTypeExpression[StateT]`       | The type of the graph state                           | `NoneType`                                                                                                                         |
| `deps_type`       | `TypeOrTypeExpression[DepsT]`        | The type of the dependencies                          | `NoneType`                                                                                                                         |
| `input_type`      | `TypeOrTypeExpression[GraphInputT]`  | The type of the graph input data                      | `NoneType`                                                                                                                         |
| `output_type`     | `TypeOrTypeExpression[GraphOutputT]` | The type of the graph output data                     | `NoneType`                                                                                                                         |
| `auto_instrument` | `bool`                               | Whether to automatically create instrumentation spans | `True`                                                                                                                             |

Source code in `pydantic_graph/pydantic_graph/beta/graph_builder.py`

```python
def __init__(
    self,
    *,
    name: str | None = None,
    state_type: TypeOrTypeExpression[StateT] = NoneType,
    deps_type: TypeOrTypeExpression[DepsT] = NoneType,
    input_type: TypeOrTypeExpression[GraphInputT] = NoneType,
    output_type: TypeOrTypeExpression[GraphOutputT] = NoneType,
    auto_instrument: bool = True,
):
    """Initialize a graph builder.

    Args:
        name: Optional name for the graph, if not provided the name will be inferred from the calling frame on the first call to a graph method.
        state_type: The type of the graph state
        deps_type: The type of the dependencies
        input_type: The type of the graph input data
        output_type: The type of the graph output data
        auto_instrument: Whether to automatically create instrumentation spans
    """
    self.name = name

    self.state_type = state_type
    self.deps_type = deps_type
    self.input_type = input_type
    self.output_type = output_type

    self.auto_instrument = auto_instrument

    self._nodes = {}
    self._edges_by_source = defaultdict(list)
    self._decision_index = 1

    self._start_node = StartNode[GraphInputT]()
    self._end_node = EndNode[GraphOutputT]()
```

#### start_node

```python
start_node: StartNode[GraphInputT]
```

Get the start node for the graph.

Returns:

| Type                     | Description                                          |
| ------------------------ | ---------------------------------------------------- |
| `StartNode[GraphInputT]` | The start node that receives the initial graph input |

#### end_node

```python
end_node: EndNode[GraphOutputT]
```

Get the end node for the graph.

Returns:

| Type                    | Description                                       |
| ----------------------- | ------------------------------------------------- |
| `EndNode[GraphOutputT]` | The end node that produces the final graph output |

#### step

```python
step(
    *, node_id: str | None = None, label: str | None = None
) -> Callable[
    [StepFunction[StateT, DepsT, InputT, OutputT]],
    Step[StateT, DepsT, InputT, OutputT],
]
```

```python
step(
    call: StepFunction[StateT, DepsT, InputT, OutputT],
    *,
    node_id: str | None = None,
    label: str | None = None
) -> Step[StateT, DepsT, InputT, OutputT]
```

```python
step(
    call: (
        StepFunction[StateT, DepsT, InputT, OutputT] | None
    ) = None,
    *,
    node_id: str | None = None,
    label: str | None = None
) -> (
    Step[StateT, DepsT, InputT, OutputT]
    | Callable[
        [StepFunction[StateT, DepsT, InputT, OutputT]],
        Step[StateT, DepsT, InputT, OutputT],
    ]
)
```

Create a step from a step function.

This method can be used as a decorator or called directly to create a step node from an async function.

Parameters:

| Name      | Type                                           | Description | Default                       |
| --------- | ---------------------------------------------- | ----------- | ----------------------------- |
| `call`    | \`StepFunction[StateT, DepsT, InputT, OutputT] | None\`      | The step function to wrap     |
| `node_id` | \`str                                          | None\`      | Optional ID for the node      |
| `label`   | \`str                                          | None\`      | Optional human-readable label |

Returns:

| Type                                   | Description                                                                                          |
| -------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| \`Step[StateT, DepsT, InputT, OutputT] | Callable\[\[StepFunction[StateT, DepsT, InputT, OutputT]\], Step[StateT, DepsT, InputT, OutputT]\]\` |

Source code in `pydantic_graph/pydantic_graph/beta/graph_builder.py`

```python
def step(
    self,
    call: StepFunction[StateT, DepsT, InputT, OutputT] | None = None,
    *,
    node_id: str | None = None,
    label: str | None = None,
) -> (
    Step[StateT, DepsT, InputT, OutputT]
    | Callable[[StepFunction[StateT, DepsT, InputT, OutputT]], Step[StateT, DepsT, InputT, OutputT]]
):
    """Create a step from a step function.

    This method can be used as a decorator or called directly to create
    a step node from an async function.

    Args:
        call: The step function to wrap
        node_id: Optional ID for the node
        label: Optional human-readable label

    Returns:
        Either a Step instance or a decorator function
    """
    if call is None:

        def decorator(
            func: StepFunction[StateT, DepsT, InputT, OutputT],
        ) -> Step[StateT, DepsT, InputT, OutputT]:
            return self.step(call=func, node_id=node_id, label=label)

        return decorator

    node_id = node_id or get_callable_name(call)

    step = Step[StateT, DepsT, InputT, OutputT](id=NodeID(node_id), call=call, label=label)

    return step
```

#### stream

```python
stream(
    *, node_id: str | None = None, label: str | None = None
) -> Callable[
    [StreamFunction[StateT, DepsT, InputT, OutputT]],
    Step[StateT, DepsT, InputT, AsyncIterable[OutputT]],
]
```

```python
stream(
    call: StreamFunction[StateT, DepsT, InputT, OutputT],
    *,
    node_id: str | None = None,
    label: str | None = None
) -> Step[StateT, DepsT, InputT, AsyncIterable[OutputT]]
```

```python
stream(
    call: (
        StreamFunction[StateT, DepsT, InputT, OutputT]
        | None
    ) = None,
    *,
    node_id: str | None = None,
    label: str | None = None
) -> (
    Step[StateT, DepsT, InputT, AsyncIterable[OutputT]]
    | Callable[
        [StreamFunction[StateT, DepsT, InputT, OutputT]],
        Step[StateT, DepsT, InputT, AsyncIterable[OutputT]],
    ]
)
```

```python
stream(
    call: (
        StreamFunction[StateT, DepsT, InputT, OutputT]
        | None
    ) = None,
    *,
    node_id: str | None = None,
    label: str | None = None
) -> (
    Step[StateT, DepsT, InputT, AsyncIterable[OutputT]]
    | Callable[
        [StreamFunction[StateT, DepsT, InputT, OutputT]],
        Step[StateT, DepsT, InputT, AsyncIterable[OutputT]],
    ]
)
```

Create a step from an async iterator (which functions like a "stream").

This method can be used as a decorator or called directly to create a step node from an async function.

Parameters:

| Name      | Type                                             | Description | Default                       |
| --------- | ------------------------------------------------ | ----------- | ----------------------------- |
| `call`    | \`StreamFunction[StateT, DepsT, InputT, OutputT] | None\`      | The step function to wrap     |
| `node_id` | \`str                                            | None\`      | Optional ID for the node      |
| `label`   | \`str                                            | None\`      | Optional human-readable label |

Returns:

| Type                                                    | Description                                                                                                             |
| ------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| \`Step\[StateT, DepsT, InputT, AsyncIterable[OutputT]\] | Callable\[\[StreamFunction[StateT, DepsT, InputT, OutputT]\], Step\[StateT, DepsT, InputT, AsyncIterable[OutputT]\]\]\` |

Source code in `pydantic_graph/pydantic_graph/beta/graph_builder.py`

```python
def stream(
    self,
    call: StreamFunction[StateT, DepsT, InputT, OutputT] | None = None,
    *,
    node_id: str | None = None,
    label: str | None = None,
) -> (
    Step[StateT, DepsT, InputT, AsyncIterable[OutputT]]
    | Callable[
        [StreamFunction[StateT, DepsT, InputT, OutputT]],
        Step[StateT, DepsT, InputT, AsyncIterable[OutputT]],
    ]
):
    """Create a step from an async iterator (which functions like a "stream").

    This method can be used as a decorator or called directly to create
    a step node from an async function.

    Args:
        call: The step function to wrap
        node_id: Optional ID for the node
        label: Optional human-readable label

    Returns:
        Either a Step instance or a decorator function
    """
    if call is None:

        def decorator(
            func: StreamFunction[StateT, DepsT, InputT, OutputT],
        ) -> Step[StateT, DepsT, InputT, AsyncIterable[OutputT]]:
            return self.stream(call=func, node_id=node_id, label=label)

        return decorator

    # We need to wrap the call so that we can call `await` even though the result is an async iterator
    async def wrapper(ctx: StepContext[StateT, DepsT, InputT]):
        return call(ctx)

    node_id = node_id or get_callable_name(call)

    return self.step(call=wrapper, node_id=node_id, label=label)
```

#### add

```python
add(*edges: EdgePath[StateT, DepsT]) -> None
```

Add one or more edge paths to the graph.

This method processes edge paths and automatically creates any necessary fork nodes for broadcasts and maps.

Parameters:

| Name     | Type                      | Description                        | Default |
| -------- | ------------------------- | ---------------------------------- | ------- |
| `*edges` | `EdgePath[StateT, DepsT]` | The edge paths to add to the graph | `()`    |

Source code in `pydantic_graph/pydantic_graph/beta/graph_builder.py`

```python
def add(self, *edges: EdgePath[StateT, DepsT]) -> None:  # noqa: C901
    """Add one or more edge paths to the graph.

    This method processes edge paths and automatically creates any necessary
    fork nodes for broadcasts and maps.

    Args:
        *edges: The edge paths to add to the graph
    """

    def _handle_path(p: Path):
        """Process a path and create necessary fork nodes.

        Args:
            p: The path to process
        """
        for item in p.items:
            if isinstance(item, BroadcastMarker):
                new_node = Fork[Any, Any](id=item.fork_id, is_map=False, downstream_join_id=None)
                self._insert_node(new_node)
                for path in item.paths:
                    _handle_path(Path(items=[*path.items]))
            elif isinstance(item, MapMarker):
                new_node = Fork[Any, Any](id=item.fork_id, is_map=True, downstream_join_id=item.downstream_join_id)
                self._insert_node(new_node)
            elif isinstance(item, DestinationMarker):
                pass

    def _handle_destination_node(d: AnyDestinationNode):
        if id(d) in destination_ids:
            return  # prevent infinite recursion if there is a cycle of decisions

        destination_ids.add(id(d))
        destinations.append(d)
        self._insert_node(d)
        if isinstance(d, Decision):
            for branch in d.branches:
                _handle_path(branch.path)
                for d2 in branch.destinations:
                    _handle_destination_node(d2)

    destination_ids = set[int]()
    destinations: list[AnyDestinationNode] = []
    for edge in edges:
        for source_node in edge.sources:
            self._insert_node(source_node)
            self._edges_by_source[source_node.id].append(edge.path)
        for destination_node in edge.destinations:
            _handle_destination_node(destination_node)
        _handle_path(edge.path)

    # Automatically create edges from step function return hints including `BaseNode`s
    for destination in destinations:
        if not isinstance(destination, Step) or isinstance(destination, NodeStep):
            continue
        parent_namespace = _utils.get_parent_namespace(inspect.currentframe())
        type_hints = get_type_hints(destination.call, localns=parent_namespace, include_extras=True)
        try:
            return_hint = type_hints['return']
        except KeyError:
            pass
        else:
            edge = self._edge_from_return_hint(destination, return_hint)
            if edge is not None:
                self.add(edge)
```

#### add_edge

```python
add_edge(
    source: Source[T],
    destination: Destination[T],
    *,
    label: str | None = None
) -> None
```

Add a simple edge between two nodes.

Parameters:

| Name          | Type             | Description          | Default                     |
| ------------- | ---------------- | -------------------- | --------------------------- |
| `source`      | `Source[T]`      | The source node      | *required*                  |
| `destination` | `Destination[T]` | The destination node | *required*                  |
| `label`       | \`str            | None\`               | Optional label for the edge |

Source code in `pydantic_graph/pydantic_graph/beta/graph_builder.py`

```python
def add_edge(self, source: Source[T], destination: Destination[T], *, label: str | None = None) -> None:
    """Add a simple edge between two nodes.

    Args:
        source: The source node
        destination: The destination node
        label: Optional label for the edge
    """
    builder = self.edge_from(source)
    if label is not None:
        builder = builder.label(label)
    self.add(builder.to(destination))
```

#### add_mapping_edge

```python
add_mapping_edge(
    source: Source[Iterable[T]],
    map_to: Destination[T],
    *,
    pre_map_label: str | None = None,
    post_map_label: str | None = None,
    fork_id: ForkID | None = None,
    downstream_join_id: JoinID | None = None
) -> None
```

Add an edge that maps iterable data across parallel paths.

Parameters:

| Name                 | Type                  | Description                                         | Default                                                                                                                                              |
| -------------------- | --------------------- | --------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| `source`             | `Source[Iterable[T]]` | The source node that produces iterable data         | *required*                                                                                                                                           |
| `map_to`             | `Destination[T]`      | The destination node that receives individual items | *required*                                                                                                                                           |
| `pre_map_label`      | \`str                 | None\`                                              | Optional label before the map operation                                                                                                              |
| `post_map_label`     | \`str                 | None\`                                              | Optional label after the map operation                                                                                                               |
| `fork_id`            | \`ForkID              | None\`                                              | Optional ID for the fork node produced for this map operation                                                                                        |
| `downstream_join_id` | \`JoinID              | None\`                                              | Optional ID of a join node that will always be downstream of this map. Specifying this ensures correct handling if you try to map an empty iterable. |

Source code in `pydantic_graph/pydantic_graph/beta/graph_builder.py`

```python
def add_mapping_edge(
    self,
    source: Source[Iterable[T]],
    map_to: Destination[T],
    *,
    pre_map_label: str | None = None,
    post_map_label: str | None = None,
    fork_id: ForkID | None = None,
    downstream_join_id: JoinID | None = None,
) -> None:
    """Add an edge that maps iterable data across parallel paths.

    Args:
        source: The source node that produces iterable data
        map_to: The destination node that receives individual items
        pre_map_label: Optional label before the map operation
        post_map_label: Optional label after the map operation
        fork_id: Optional ID for the fork node produced for this map operation
        downstream_join_id: Optional ID of a join node that will always be downstream of this map.
            Specifying this ensures correct handling if you try to map an empty iterable.
    """
    builder = self.edge_from(source)
    if pre_map_label is not None:
        builder = builder.label(pre_map_label)
    builder = builder.map(fork_id=fork_id, downstream_join_id=downstream_join_id)
    if post_map_label is not None:
        builder = builder.label(post_map_label)
    self.add(builder.to(map_to))
```

#### edge_from

```python
edge_from(
    *sources: Source[SourceOutputT],
) -> EdgePathBuilder[StateT, DepsT, SourceOutputT]
```

Create an edge path builder starting from the given source nodes.

Parameters:

| Name       | Type                    | Description                                  | Default |
| ---------- | ----------------------- | -------------------------------------------- | ------- |
| `*sources` | `Source[SourceOutputT]` | The source nodes to start the edge path from | `()`    |

Returns:

| Type                                            | Description                                                |
| ----------------------------------------------- | ---------------------------------------------------------- |
| `EdgePathBuilder[StateT, DepsT, SourceOutputT]` | An EdgePathBuilder for constructing the complete edge path |

Source code in `pydantic_graph/pydantic_graph/beta/graph_builder.py`

```python
def edge_from(self, *sources: Source[SourceOutputT]) -> EdgePathBuilder[StateT, DepsT, SourceOutputT]:
    """Create an edge path builder starting from the given source nodes.

    Args:
        *sources: The source nodes to start the edge path from

    Returns:
        An EdgePathBuilder for constructing the complete edge path
    """
    return EdgePathBuilder[StateT, DepsT, SourceOutputT](
        sources=sources, path_builder=PathBuilder(working_items=[])
    )
```

#### decision

```python
decision(
    *, note: str | None = None, node_id: str | None = None
) -> Decision[StateT, DepsT, Never]
```

Create a new decision node.

Parameters:

| Name      | Type  | Description | Default                                                   |
| --------- | ----- | ----------- | --------------------------------------------------------- |
| `note`    | \`str | None\`      | Optional note to describe the decision logic              |
| `node_id` | \`str | None\`      | Optional ID for the node produced for this decision logic |

Returns:

| Type                             | Description                          |
| -------------------------------- | ------------------------------------ |
| `Decision[StateT, DepsT, Never]` | A new Decision node with no branches |

Source code in `pydantic_graph/pydantic_graph/beta/graph_builder.py`

```python
def decision(self, *, note: str | None = None, node_id: str | None = None) -> Decision[StateT, DepsT, Never]:
    """Create a new decision node.

    Args:
        note: Optional note to describe the decision logic
        node_id: Optional ID for the node produced for this decision logic

    Returns:
        A new Decision node with no branches
    """
    return Decision(id=NodeID(node_id or generate_placeholder_node_id('decision')), branches=[], note=note)
```

#### match

```python
match(
    source: TypeOrTypeExpression[SourceT],
    *,
    matches: Callable[[Any], bool] | None = None
) -> DecisionBranchBuilder[
    StateT, DepsT, SourceT, SourceT, Never
]
```

Create a decision branch matcher.

Parameters:

| Name      | Type                            | Description                                  | Default                           |
| --------- | ------------------------------- | -------------------------------------------- | --------------------------------- |
| `source`  | `TypeOrTypeExpression[SourceT]` | The type or type expression to match against | *required*                        |
| `matches` | \`Callable\[[Any], bool\]       | None\`                                       | Optional custom matching function |

Returns:

| Type                                                            | Description                                         |
| --------------------------------------------------------------- | --------------------------------------------------- |
| `DecisionBranchBuilder[StateT, DepsT, SourceT, SourceT, Never]` | A DecisionBranchBuilder for constructing the branch |

Source code in `pydantic_graph/pydantic_graph/beta/graph_builder.py`

```python
def match(
    self,
    source: TypeOrTypeExpression[SourceT],
    *,
    matches: Callable[[Any], bool] | None = None,
) -> DecisionBranchBuilder[StateT, DepsT, SourceT, SourceT, Never]:
    """Create a decision branch matcher.

    Args:
        source: The type or type expression to match against
        matches: Optional custom matching function

    Returns:
        A DecisionBranchBuilder for constructing the branch
    """
    # Note, the following node_id really is just a placeholder and shouldn't end up in the final graph
    # This is why we don't expose a way for end users to override the value used here.
    node_id = NodeID(generate_placeholder_node_id('match_decision'))
    decision = Decision[StateT, DepsT, Never](id=node_id, branches=[], note=None)
    new_path_builder = PathBuilder[StateT, DepsT, SourceT](working_items=[])
    return DecisionBranchBuilder(decision=decision, source=source, matches=matches, path_builder=new_path_builder)
```

#### match_node

```python
match_node(
    source: type[SourceNodeT],
    *,
    matches: Callable[[Any], bool] | None = None
) -> DecisionBranch[SourceNodeT]
```

Create a decision branch for BaseNode subclasses.

This is similar to match() but specifically designed for matching against BaseNode types from the v1 system.

Parameters:

| Name      | Type                      | Description                            | Default                           |
| --------- | ------------------------- | -------------------------------------- | --------------------------------- |
| `source`  | `type[SourceNodeT]`       | The BaseNode subclass to match against | *required*                        |
| `matches` | \`Callable\[[Any], bool\] | None\`                                 | Optional custom matching function |

Returns:

| Type                          | Description                            |
| ----------------------------- | -------------------------------------- |
| `DecisionBranch[SourceNodeT]` | A DecisionBranch for the BaseNode type |

Source code in `pydantic_graph/pydantic_graph/beta/graph_builder.py`

```python
def match_node(
    self,
    source: type[SourceNodeT],
    *,
    matches: Callable[[Any], bool] | None = None,
) -> DecisionBranch[SourceNodeT]:
    """Create a decision branch for BaseNode subclasses.

    This is similar to match() but specifically designed for matching
    against BaseNode types from the v1 system.

    Args:
        source: The BaseNode subclass to match against
        matches: Optional custom matching function

    Returns:
        A DecisionBranch for the BaseNode type
    """
    node = NodeStep(source)
    path = Path(items=[DestinationMarker(node.id)])
    return DecisionBranch(source=source, matches=matches, path=path, destinations=[node])
```

#### node

```python
node(
    node_type: type[BaseNode[StateT, DepsT, GraphOutputT]],
) -> EdgePath[StateT, DepsT]
```

Create an edge path from a BaseNode class.

This method integrates v1-style BaseNode classes into the v2 graph system by analyzing their type hints and creating appropriate edges.

Parameters:

| Name        | Type                                          | Description                        | Default    |
| ----------- | --------------------------------------------- | ---------------------------------- | ---------- |
| `node_type` | `type[BaseNode[StateT, DepsT, GraphOutputT]]` | The BaseNode subclass to integrate | *required* |

Returns:

| Type                      | Description                                           |
| ------------------------- | ----------------------------------------------------- |
| `EdgePath[StateT, DepsT]` | An EdgePath representing the node and its connections |

Raises:

| Type              | Description                                     |
| ----------------- | ----------------------------------------------- |
| `GraphSetupError` | If the node type is missing required type hints |

Source code in `pydantic_graph/pydantic_graph/beta/graph_builder.py`

```python
def node(
    self,
    node_type: type[BaseNode[StateT, DepsT, GraphOutputT]],
) -> EdgePath[StateT, DepsT]:
    """Create an edge path from a BaseNode class.

    This method integrates v1-style BaseNode classes into the v2 graph
    system by analyzing their type hints and creating appropriate edges.

    Args:
        node_type: The BaseNode subclass to integrate

    Returns:
        An EdgePath representing the node and its connections

    Raises:
        GraphSetupError: If the node type is missing required type hints
    """
    parent_namespace = _utils.get_parent_namespace(inspect.currentframe())
    type_hints = get_type_hints(node_type.run, localns=parent_namespace, include_extras=True)
    try:
        return_hint = type_hints['return']
    except KeyError as e:  # pragma: no cover
        raise exceptions.GraphSetupError(
            f'Node {node_type} is missing a return type hint on its `run` method'
        ) from e

    node = NodeStep(node_type)

    edge = self._edge_from_return_hint(node, return_hint)
    if not edge:  # pragma: no cover
        raise exceptions.GraphSetupError(f'Node {node_type} is missing a return type hint on its `run` method')

    return edge
```

#### build

```python
build(
    validate_graph_structure: bool = True,
) -> Graph[StateT, DepsT, GraphInputT, GraphOutputT]
```

Build the final executable graph from the accumulated nodes and edges.

This method performs validation, normalization, and analysis of the graph structure to create a complete, executable graph instance.

Parameters:

| Name                       | Type   | Description                                                                                                                  | Default |
| -------------------------- | ------ | ---------------------------------------------------------------------------------------------------------------------------- | ------- |
| `validate_graph_structure` | `bool` | whether to perform validation of the graph structure See the docstring of \_validate_graph_structure below for more details. | `True`  |

Returns:

| Type                                              | Description                                   |
| ------------------------------------------------- | --------------------------------------------- |
| `Graph[StateT, DepsT, GraphInputT, GraphOutputT]` | A complete Graph instance ready for execution |

Raises:

| Type         | Description                                                        |
| ------------ | ------------------------------------------------------------------ |
| `ValueError` | If the graph structure is invalid (e.g., join without parent fork) |

Source code in `pydantic_graph/pydantic_graph/beta/graph_builder.py`

```python
def build(self, validate_graph_structure: bool = True) -> Graph[StateT, DepsT, GraphInputT, GraphOutputT]:
    """Build the final executable graph from the accumulated nodes and edges.

    This method performs validation, normalization, and analysis of the graph
    structure to create a complete, executable graph instance.

    Args:
        validate_graph_structure: whether to perform validation of the graph structure
            See the docstring of _validate_graph_structure below for more details.

    Returns:
        A complete Graph instance ready for execution

    Raises:
        ValueError: If the graph structure is invalid (e.g., join without parent fork)
    """
    nodes = self._nodes
    edges_by_source = self._edges_by_source

    nodes, edges_by_source = _replace_placeholder_node_ids(nodes, edges_by_source)
    nodes, edges_by_source = _flatten_paths(nodes, edges_by_source)
    nodes, edges_by_source = _normalize_forks(nodes, edges_by_source)
    if validate_graph_structure:
        _validate_graph_structure(nodes, edges_by_source)
    parent_forks = _collect_dominating_forks(nodes, edges_by_source)
    intermediate_join_nodes = _compute_intermediate_join_nodes(nodes, parent_forks)

    return Graph[StateT, DepsT, GraphInputT, GraphOutputT](
        name=self.name,
        state_type=unpack_type_expression(self.state_type),
        deps_type=unpack_type_expression(self.deps_type),
        input_type=unpack_type_expression(self.input_type),
        output_type=unpack_type_expression(self.output_type),
        nodes=nodes,
        edges_by_source=edges_by_source,
        parent_forks=parent_forks,
        intermediate_join_nodes=intermediate_join_nodes,
        auto_instrument=self.auto_instrument,
    )
```

### EndNode

Bases: `Generic[InputT]`

Terminal node representing the completion of graph execution.

The EndNode marks the successful completion of a graph execution flow and can collect the final output data.

Source code in `pydantic_graph/pydantic_graph/beta/node.py`

```python
class EndNode(Generic[InputT]):
    """Terminal node representing the completion of graph execution.

    The EndNode marks the successful completion of a graph execution flow
    and can collect the final output data.
    """

    id = NodeID('__end__')
    """Fixed identifier for the end node."""

    def _force_variance(self, inputs: InputT) -> None:  # pragma: no cover
        """Force type variance for proper generic typing.

        This method exists solely for type checking purposes and should never be called.

        Args:
            inputs: Input data of type InputT.

        Raises:
            RuntimeError: Always, as this method should never be executed.
        """
        raise RuntimeError('This method should never be called, it is just defined for typing purposes.')
```

#### id

```python
id = NodeID('__end__')
```

Fixed identifier for the end node.

### StartNode

Bases: `Generic[OutputT]`

Entry point node for graph execution.

The StartNode represents the beginning of a graph execution flow.

Source code in `pydantic_graph/pydantic_graph/beta/node.py`

```python
class StartNode(Generic[OutputT]):
    """Entry point node for graph execution.

    The StartNode represents the beginning of a graph execution flow.
    """

    id = NodeID('__start__')
    """Fixed identifier for the start node."""
```

#### id

```python
id = NodeID('__start__')
```

Fixed identifier for the start node.

### StepContext

Bases: `Generic[StateT, DepsT, InputT]`

Context information passed to step functions during graph execution.

The step context provides access to the current graph state, dependencies, and input data for a step.

Class Type Parameters:

| Name     | Bound or Constraints | Description                  | Default    |
| -------- | -------------------- | ---------------------------- | ---------- |
| `StateT` |                      | The type of the graph state  | *required* |
| `DepsT`  |                      | The type of the dependencies | *required* |
| `InputT` |                      | The type of the input data   | *required* |

Source code in `pydantic_graph/pydantic_graph/beta/step.py`

```python
@dataclass(init=False)
class StepContext(Generic[StateT, DepsT, InputT]):
    """Context information passed to step functions during graph execution.

    The step context provides access to the current graph state, dependencies, and input data for a step.

    Type Parameters:
        StateT: The type of the graph state
        DepsT: The type of the dependencies
        InputT: The type of the input data
    """

    _state: StateT
    """The current graph state."""
    _deps: DepsT
    """The graph run dependencies."""
    _inputs: InputT
    """The input data for this step."""

    def __init__(self, *, state: StateT, deps: DepsT, inputs: InputT):
        self._state = state
        self._deps = deps
        self._inputs = inputs

    @property
    def state(self) -> StateT:
        return self._state

    @property
    def deps(self) -> DepsT:
        return self._deps

    @property
    def inputs(self) -> InputT:
        """The input data for this step.

        This must be a property to ensure correct variance behavior
        """
        return self._inputs
```

#### inputs

```python
inputs: InputT
```

The input data for this step.

This must be a property to ensure correct variance behavior

### StepNode

Bases: `BaseNode[StateT, DepsT, Any]`

A base node that represents a step with bound inputs.

StepNode bridges between the v1 and v2 graph execution systems by wrapping a Step with bound inputs in a BaseNode interface. It is not meant to be run directly but rather used to indicate transitions to v2-style steps.

Source code in `pydantic_graph/pydantic_graph/beta/step.py`

```python
@dataclass
class StepNode(BaseNode[StateT, DepsT, Any]):
    """A base node that represents a step with bound inputs.

    StepNode bridges between the v1 and v2 graph execution systems by wrapping
    a [`Step`][pydantic_graph.beta.step.Step] with bound inputs in a BaseNode interface.
    It is not meant to be run directly but rather used to indicate transitions
    to v2-style steps.
    """

    step: Step[StateT, DepsT, Any, Any]
    """The step to execute."""

    inputs: Any
    """The inputs bound to this step."""

    async def run(self, ctx: GraphRunContext[StateT, DepsT]) -> BaseNode[StateT, DepsT, Any] | End[Any]:
        """Attempt to run the step node.

        Args:
            ctx: The graph execution context

        Returns:
            The result of step execution

        Raises:
            NotImplementedError: Always raised as StepNode is not meant to be run directly
        """
        raise NotImplementedError(
            '`StepNode` is not meant to be run directly, it is meant to be used in `BaseNode` subclasses to indicate a transition to v2-style steps.'
        )
```

#### step

```python
step: Step[StateT, DepsT, Any, Any]
```

The step to execute.

#### inputs

```python
inputs: Any
```

The inputs bound to this step.

#### run

```python
run(
    ctx: GraphRunContext[StateT, DepsT],
) -> BaseNode[StateT, DepsT, Any] | End[Any]
```

Attempt to run the step node.

Parameters:

| Name  | Type                             | Description                 | Default    |
| ----- | -------------------------------- | --------------------------- | ---------- |
| `ctx` | `GraphRunContext[StateT, DepsT]` | The graph execution context | *required* |

Returns:

| Type                           | Description |
| ------------------------------ | ----------- |
| \`BaseNode[StateT, DepsT, Any] | End[Any]\`  |

Raises:

| Type                  | Description                                               |
| --------------------- | --------------------------------------------------------- |
| `NotImplementedError` | Always raised as StepNode is not meant to be run directly |

Source code in `pydantic_graph/pydantic_graph/beta/step.py`

```python
async def run(self, ctx: GraphRunContext[StateT, DepsT]) -> BaseNode[StateT, DepsT, Any] | End[Any]:
    """Attempt to run the step node.

    Args:
        ctx: The graph execution context

    Returns:
        The result of step execution

    Raises:
        NotImplementedError: Always raised as StepNode is not meant to be run directly
    """
    raise NotImplementedError(
        '`StepNode` is not meant to be run directly, it is meant to be used in `BaseNode` subclasses to indicate a transition to v2-style steps.'
    )
```

### TypeExpression

Bases: `Generic[T]`

A workaround for type checker limitations when using complex type expressions.

```text
This class serves as a wrapper for types that cannot normally be used in positions
```

requiring `type[T]`, such as `Any`, `Union[...]`, or `Literal[...]`. It provides a way to pass these complex type expressions to functions expecting concrete types.

Example

Instead of `output_type=Union[str, int]` (which may cause type errors), use `output_type=TypeExpression[Union[str, int]]`.

Note

This is a workaround for the lack of TypeForm in the Python type system.

Source code in `pydantic_graph/pydantic_graph/beta/util.py`

```python
class TypeExpression(Generic[T]):
    """A workaround for type checker limitations when using complex type expressions.

        This class serves as a wrapper for types that cannot normally be used in positions
    requiring `type[T]`, such as `Any`, `Union[...]`, or `Literal[...]`. It provides a
        way to pass these complex type expressions to functions expecting concrete types.

    Example:
            Instead of `output_type=Union[str, int]` (which may cause type errors),
            use `output_type=TypeExpression[Union[str, int]]`.

    Note:
            This is a workaround for the lack of TypeForm in the Python type system.
    """

    pass
```
