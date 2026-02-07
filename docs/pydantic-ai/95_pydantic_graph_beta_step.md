# `pydantic_graph.beta.step`

Step-based graph execution components.

This module provides the core abstractions for step-based graph execution, including step contexts, step functions, and step nodes that bridge between the v1 and v2 graph execution systems.

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

### StepFunction

Bases: `Protocol[StateT, DepsT, InputT, OutputT]`

Protocol for step functions that can be executed in the graph.

Step functions are async callables that receive a step context and return a result.

Class Type Parameters:

| Name      | Bound or Constraints | Description                  | Default    |
| --------- | -------------------- | ---------------------------- | ---------- |
| `StateT`  |                      | The type of the graph state  | *required* |
| `DepsT`   |                      | The type of the dependencies | *required* |
| `InputT`  |                      | The type of the input data   | *required* |
| `OutputT` |                      | The type of the output data  | *required* |

Source code in `pydantic_graph/pydantic_graph/beta/step.py`

```python
class StepFunction(Protocol[StateT, DepsT, InputT, OutputT]):
    """Protocol for step functions that can be executed in the graph.

    Step functions are async callables that receive a step context and return a result.

    Type Parameters:
        StateT: The type of the graph state
        DepsT: The type of the dependencies
        InputT: The type of the input data
        OutputT: The type of the output data
    """

    def __call__(self, ctx: StepContext[StateT, DepsT, InputT]) -> Awaitable[OutputT]:
        """Execute the step function with the given context.

        Args:
            ctx: The step context containing state, dependencies, and inputs

        Returns:
            An awaitable that resolves to the step's output
        """
        raise NotImplementedError
```

#### __call__

```python
__call__(
    ctx: StepContext[StateT, DepsT, InputT],
) -> Awaitable[OutputT]
```

Execute the step function with the given context.

Parameters:

| Name  | Type                                 | Description                                                 | Default    |
| ----- | ------------------------------------ | ----------------------------------------------------------- | ---------- |
| `ctx` | `StepContext[StateT, DepsT, InputT]` | The step context containing state, dependencies, and inputs | *required* |

Returns:

| Type                 | Description                                     |
| -------------------- | ----------------------------------------------- |
| `Awaitable[OutputT]` | An awaitable that resolves to the step's output |

Source code in `pydantic_graph/pydantic_graph/beta/step.py`

```python
def __call__(self, ctx: StepContext[StateT, DepsT, InputT]) -> Awaitable[OutputT]:
    """Execute the step function with the given context.

    Args:
        ctx: The step context containing state, dependencies, and inputs

    Returns:
        An awaitable that resolves to the step's output
    """
    raise NotImplementedError
```

### StreamFunction

Bases: `Protocol[StateT, DepsT, InputT, OutputT]`

Protocol for stream functions that can be executed in the graph.

Stream functions are async callables that receive a step context and return an async iterator.

Class Type Parameters:

| Name      | Bound or Constraints | Description                  | Default    |
| --------- | -------------------- | ---------------------------- | ---------- |
| `StateT`  |                      | The type of the graph state  | *required* |
| `DepsT`   |                      | The type of the dependencies | *required* |
| `InputT`  |                      | The type of the input data   | *required* |
| `OutputT` |                      | The type of the output data  | *required* |

Source code in `pydantic_graph/pydantic_graph/beta/step.py`

```python
class StreamFunction(Protocol[StateT, DepsT, InputT, OutputT]):
    """Protocol for stream functions that can be executed in the graph.

    Stream functions are async callables that receive a step context and return an async iterator.

    Type Parameters:
        StateT: The type of the graph state
        DepsT: The type of the dependencies
        InputT: The type of the input data
        OutputT: The type of the output data
    """

    def __call__(self, ctx: StepContext[StateT, DepsT, InputT]) -> AsyncIterator[OutputT]:
        """Execute the stream function with the given context.

        Args:
            ctx: The step context containing state, dependencies, and inputs

        Returns:
            An async iterator yielding the streamed output
        """
        raise NotImplementedError
        yield
```

#### __call__

```python
__call__(
    ctx: StepContext[StateT, DepsT, InputT],
) -> AsyncIterator[OutputT]
```

Execute the stream function with the given context.

Parameters:

| Name  | Type                                 | Description                                                 | Default    |
| ----- | ------------------------------------ | ----------------------------------------------------------- | ---------- |
| `ctx` | `StepContext[StateT, DepsT, InputT]` | The step context containing state, dependencies, and inputs | *required* |

Returns:

| Type                     | Description                                    |
| ------------------------ | ---------------------------------------------- |
| `AsyncIterator[OutputT]` | An async iterator yielding the streamed output |

Source code in `pydantic_graph/pydantic_graph/beta/step.py`

```python
def __call__(self, ctx: StepContext[StateT, DepsT, InputT]) -> AsyncIterator[OutputT]:
    """Execute the stream function with the given context.

    Args:
        ctx: The step context containing state, dependencies, and inputs

    Returns:
        An async iterator yielding the streamed output
    """
    raise NotImplementedError
    yield
```

### AnyStepFunction

```python
AnyStepFunction = StepFunction[Any, Any, Any, Any]
```

Type alias for a step function with any type parameters.

### Step

Bases: `Generic[StateT, DepsT, InputT, OutputT]`

A step in the graph execution that wraps a step function.

Steps represent individual units of execution in the graph, encapsulating a step function along with metadata like ID and label.

Class Type Parameters:

| Name      | Bound or Constraints | Description                  | Default    |
| --------- | -------------------- | ---------------------------- | ---------- |
| `StateT`  |                      | The type of the graph state  | *required* |
| `DepsT`   |                      | The type of the dependencies | *required* |
| `InputT`  |                      | The type of the input data   | *required* |
| `OutputT` |                      | The type of the output data  | *required* |

Source code in `pydantic_graph/pydantic_graph/beta/step.py`

```python
@dataclass(init=False)
class Step(Generic[StateT, DepsT, InputT, OutputT]):
    """A step in the graph execution that wraps a step function.

    Steps represent individual units of execution in the graph, encapsulating
    a step function along with metadata like ID and label.

    Type Parameters:
        StateT: The type of the graph state
        DepsT: The type of the dependencies
        InputT: The type of the input data
        OutputT: The type of the output data
    """

    id: NodeID
    """Unique identifier for this step."""
    _call: StepFunction[StateT, DepsT, InputT, OutputT]
    """The step function to execute."""
    label: str | None
    """Optional human-readable label for this step."""

    def __init__(self, *, id: NodeID, call: StepFunction[StateT, DepsT, InputT, OutputT], label: str | None = None):
        self.id = id
        self._call = call
        self.label = label

    @property
    def call(self) -> StepFunction[StateT, DepsT, InputT, OutputT]:
        """The step function to execute. This needs to be a property for proper variance inference."""
        return self._call

    @overload
    def as_node(self, inputs: None = None) -> StepNode[StateT, DepsT]: ...

    @overload
    def as_node(self, inputs: InputT) -> StepNode[StateT, DepsT]: ...

    def as_node(self, inputs: InputT | None = None) -> StepNode[StateT, DepsT]:
        """Create a step node with bound inputs.

        Args:
            inputs: The input data to bind to this step, or None

        Returns:
            A [`StepNode`][pydantic_graph.beta.step.StepNode] with this step and the bound inputs
        """
        return StepNode(self, inputs)
```

#### id

```python
id: NodeID = id
```

Unique identifier for this step.

#### label

```python
label: str | None = label
```

Optional human-readable label for this step.

#### call

```python
call: StepFunction[StateT, DepsT, InputT, OutputT]
```

The step function to execute. This needs to be a property for proper variance inference.

#### as_node

```python
as_node(inputs: None = None) -> StepNode[StateT, DepsT]
```

```python
as_node(inputs: InputT) -> StepNode[StateT, DepsT]
```

```python
as_node(
    inputs: InputT | None = None,
) -> StepNode[StateT, DepsT]
```

Create a step node with bound inputs.

Parameters:

| Name     | Type     | Description | Default                                      |
| -------- | -------- | ----------- | -------------------------------------------- |
| `inputs` | \`InputT | None\`      | The input data to bind to this step, or None |

Returns:

| Type                      | Description                                    |
| ------------------------- | ---------------------------------------------- |
| `StepNode[StateT, DepsT]` | A StepNode with this step and the bound inputs |

Source code in `pydantic_graph/pydantic_graph/beta/step.py`

```python
def as_node(self, inputs: InputT | None = None) -> StepNode[StateT, DepsT]:
    """Create a step node with bound inputs.

    Args:
        inputs: The input data to bind to this step, or None

    Returns:
        A [`StepNode`][pydantic_graph.beta.step.StepNode] with this step and the bound inputs
    """
    return StepNode(self, inputs)
```

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

### NodeStep

Bases: `Step[StateT, DepsT, Any, BaseNode[StateT, DepsT, Any] | End[Any]]`

A step that wraps a BaseNode type for execution.

NodeStep allows v1-style BaseNode classes to be used as steps in the v2 graph execution system. It validates that the input is of the expected node type and runs it with the appropriate graph context.

Source code in `pydantic_graph/pydantic_graph/beta/step.py`

```python
class NodeStep(Step[StateT, DepsT, Any, BaseNode[StateT, DepsT, Any] | End[Any]]):
    """A step that wraps a BaseNode type for execution.

    NodeStep allows v1-style BaseNode classes to be used as steps in the
    v2 graph execution system. It validates that the input is of the expected
    node type and runs it with the appropriate graph context.
    """

    node_type: type[BaseNode[StateT, DepsT, Any]]
    """The BaseNode type this step executes."""

    def __init__(
        self,
        node_type: type[BaseNode[StateT, DepsT, Any]],
        *,
        id: NodeID | None = None,
        label: str | None = None,
    ):
        """Initialize a node step.

        Args:
            node_type: The BaseNode class this step will execute
            id: Optional unique identifier, defaults to the node's get_node_id()
            label: Optional human-readable label for this step
        """
        super().__init__(
            id=id or NodeID(node_type.get_node_id()),
            call=self._call_node,
            label=label,
        )
        # `type[BaseNode[StateT, DepsT, Any]]` could actually be a `typing._GenericAlias` like `pydantic_ai._agent_graph.UserPromptNode[~DepsT, ~OutputT]`,
        # so we get the origin to get to the actual class
        self.node_type = get_origin(node_type) or node_type

    async def _call_node(self, ctx: StepContext[StateT, DepsT, Any]) -> BaseNode[StateT, DepsT, Any] | End[Any]:
        """Execute the wrapped node with the step context.

        Args:
            ctx: The step context containing the node instance to run

        Returns:
            The result of running the node, either another BaseNode or End

        Raises:
            ValueError: If the input node is not of the expected type
        """
        node = ctx.inputs
        if not isinstance(node, self.node_type):
            raise ValueError(f'Node {node} is not of type {self.node_type}')  # pragma: no cover
        node = cast(BaseNode[StateT, DepsT, Any], node)
        return await node.run(GraphRunContext(state=ctx.state, deps=ctx.deps))
```

#### __init__

```python
__init__(
    node_type: type[BaseNode[StateT, DepsT, Any]],
    *,
    id: NodeID | None = None,
    label: str | None = None
)
```

Initialize a node step.

Parameters:

| Name        | Type                                 | Description                               | Default                                                          |
| ----------- | ------------------------------------ | ----------------------------------------- | ---------------------------------------------------------------- |
| `node_type` | `type[BaseNode[StateT, DepsT, Any]]` | The BaseNode class this step will execute | *required*                                                       |
| `id`        | \`NodeID                             | None\`                                    | Optional unique identifier, defaults to the node's get_node_id() |
| `label`     | \`str                                | None\`                                    | Optional human-readable label for this step                      |

Source code in `pydantic_graph/pydantic_graph/beta/step.py`

```python
def __init__(
    self,
    node_type: type[BaseNode[StateT, DepsT, Any]],
    *,
    id: NodeID | None = None,
    label: str | None = None,
):
    """Initialize a node step.

    Args:
        node_type: The BaseNode class this step will execute
        id: Optional unique identifier, defaults to the node's get_node_id()
        label: Optional human-readable label for this step
    """
    super().__init__(
        id=id or NodeID(node_type.get_node_id()),
        call=self._call_node,
        label=label,
    )
    # `type[BaseNode[StateT, DepsT, Any]]` could actually be a `typing._GenericAlias` like `pydantic_ai._agent_graph.UserPromptNode[~DepsT, ~OutputT]`,
    # so we get the origin to get to the actual class
    self.node_type = get_origin(node_type) or node_type
```

#### node_type

```python
node_type: type[BaseNode[StateT, DepsT, Any]] = (
    get_origin(node_type) or node_type
)
```

The BaseNode type this step executes.
