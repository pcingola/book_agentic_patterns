# `pydantic_graph.nodes`

### StateT

```python
StateT = TypeVar('StateT', default=None)
```

Type variable for the state in a graph.

### GraphRunContext

Bases: `Generic[StateT, DepsT]`

Context for a graph.

Source code in `pydantic_graph/pydantic_graph/nodes.py`

```python
@dataclass(kw_only=True)
class GraphRunContext(Generic[StateT, DepsT]):
    """Context for a graph."""

    state: StateT
    """The state of the graph."""
    deps: DepsT
    """Dependencies for the graph."""
```

#### state

```python
state: StateT
```

The state of the graph.

#### deps

```python
deps: DepsT
```

Dependencies for the graph.

### BaseNode

Bases: `ABC`, `Generic[StateT, DepsT, NodeRunEndT]`

Base class for a node.

Source code in `pydantic_graph/pydantic_graph/nodes.py`

```python
class BaseNode(ABC, Generic[StateT, DepsT, NodeRunEndT]):
    """Base class for a node."""

    docstring_notes: ClassVar[bool] = False
    """Set to `True` to generate mermaid diagram notes from the class's docstring.

    While this can add valuable information to the diagram, it can make diagrams harder to view, hence
    it is disabled by default. You can also customise notes overriding the
    [`get_note`][pydantic_graph.nodes.BaseNode.get_note] method.
    """

    @abstractmethod
    async def run(self, ctx: GraphRunContext[StateT, DepsT]) -> BaseNode[StateT, DepsT, Any] | End[NodeRunEndT]:
        """Run the node.

        This is an abstract method that must be implemented by subclasses.

        !!! note "Return types used at runtime"
            The return type of this method are read by `pydantic_graph` at runtime and used to define which
            nodes can be called next in the graph. This is displayed in [mermaid diagrams](mermaid.md)
            and enforced when running the graph.

        Args:
            ctx: The graph context.

        Returns:
            The next node to run or [`End`][pydantic_graph.nodes.End] to signal the end of the graph.
        """
        ...

    def get_snapshot_id(self) -> str:
        if snapshot_id := getattr(self, '__snapshot_id', None):
            return snapshot_id
        else:
            snapshot_id = generate_snapshot_id(self.get_node_id())
            object.__setattr__(self, '__snapshot_id', snapshot_id)
            return snapshot_id

    def set_snapshot_id(self, snapshot_id: str) -> None:
        object.__setattr__(self, '__snapshot_id', snapshot_id)

    @classmethod
    @cache
    def get_node_id(cls) -> str:
        """Get the ID of the node."""
        return cls.__name__

    @classmethod
    def get_note(cls) -> str | None:
        """Get a note about the node to render on mermaid charts.

        By default, this returns a note only if [`docstring_notes`][pydantic_graph.nodes.BaseNode.docstring_notes]
        is `True`. You can override this method to customise the node notes.
        """
        if not cls.docstring_notes:
            return None
        docstring = cls.__doc__
        # dataclasses get an automatic docstring which is just their signature, we don't want that
        if docstring and is_dataclass(cls) and docstring.startswith(f'{cls.__name__}('):
            docstring = None  # pragma: no cover
        if docstring:  # pragma: no branch
            # remove indentation from docstring
            import inspect

            docstring = inspect.cleandoc(docstring)
        return docstring

    @classmethod
    def get_node_def(cls, local_ns: dict[str, Any] | None) -> NodeDef[StateT, DepsT, NodeRunEndT]:
        """Get the node definition."""
        type_hints = get_type_hints(cls.run, localns=local_ns, include_extras=True)
        try:
            return_hint = type_hints['return']
        except KeyError as e:
            raise exceptions.GraphSetupError(f'Node {cls} is missing a return type hint on its `run` method') from e

        next_node_edges: dict[str, Edge] = {}
        end_edge: Edge | None = None
        returns_base_node: bool = False
        for return_type in _utils.get_union_args(return_hint):
            return_type, annotations = _utils.unpack_annotated(return_type)
            edge = next((a for a in annotations if isinstance(a, Edge)), Edge(None))
            return_type_origin = get_origin(return_type) or return_type
            if return_type_origin is End:
                end_edge = edge
            elif return_type_origin is BaseNode:
                returns_base_node = True
            elif issubclass(return_type_origin, BaseNode):
                next_node_edges[return_type.get_node_id()] = edge
            else:
                raise exceptions.GraphSetupError(f'Invalid return type: {return_type}')

        return NodeDef(
            node=cls,
            node_id=cls.get_node_id(),
            note=cls.get_note(),
            next_node_edges=next_node_edges,
            end_edge=end_edge,
            returns_base_node=returns_base_node,
        )

    def deep_copy(self) -> Self:
        """Returns a deep copy of the node."""
        return copy.deepcopy(self)
```

#### docstring_notes

```python
docstring_notes: bool = False
```

Set to `True` to generate mermaid diagram notes from the class's docstring.

While this can add valuable information to the diagram, it can make diagrams harder to view, hence it is disabled by default. You can also customise notes overriding the get_note method.

#### run

```python
run(
    ctx: GraphRunContext[StateT, DepsT],
) -> BaseNode[StateT, DepsT, Any] | End[NodeRunEndT]
```

Run the node.

This is an abstract method that must be implemented by subclasses.

Return types used at runtime

The return type of this method are read by `pydantic_graph` at runtime and used to define which nodes can be called next in the graph. This is displayed in [mermaid diagrams](https://ai.pydantic.dev/api/pydantic_graph/mermaid/index.md) and enforced when running the graph.

Parameters:

| Name  | Type                             | Description        | Default    |
| ----- | -------------------------------- | ------------------ | ---------- |
| `ctx` | `GraphRunContext[StateT, DepsT]` | The graph context. | *required* |

Returns:

| Type                           | Description        |
| ------------------------------ | ------------------ |
| \`BaseNode[StateT, DepsT, Any] | End[NodeRunEndT]\` |

Source code in `pydantic_graph/pydantic_graph/nodes.py`

```python
@abstractmethod
async def run(self, ctx: GraphRunContext[StateT, DepsT]) -> BaseNode[StateT, DepsT, Any] | End[NodeRunEndT]:
    """Run the node.

    This is an abstract method that must be implemented by subclasses.

    !!! note "Return types used at runtime"
        The return type of this method are read by `pydantic_graph` at runtime and used to define which
        nodes can be called next in the graph. This is displayed in [mermaid diagrams](mermaid.md)
        and enforced when running the graph.

    Args:
        ctx: The graph context.

    Returns:
        The next node to run or [`End`][pydantic_graph.nodes.End] to signal the end of the graph.
    """
    ...
```

#### get_node_id

```python
get_node_id() -> str
```

Get the ID of the node.

Source code in `pydantic_graph/pydantic_graph/nodes.py`

```python
@classmethod
@cache
def get_node_id(cls) -> str:
    """Get the ID of the node."""
    return cls.__name__
```

#### get_note

```python
get_note() -> str | None
```

Get a note about the node to render on mermaid charts.

By default, this returns a note only if docstring_notes is `True`. You can override this method to customise the node notes.

Source code in `pydantic_graph/pydantic_graph/nodes.py`

```python
@classmethod
def get_note(cls) -> str | None:
    """Get a note about the node to render on mermaid charts.

    By default, this returns a note only if [`docstring_notes`][pydantic_graph.nodes.BaseNode.docstring_notes]
    is `True`. You can override this method to customise the node notes.
    """
    if not cls.docstring_notes:
        return None
    docstring = cls.__doc__
    # dataclasses get an automatic docstring which is just their signature, we don't want that
    if docstring and is_dataclass(cls) and docstring.startswith(f'{cls.__name__}('):
        docstring = None  # pragma: no cover
    if docstring:  # pragma: no branch
        # remove indentation from docstring
        import inspect

        docstring = inspect.cleandoc(docstring)
    return docstring
```

#### get_node_def

```python
get_node_def(
    local_ns: dict[str, Any] | None,
) -> NodeDef[StateT, DepsT, NodeRunEndT]
```

Get the node definition.

Source code in `pydantic_graph/pydantic_graph/nodes.py`

```python
@classmethod
def get_node_def(cls, local_ns: dict[str, Any] | None) -> NodeDef[StateT, DepsT, NodeRunEndT]:
    """Get the node definition."""
    type_hints = get_type_hints(cls.run, localns=local_ns, include_extras=True)
    try:
        return_hint = type_hints['return']
    except KeyError as e:
        raise exceptions.GraphSetupError(f'Node {cls} is missing a return type hint on its `run` method') from e

    next_node_edges: dict[str, Edge] = {}
    end_edge: Edge | None = None
    returns_base_node: bool = False
    for return_type in _utils.get_union_args(return_hint):
        return_type, annotations = _utils.unpack_annotated(return_type)
        edge = next((a for a in annotations if isinstance(a, Edge)), Edge(None))
        return_type_origin = get_origin(return_type) or return_type
        if return_type_origin is End:
            end_edge = edge
        elif return_type_origin is BaseNode:
            returns_base_node = True
        elif issubclass(return_type_origin, BaseNode):
            next_node_edges[return_type.get_node_id()] = edge
        else:
            raise exceptions.GraphSetupError(f'Invalid return type: {return_type}')

    return NodeDef(
        node=cls,
        node_id=cls.get_node_id(),
        note=cls.get_note(),
        next_node_edges=next_node_edges,
        end_edge=end_edge,
        returns_base_node=returns_base_node,
    )
```

#### deep_copy

```python
deep_copy() -> Self
```

Returns a deep copy of the node.

Source code in `pydantic_graph/pydantic_graph/nodes.py`

```python
def deep_copy(self) -> Self:
    """Returns a deep copy of the node."""
    return copy.deepcopy(self)
```

### End

Bases: `Generic[RunEndT]`

Type to return from a node to signal the end of the graph.

Source code in `pydantic_graph/pydantic_graph/nodes.py`

```python
@dataclass
class End(Generic[RunEndT]):
    """Type to return from a node to signal the end of the graph."""

    data: RunEndT
    """Data to return from the graph."""

    def deep_copy_data(self) -> End[RunEndT]:
        """Returns a deep copy of the end of the run."""
        if self.data is None:
            return self
        else:
            end = End(copy.deepcopy(self.data))
            end.set_snapshot_id(self.get_snapshot_id())
            return end

    def get_snapshot_id(self) -> str:
        if snapshot_id := getattr(self, '__snapshot_id', None):
            return snapshot_id
        else:
            self.__dict__['__snapshot_id'] = snapshot_id = generate_snapshot_id('end')
            return snapshot_id

    def set_snapshot_id(self, set_id: str) -> None:
        self.__dict__['__snapshot_id'] = set_id
```

#### data

```python
data: RunEndT
```

Data to return from the graph.

#### deep_copy_data

```python
deep_copy_data() -> End[RunEndT]
```

Returns a deep copy of the end of the run.

Source code in `pydantic_graph/pydantic_graph/nodes.py`

```python
def deep_copy_data(self) -> End[RunEndT]:
    """Returns a deep copy of the end of the run."""
    if self.data is None:
        return self
    else:
        end = End(copy.deepcopy(self.data))
        end.set_snapshot_id(self.get_snapshot_id())
        return end
```

### Edge

Annotation to apply a label to an edge in a graph.

Source code in `pydantic_graph/pydantic_graph/nodes.py`

```python
@dataclass(frozen=True)
class Edge:
    """Annotation to apply a label to an edge in a graph."""

    label: str | None
    """Label for the edge."""
```

#### label

```python
label: str | None
```

Label for the edge.

### DepsT

```python
DepsT = TypeVar('DepsT', default=None, contravariant=True)
```

Type variable for the dependencies of a graph and node.

### RunEndT

```python
RunEndT = TypeVar('RunEndT', covariant=True, default=None)
```

Covariant type variable for the return type of a graph run.

### NodeRunEndT

```python
NodeRunEndT = TypeVar(
    "NodeRunEndT", covariant=True, default=Never
)
```

Covariant type variable for the return type of a node run.
