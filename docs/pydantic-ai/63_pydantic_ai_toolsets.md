# `pydantic_ai.toolsets`

### AbstractToolset

Bases: `ABC`, `Generic[AgentDepsT]`

A toolset is a collection of tools that can be used by an agent.

It is responsible for:

- Listing the tools it contains
- Validating the arguments of the tools
- Calling the tools

See [toolset docs](https://ai.pydantic.dev/toolsets/index.md) for more information.

Source code in `pydantic_ai_slim/pydantic_ai/toolsets/abstract.py`

```python
class AbstractToolset(ABC, Generic[AgentDepsT]):
    """A toolset is a collection of tools that can be used by an agent.

    It is responsible for:

    - Listing the tools it contains
    - Validating the arguments of the tools
    - Calling the tools

    See [toolset docs](../toolsets.md) for more information.
    """

    @property
    @abstractmethod
    def id(self) -> str | None:
        """An ID for the toolset that is unique among all toolsets registered with the same agent.

        If you're implementing a concrete implementation that users can instantiate more than once, you should let them optionally pass a custom ID to the constructor and return that here.

        A toolset needs to have an ID in order to be used in a durable execution environment like Temporal, in which case the ID will be used to identify the toolset's activities within the workflow.
        """
        raise NotImplementedError()

    @property
    def label(self) -> str:
        """The name of the toolset for use in error messages."""
        label = self.__class__.__name__
        if self.id:  # pragma: no branch
            label += f' {self.id!r}'
        return label

    @property
    def tool_name_conflict_hint(self) -> str:
        """A hint for how to avoid name conflicts with other toolsets for use in error messages."""
        return 'Rename the tool or wrap the toolset in a `PrefixedToolset` to avoid name conflicts.'

    async def __aenter__(self) -> Self:
        """Enter the toolset context.

        This is where you can set up network connections in a concrete implementation.
        """
        return self

    async def __aexit__(self, *args: Any) -> bool | None:
        """Exit the toolset context.

        This is where you can tear down network connections in a concrete implementation.
        """
        return None

    @abstractmethod
    async def get_tools(self, ctx: RunContext[AgentDepsT]) -> dict[str, ToolsetTool[AgentDepsT]]:
        """The tools that are available in this toolset."""
        raise NotImplementedError()

    @abstractmethod
    async def call_tool(
        self, name: str, tool_args: dict[str, Any], ctx: RunContext[AgentDepsT], tool: ToolsetTool[AgentDepsT]
    ) -> Any:
        """Call a tool with the given arguments.

        Args:
            name: The name of the tool to call.
            tool_args: The arguments to pass to the tool.
            ctx: The run context.
            tool: The tool definition returned by [`get_tools`][pydantic_ai.toolsets.AbstractToolset.get_tools] that was called.
        """
        raise NotImplementedError()

    def apply(self, visitor: Callable[[AbstractToolset[AgentDepsT]], None]) -> None:
        """Run a visitor function on all "leaf" toolsets (i.e. those that implement their own tool listing and calling)."""
        visitor(self)

    def visit_and_replace(
        self, visitor: Callable[[AbstractToolset[AgentDepsT]], AbstractToolset[AgentDepsT]]
    ) -> AbstractToolset[AgentDepsT]:
        """Run a visitor function on all "leaf" toolsets (i.e. those that implement their own tool listing and calling) and replace them in the hierarchy with the result of the function."""
        return visitor(self)

    def filtered(
        self, filter_func: Callable[[RunContext[AgentDepsT], ToolDefinition], bool]
    ) -> FilteredToolset[AgentDepsT]:
        """Returns a new toolset that filters this toolset's tools using a filter function that takes the agent context and the tool definition.

        See [toolset docs](../toolsets.md#filtering-tools) for more information.
        """
        from .filtered import FilteredToolset

        return FilteredToolset(self, filter_func)

    def prefixed(self, prefix: str) -> PrefixedToolset[AgentDepsT]:
        """Returns a new toolset that prefixes the names of this toolset's tools.

        See [toolset docs](../toolsets.md#prefixing-tool-names) for more information.
        """
        from .prefixed import PrefixedToolset

        return PrefixedToolset(self, prefix)

    def prepared(self, prepare_func: ToolsPrepareFunc[AgentDepsT]) -> PreparedToolset[AgentDepsT]:
        """Returns a new toolset that prepares this toolset's tools using a prepare function that takes the agent context and the original tool definitions.

        See [toolset docs](../toolsets.md#preparing-tool-definitions) for more information.
        """
        from .prepared import PreparedToolset

        return PreparedToolset(self, prepare_func)

    def renamed(self, name_map: dict[str, str]) -> RenamedToolset[AgentDepsT]:
        """Returns a new toolset that renames this toolset's tools using a dictionary mapping new names to original names.

        See [toolset docs](../toolsets.md#renaming-tools) for more information.
        """
        from .renamed import RenamedToolset

        return RenamedToolset(self, name_map)

    def approval_required(
        self,
        approval_required_func: Callable[[RunContext[AgentDepsT], ToolDefinition, dict[str, Any]], bool] = (
            lambda ctx, tool_def, tool_args: True
        ),
    ) -> ApprovalRequiredToolset[AgentDepsT]:
        """Returns a new toolset that requires (some) calls to tools it contains to be approved.

        See [toolset docs](../toolsets.md#requiring-tool-approval) for more information.
        """
        from .approval_required import ApprovalRequiredToolset

        return ApprovalRequiredToolset(self, approval_required_func)
```

#### id

```python
id: str | None
```

An ID for the toolset that is unique among all toolsets registered with the same agent.

If you're implementing a concrete implementation that users can instantiate more than once, you should let them optionally pass a custom ID to the constructor and return that here.

A toolset needs to have an ID in order to be used in a durable execution environment like Temporal, in which case the ID will be used to identify the toolset's activities within the workflow.

#### label

```python
label: str
```

The name of the toolset for use in error messages.

#### tool_name_conflict_hint

```python
tool_name_conflict_hint: str
```

A hint for how to avoid name conflicts with other toolsets for use in error messages.

#### __aenter__

```python
__aenter__() -> Self
```

Enter the toolset context.

This is where you can set up network connections in a concrete implementation.

Source code in `pydantic_ai_slim/pydantic_ai/toolsets/abstract.py`

```python
async def __aenter__(self) -> Self:
    """Enter the toolset context.

    This is where you can set up network connections in a concrete implementation.
    """
    return self
```

#### __aexit__

```python
__aexit__(*args: Any) -> bool | None
```

Exit the toolset context.

This is where you can tear down network connections in a concrete implementation.

Source code in `pydantic_ai_slim/pydantic_ai/toolsets/abstract.py`

```python
async def __aexit__(self, *args: Any) -> bool | None:
    """Exit the toolset context.

    This is where you can tear down network connections in a concrete implementation.
    """
    return None
```

#### get_tools

```python
get_tools(
    ctx: RunContext[AgentDepsT],
) -> dict[str, ToolsetTool[AgentDepsT]]
```

The tools that are available in this toolset.

Source code in `pydantic_ai_slim/pydantic_ai/toolsets/abstract.py`

```python
@abstractmethod
async def get_tools(self, ctx: RunContext[AgentDepsT]) -> dict[str, ToolsetTool[AgentDepsT]]:
    """The tools that are available in this toolset."""
    raise NotImplementedError()
```

#### call_tool

```python
call_tool(
    name: str,
    tool_args: dict[str, Any],
    ctx: RunContext[AgentDepsT],
    tool: ToolsetTool[AgentDepsT],
) -> Any
```

Call a tool with the given arguments.

Parameters:

| Name        | Type                      | Description                                                | Default    |
| ----------- | ------------------------- | ---------------------------------------------------------- | ---------- |
| `name`      | `str`                     | The name of the tool to call.                              | *required* |
| `tool_args` | `dict[str, Any]`          | The arguments to pass to the tool.                         | *required* |
| `ctx`       | `RunContext[AgentDepsT]`  | The run context.                                           | *required* |
| `tool`      | `ToolsetTool[AgentDepsT]` | The tool definition returned by get_tools that was called. | *required* |

Source code in `pydantic_ai_slim/pydantic_ai/toolsets/abstract.py`

```python
@abstractmethod
async def call_tool(
    self, name: str, tool_args: dict[str, Any], ctx: RunContext[AgentDepsT], tool: ToolsetTool[AgentDepsT]
) -> Any:
    """Call a tool with the given arguments.

    Args:
        name: The name of the tool to call.
        tool_args: The arguments to pass to the tool.
        ctx: The run context.
        tool: The tool definition returned by [`get_tools`][pydantic_ai.toolsets.AbstractToolset.get_tools] that was called.
    """
    raise NotImplementedError()
```

#### apply

```python
apply(
    visitor: Callable[[AbstractToolset[AgentDepsT]], None],
) -> None
```

Run a visitor function on all "leaf" toolsets (i.e. those that implement their own tool listing and calling).

Source code in `pydantic_ai_slim/pydantic_ai/toolsets/abstract.py`

```python
def apply(self, visitor: Callable[[AbstractToolset[AgentDepsT]], None]) -> None:
    """Run a visitor function on all "leaf" toolsets (i.e. those that implement their own tool listing and calling)."""
    visitor(self)
```

#### visit_and_replace

```python
visit_and_replace(
    visitor: Callable[
        [AbstractToolset[AgentDepsT]],
        AbstractToolset[AgentDepsT],
    ],
) -> AbstractToolset[AgentDepsT]
```

Run a visitor function on all "leaf" toolsets (i.e. those that implement their own tool listing and calling) and replace them in the hierarchy with the result of the function.

Source code in `pydantic_ai_slim/pydantic_ai/toolsets/abstract.py`

```python
def visit_and_replace(
    self, visitor: Callable[[AbstractToolset[AgentDepsT]], AbstractToolset[AgentDepsT]]
) -> AbstractToolset[AgentDepsT]:
    """Run a visitor function on all "leaf" toolsets (i.e. those that implement their own tool listing and calling) and replace them in the hierarchy with the result of the function."""
    return visitor(self)
```

#### filtered

```python
filtered(
    filter_func: Callable[
        [RunContext[AgentDepsT], ToolDefinition], bool
    ],
) -> FilteredToolset[AgentDepsT]
```

Returns a new toolset that filters this toolset's tools using a filter function that takes the agent context and the tool definition.

See [toolset docs](https://ai.pydantic.dev/toolsets/#filtering-tools) for more information.

Source code in `pydantic_ai_slim/pydantic_ai/toolsets/abstract.py`

```python
def filtered(
    self, filter_func: Callable[[RunContext[AgentDepsT], ToolDefinition], bool]
) -> FilteredToolset[AgentDepsT]:
    """Returns a new toolset that filters this toolset's tools using a filter function that takes the agent context and the tool definition.

    See [toolset docs](../toolsets.md#filtering-tools) for more information.
    """
    from .filtered import FilteredToolset

    return FilteredToolset(self, filter_func)
```

#### prefixed

```python
prefixed(prefix: str) -> PrefixedToolset[AgentDepsT]
```

Returns a new toolset that prefixes the names of this toolset's tools.

See [toolset docs](https://ai.pydantic.dev/toolsets/#prefixing-tool-names) for more information.

Source code in `pydantic_ai_slim/pydantic_ai/toolsets/abstract.py`

```python
def prefixed(self, prefix: str) -> PrefixedToolset[AgentDepsT]:
    """Returns a new toolset that prefixes the names of this toolset's tools.

    See [toolset docs](../toolsets.md#prefixing-tool-names) for more information.
    """
    from .prefixed import PrefixedToolset

    return PrefixedToolset(self, prefix)
```

#### prepared

```python
prepared(
    prepare_func: ToolsPrepareFunc[AgentDepsT],
) -> PreparedToolset[AgentDepsT]
```

Returns a new toolset that prepares this toolset's tools using a prepare function that takes the agent context and the original tool definitions.

See [toolset docs](https://ai.pydantic.dev/toolsets/#preparing-tool-definitions) for more information.

Source code in `pydantic_ai_slim/pydantic_ai/toolsets/abstract.py`

```python
def prepared(self, prepare_func: ToolsPrepareFunc[AgentDepsT]) -> PreparedToolset[AgentDepsT]:
    """Returns a new toolset that prepares this toolset's tools using a prepare function that takes the agent context and the original tool definitions.

    See [toolset docs](../toolsets.md#preparing-tool-definitions) for more information.
    """
    from .prepared import PreparedToolset

    return PreparedToolset(self, prepare_func)
```

#### renamed

```python
renamed(
    name_map: dict[str, str],
) -> RenamedToolset[AgentDepsT]
```

Returns a new toolset that renames this toolset's tools using a dictionary mapping new names to original names.

See [toolset docs](https://ai.pydantic.dev/toolsets/#renaming-tools) for more information.

Source code in `pydantic_ai_slim/pydantic_ai/toolsets/abstract.py`

```python
def renamed(self, name_map: dict[str, str]) -> RenamedToolset[AgentDepsT]:
    """Returns a new toolset that renames this toolset's tools using a dictionary mapping new names to original names.

    See [toolset docs](../toolsets.md#renaming-tools) for more information.
    """
    from .renamed import RenamedToolset

    return RenamedToolset(self, name_map)
```

#### approval_required

```python
approval_required(
    approval_required_func: Callable[
        [
            RunContext[AgentDepsT],
            ToolDefinition,
            dict[str, Any],
        ],
        bool,
    ] = lambda ctx, tool_def, tool_args: True
) -> ApprovalRequiredToolset[AgentDepsT]
```

Returns a new toolset that requires (some) calls to tools it contains to be approved.

See [toolset docs](https://ai.pydantic.dev/toolsets/#requiring-tool-approval) for more information.

Source code in `pydantic_ai_slim/pydantic_ai/toolsets/abstract.py`

```python
def approval_required(
    self,
    approval_required_func: Callable[[RunContext[AgentDepsT], ToolDefinition, dict[str, Any]], bool] = (
        lambda ctx, tool_def, tool_args: True
    ),
) -> ApprovalRequiredToolset[AgentDepsT]:
    """Returns a new toolset that requires (some) calls to tools it contains to be approved.

    See [toolset docs](../toolsets.md#requiring-tool-approval) for more information.
    """
    from .approval_required import ApprovalRequiredToolset

    return ApprovalRequiredToolset(self, approval_required_func)
```

### CombinedToolset

Bases: `AbstractToolset[AgentDepsT]`

A toolset that combines multiple toolsets.

See [toolset docs](https://ai.pydantic.dev/toolsets/#combining-toolsets) for more information.

Source code in `pydantic_ai_slim/pydantic_ai/toolsets/combined.py`

```python
@dataclass
class CombinedToolset(AbstractToolset[AgentDepsT]):
    """A toolset that combines multiple toolsets.

    See [toolset docs](../toolsets.md#combining-toolsets) for more information.
    """

    toolsets: Sequence[AbstractToolset[AgentDepsT]]

    _enter_lock: Lock = field(compare=False, init=False, default_factory=Lock)
    _entered_count: int = field(init=False, default=0)
    _exit_stack: AsyncExitStack | None = field(init=False, default=None)

    @property
    def id(self) -> str | None:
        return None  # pragma: no cover

    @property
    def label(self) -> str:
        return f'{self.__class__.__name__}({", ".join(toolset.label for toolset in self.toolsets)})'  # pragma: no cover

    async def __aenter__(self) -> Self:
        async with self._enter_lock:
            if self._entered_count == 0:
                async with AsyncExitStack() as exit_stack:
                    for toolset in self.toolsets:
                        await exit_stack.enter_async_context(toolset)
                    self._exit_stack = exit_stack.pop_all()
            self._entered_count += 1
        return self

    async def __aexit__(self, *args: Any) -> bool | None:
        async with self._enter_lock:
            self._entered_count -= 1
            if self._entered_count == 0 and self._exit_stack is not None:
                await self._exit_stack.aclose()
                self._exit_stack = None

    async def get_tools(self, ctx: RunContext[AgentDepsT]) -> dict[str, ToolsetTool[AgentDepsT]]:
        toolsets_tools = await asyncio.gather(*(toolset.get_tools(ctx) for toolset in self.toolsets))
        all_tools: dict[str, ToolsetTool[AgentDepsT]] = {}

        for toolset, tools in zip(self.toolsets, toolsets_tools):
            for name, tool in tools.items():
                tool_toolset = tool.toolset
                if existing_tool := all_tools.get(name):
                    capitalized_toolset_label = tool_toolset.label[0].upper() + tool_toolset.label[1:]
                    raise UserError(
                        f'{capitalized_toolset_label} defines a tool whose name conflicts with existing tool from {existing_tool.toolset.label}: {name!r}. {toolset.tool_name_conflict_hint}'
                    )

                all_tools[name] = _CombinedToolsetTool(
                    toolset=tool_toolset,
                    tool_def=tool.tool_def,
                    max_retries=tool.max_retries,
                    args_validator=tool.args_validator,
                    source_toolset=toolset,
                    source_tool=tool,
                )
        return all_tools

    async def call_tool(
        self, name: str, tool_args: dict[str, Any], ctx: RunContext[AgentDepsT], tool: ToolsetTool[AgentDepsT]
    ) -> Any:
        assert isinstance(tool, _CombinedToolsetTool)
        return await tool.source_toolset.call_tool(name, tool_args, ctx, tool.source_tool)

    def apply(self, visitor: Callable[[AbstractToolset[AgentDepsT]], None]) -> None:
        for toolset in self.toolsets:
            toolset.apply(visitor)

    def visit_and_replace(
        self, visitor: Callable[[AbstractToolset[AgentDepsT]], AbstractToolset[AgentDepsT]]
    ) -> AbstractToolset[AgentDepsT]:
        return replace(self, toolsets=[toolset.visit_and_replace(visitor) for toolset in self.toolsets])
```

### ExternalToolset

Bases: `AbstractToolset[AgentDepsT]`

A toolset that holds tools whose results will be produced outside of the Pydantic AI agent run in which they were called.

See [toolset docs](https://ai.pydantic.dev/toolsets/#external-toolset) for more information.

Source code in `pydantic_ai_slim/pydantic_ai/toolsets/external.py`

```python
class ExternalToolset(AbstractToolset[AgentDepsT]):
    """A toolset that holds tools whose results will be produced outside of the Pydantic AI agent run in which they were called.

    See [toolset docs](../toolsets.md#external-toolset) for more information.
    """

    tool_defs: list[ToolDefinition]
    _id: str | None

    def __init__(self, tool_defs: list[ToolDefinition], *, id: str | None = None):
        self.tool_defs = tool_defs
        self._id = id

    @property
    def id(self) -> str | None:
        return self._id

    async def get_tools(self, ctx: RunContext[AgentDepsT]) -> dict[str, ToolsetTool[AgentDepsT]]:
        return {
            tool_def.name: ToolsetTool(
                toolset=self,
                tool_def=replace(tool_def, kind='external'),
                max_retries=0,
                args_validator=TOOL_SCHEMA_VALIDATOR,
            )
            for tool_def in self.tool_defs
        }

    async def call_tool(
        self, name: str, tool_args: dict[str, Any], ctx: RunContext[AgentDepsT], tool: ToolsetTool[AgentDepsT]
    ) -> Any:
        raise NotImplementedError('External tools cannot be called directly')
```

### ApprovalRequiredToolset

Bases: `WrapperToolset[AgentDepsT]`

A toolset that requires (some) calls to tools it contains to be approved.

See [toolset docs](https://ai.pydantic.dev/toolsets/#requiring-tool-approval) for more information.

Source code in `pydantic_ai_slim/pydantic_ai/toolsets/approval_required.py`

```python
@dataclass
class ApprovalRequiredToolset(WrapperToolset[AgentDepsT]):
    """A toolset that requires (some) calls to tools it contains to be approved.

    See [toolset docs](../toolsets.md#requiring-tool-approval) for more information.
    """

    approval_required_func: Callable[[RunContext[AgentDepsT], ToolDefinition, dict[str, Any]], bool] = (
        lambda ctx, tool_def, tool_args: True
    )

    async def call_tool(
        self, name: str, tool_args: dict[str, Any], ctx: RunContext[AgentDepsT], tool: ToolsetTool[AgentDepsT]
    ) -> Any:
        if not ctx.tool_call_approved and self.approval_required_func(ctx, tool.tool_def, tool_args):
            raise ApprovalRequired

        return await super().call_tool(name, tool_args, ctx, tool)
```

### FilteredToolset

Bases: `WrapperToolset[AgentDepsT]`

A toolset that filters the tools it contains using a filter function that takes the agent context and the tool definition.

See [toolset docs](https://ai.pydantic.dev/toolsets/#filtering-tools) for more information.

Source code in `pydantic_ai_slim/pydantic_ai/toolsets/filtered.py`

```python
@dataclass
class FilteredToolset(WrapperToolset[AgentDepsT]):
    """A toolset that filters the tools it contains using a filter function that takes the agent context and the tool definition.

    See [toolset docs](../toolsets.md#filtering-tools) for more information.
    """

    filter_func: Callable[[RunContext[AgentDepsT], ToolDefinition], bool]

    async def get_tools(self, ctx: RunContext[AgentDepsT]) -> dict[str, ToolsetTool[AgentDepsT]]:
        return {
            name: tool for name, tool in (await super().get_tools(ctx)).items() if self.filter_func(ctx, tool.tool_def)
        }
```

### FunctionToolset

Bases: `AbstractToolset[AgentDepsT]`

A toolset that lets Python functions be used as tools.

See [toolset docs](https://ai.pydantic.dev/toolsets/#function-toolset) for more information.

Source code in `pydantic_ai_slim/pydantic_ai/toolsets/function.py`

````python
class FunctionToolset(AbstractToolset[AgentDepsT]):
    """A toolset that lets Python functions be used as tools.

    See [toolset docs](../toolsets.md#function-toolset) for more information.
    """

    tools: dict[str, Tool[Any]]
    max_retries: int
    timeout: float | None
    _id: str | None
    docstring_format: DocstringFormat
    require_parameter_descriptions: bool
    schema_generator: type[GenerateJsonSchema]

    def __init__(
        self,
        tools: Sequence[Tool[AgentDepsT] | ToolFuncEither[AgentDepsT, ...]] = [],
        *,
        max_retries: int = 1,
        timeout: float | None = None,
        docstring_format: DocstringFormat = 'auto',
        require_parameter_descriptions: bool = False,
        schema_generator: type[GenerateJsonSchema] = GenerateToolJsonSchema,
        strict: bool | None = None,
        sequential: bool = False,
        requires_approval: bool = False,
        metadata: dict[str, Any] | None = None,
        id: str | None = None,
    ):
        """Build a new function toolset.

        Args:
            tools: The tools to add to the toolset.
            max_retries: The maximum number of retries for each tool during a run.
                Applies to all tools, unless overridden when adding a tool.
            timeout: Timeout in seconds for tool execution. If a tool takes longer than this,
                a retry prompt is returned to the model. Individual tools can override this with their own timeout.
                Defaults to None (no timeout).
            docstring_format: Format of tool docstring, see [`DocstringFormat`][pydantic_ai.tools.DocstringFormat].
                Defaults to `'auto'`, such that the format is inferred from the structure of the docstring.
                Applies to all tools, unless overridden when adding a tool.
            require_parameter_descriptions: If True, raise an error if a parameter description is missing. Defaults to False.
                Applies to all tools, unless overridden when adding a tool.
            schema_generator: The JSON schema generator class to use for this tool. Defaults to `GenerateToolJsonSchema`.
                Applies to all tools, unless overridden when adding a tool.
            strict: Whether to enforce JSON schema compliance (only affects OpenAI).
                See [`ToolDefinition`][pydantic_ai.tools.ToolDefinition] for more info.
            sequential: Whether the function requires a sequential/serial execution environment. Defaults to False.
                Applies to all tools, unless overridden when adding a tool.
            requires_approval: Whether this tool requires human-in-the-loop approval. Defaults to False.
                See the [tools documentation](../deferred-tools.md#human-in-the-loop-tool-approval) for more info.
                Applies to all tools, unless overridden when adding a tool.
            metadata: Optional metadata for the tool. This is not sent to the model but can be used for filtering and tool behavior customization.
                Applies to all tools, unless overridden when adding a tool, which will be merged with the toolset's metadata.
            id: An optional unique ID for the toolset. A toolset needs to have an ID in order to be used in a durable execution environment like Temporal,
                in which case the ID will be used to identify the toolset's activities within the workflow.
        """
        self.max_retries = max_retries
        self.timeout = timeout
        self._id = id
        self.docstring_format = docstring_format
        self.require_parameter_descriptions = require_parameter_descriptions
        self.schema_generator = schema_generator
        self.strict = strict
        self.sequential = sequential
        self.requires_approval = requires_approval
        self.metadata = metadata

        self.tools = {}
        for tool in tools:
            if isinstance(tool, Tool):
                self.add_tool(tool)  # pyright: ignore[reportUnknownArgumentType]
            else:
                self.add_function(tool)

    @property
    def id(self) -> str | None:
        return self._id

    @overload
    def tool(self, func: ToolFuncEither[AgentDepsT, ToolParams], /) -> ToolFuncEither[AgentDepsT, ToolParams]: ...

    @overload
    def tool(
        self,
        /,
        *,
        name: str | None = None,
        description: str | None = None,
        retries: int | None = None,
        prepare: ToolPrepareFunc[AgentDepsT] | None = None,
        docstring_format: DocstringFormat | None = None,
        require_parameter_descriptions: bool | None = None,
        schema_generator: type[GenerateJsonSchema] | None = None,
        strict: bool | None = None,
        sequential: bool | None = None,
        requires_approval: bool | None = None,
        metadata: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> Callable[[ToolFuncEither[AgentDepsT, ToolParams]], ToolFuncEither[AgentDepsT, ToolParams]]: ...

    def tool(
        self,
        func: ToolFuncEither[AgentDepsT, ToolParams] | None = None,
        /,
        *,
        name: str | None = None,
        description: str | None = None,
        retries: int | None = None,
        prepare: ToolPrepareFunc[AgentDepsT] | None = None,
        docstring_format: DocstringFormat | None = None,
        require_parameter_descriptions: bool | None = None,
        schema_generator: type[GenerateJsonSchema] | None = None,
        strict: bool | None = None,
        sequential: bool | None = None,
        requires_approval: bool | None = None,
        metadata: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> Any:
        """Decorator to register a tool function which takes [`RunContext`][pydantic_ai.tools.RunContext] as its first argument.

        Can decorate a sync or async functions.

        The docstring is inspected to extract both the tool description and description of each parameter,
        [learn more](../tools.md#function-tools-and-schema).

        We can't add overloads for every possible signature of tool, since the return type is a recursive union
        so the signature of functions decorated with `@toolset.tool` is obscured.

        Example:
        ```python
        from pydantic_ai import Agent, FunctionToolset, RunContext

        toolset = FunctionToolset()

        @toolset.tool
        def foobar(ctx: RunContext[int], x: int) -> int:
            return ctx.deps + x

        @toolset.tool(retries=2)
        async def spam(ctx: RunContext[str], y: float) -> float:
            return ctx.deps + y

        agent = Agent('test', toolsets=[toolset], deps_type=int)
        result = agent.run_sync('foobar', deps=1)
        print(result.output)
        #> {"foobar":1,"spam":1.0}
        ```

        Args:
            func: The tool function to register.
            name: The name of the tool, defaults to the function name.
            description: The description of the tool,defaults to the function docstring.
            retries: The number of retries to allow for this tool, defaults to the agent's default retries,
                which defaults to 1.
            prepare: custom method to prepare the tool definition for each step, return `None` to omit this
                tool from a given step. This is useful if you want to customise a tool at call time,
                or omit it completely from a step. See [`ToolPrepareFunc`][pydantic_ai.tools.ToolPrepareFunc].
            docstring_format: The format of the docstring, see [`DocstringFormat`][pydantic_ai.tools.DocstringFormat].
                If `None`, the default value is determined by the toolset.
            require_parameter_descriptions: If True, raise an error if a parameter description is missing.
                If `None`, the default value is determined by the toolset.
            schema_generator: The JSON schema generator class to use for this tool.
                If `None`, the default value is determined by the toolset.
            strict: Whether to enforce JSON schema compliance (only affects OpenAI).
                See [`ToolDefinition`][pydantic_ai.tools.ToolDefinition] for more info.
                If `None`, the default value is determined by the toolset.
            sequential: Whether the function requires a sequential/serial execution environment. Defaults to False.
                If `None`, the default value is determined by the toolset.
            requires_approval: Whether this tool requires human-in-the-loop approval. Defaults to False.
                See the [tools documentation](../deferred-tools.md#human-in-the-loop-tool-approval) for more info.
                If `None`, the default value is determined by the toolset.
            metadata: Optional metadata for the tool. This is not sent to the model but can be used for filtering and tool behavior customization.
                If `None`, the default value is determined by the toolset. If provided, it will be merged with the toolset's metadata.
            timeout: Timeout in seconds for tool execution. If the tool takes longer, a retry prompt is returned to the model.
                Defaults to None (no timeout).
        """

        def tool_decorator(
            func_: ToolFuncEither[AgentDepsT, ToolParams],
        ) -> ToolFuncEither[AgentDepsT, ToolParams]:
            # noinspection PyTypeChecker
            self.add_function(
                func=func_,
                takes_ctx=None,
                name=name,
                description=description,
                retries=retries,
                prepare=prepare,
                docstring_format=docstring_format,
                require_parameter_descriptions=require_parameter_descriptions,
                schema_generator=schema_generator,
                strict=strict,
                sequential=sequential,
                requires_approval=requires_approval,
                metadata=metadata,
                timeout=timeout,
            )
            return func_

        return tool_decorator if func is None else tool_decorator(func)

    def add_function(
        self,
        func: ToolFuncEither[AgentDepsT, ToolParams],
        takes_ctx: bool | None = None,
        name: str | None = None,
        description: str | None = None,
        retries: int | None = None,
        prepare: ToolPrepareFunc[AgentDepsT] | None = None,
        docstring_format: DocstringFormat | None = None,
        require_parameter_descriptions: bool | None = None,
        schema_generator: type[GenerateJsonSchema] | None = None,
        strict: bool | None = None,
        sequential: bool | None = None,
        requires_approval: bool | None = None,
        metadata: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> None:
        """Add a function as a tool to the toolset.

        Can take a sync or async function.

        The docstring is inspected to extract both the tool description and description of each parameter,
        [learn more](../tools.md#function-tools-and-schema).

        Args:
            func: The tool function to register.
            takes_ctx: Whether the function takes a [`RunContext`][pydantic_ai.tools.RunContext] as its first argument. If `None`, this is inferred from the function signature.
            name: The name of the tool, defaults to the function name.
            description: The description of the tool, defaults to the function docstring.
            retries: The number of retries to allow for this tool, defaults to the agent's default retries,
                which defaults to 1.
            prepare: custom method to prepare the tool definition for each step, return `None` to omit this
                tool from a given step. This is useful if you want to customise a tool at call time,
                or omit it completely from a step. See [`ToolPrepareFunc`][pydantic_ai.tools.ToolPrepareFunc].
            docstring_format: The format of the docstring, see [`DocstringFormat`][pydantic_ai.tools.DocstringFormat].
                If `None`, the default value is determined by the toolset.
            require_parameter_descriptions: If True, raise an error if a parameter description is missing.
                If `None`, the default value is determined by the toolset.
            schema_generator: The JSON schema generator class to use for this tool.
                If `None`, the default value is determined by the toolset.
            strict: Whether to enforce JSON schema compliance (only affects OpenAI).
                See [`ToolDefinition`][pydantic_ai.tools.ToolDefinition] for more info.
                If `None`, the default value is determined by the toolset.
            sequential: Whether the function requires a sequential/serial execution environment. Defaults to False.
                If `None`, the default value is determined by the toolset.
            requires_approval: Whether this tool requires human-in-the-loop approval. Defaults to False.
                See the [tools documentation](../deferred-tools.md#human-in-the-loop-tool-approval) for more info.
                If `None`, the default value is determined by the toolset.
            metadata: Optional metadata for the tool. This is not sent to the model but can be used for filtering and tool behavior customization.
                If `None`, the default value is determined by the toolset. If provided, it will be merged with the toolset's metadata.
            timeout: Timeout in seconds for tool execution. If the tool takes longer, a retry prompt is returned to the model.
                Defaults to None (no timeout).
        """
        if docstring_format is None:
            docstring_format = self.docstring_format
        if require_parameter_descriptions is None:
            require_parameter_descriptions = self.require_parameter_descriptions
        if schema_generator is None:
            schema_generator = self.schema_generator
        if strict is None:
            strict = self.strict
        if sequential is None:
            sequential = self.sequential
        if requires_approval is None:
            requires_approval = self.requires_approval

        tool = Tool[AgentDepsT](
            func,
            takes_ctx=takes_ctx,
            name=name,
            description=description,
            max_retries=retries,
            prepare=prepare,
            docstring_format=docstring_format,
            require_parameter_descriptions=require_parameter_descriptions,
            schema_generator=schema_generator,
            strict=strict,
            sequential=sequential,
            requires_approval=requires_approval,
            metadata=metadata,
            timeout=timeout,
        )
        self.add_tool(tool)

    def add_tool(self, tool: Tool[AgentDepsT]) -> None:
        """Add a tool to the toolset.

        Args:
            tool: The tool to add.
        """
        if tool.name in self.tools:
            raise UserError(f'Tool name conflicts with existing tool: {tool.name!r}')
        if tool.max_retries is None:
            tool.max_retries = self.max_retries
        if self.metadata is not None:
            tool.metadata = self.metadata | (tool.metadata or {})
        self.tools[tool.name] = tool

    async def get_tools(self, ctx: RunContext[AgentDepsT]) -> dict[str, ToolsetTool[AgentDepsT]]:
        tools: dict[str, ToolsetTool[AgentDepsT]] = {}
        for original_name, tool in self.tools.items():
            max_retries = tool.max_retries if tool.max_retries is not None else self.max_retries
            run_context = replace(
                ctx,
                tool_name=original_name,
                retry=ctx.retries.get(original_name, 0),
                max_retries=max_retries,
            )
            tool_def = await tool.prepare_tool_def(run_context)
            if not tool_def:
                continue

            new_name = tool_def.name
            if new_name in tools:
                if new_name != original_name:
                    raise UserError(f'Renaming tool {original_name!r} to {new_name!r} conflicts with existing tool.')
                else:
                    raise UserError(f'Tool name conflicts with previously renamed tool: {new_name!r}.')

            tools[new_name] = FunctionToolsetTool(
                toolset=self,
                tool_def=tool_def,
                max_retries=max_retries,
                args_validator=tool.function_schema.validator,
                call_func=tool.function_schema.call,
                is_async=tool.function_schema.is_async,
                timeout=tool_def.timeout,
            )
        return tools

    async def call_tool(
        self, name: str, tool_args: dict[str, Any], ctx: RunContext[AgentDepsT], tool: ToolsetTool[AgentDepsT]
    ) -> Any:
        assert isinstance(tool, FunctionToolsetTool)

        # Per-tool timeout takes precedence over toolset timeout
        timeout = tool.timeout if tool.timeout is not None else self.timeout
        if timeout is not None:
            try:
                with anyio.fail_after(timeout):
                    return await tool.call_func(tool_args, ctx)
            except TimeoutError:
                raise ModelRetry(f'Timed out after {timeout} seconds.') from None
        else:
            return await tool.call_func(tool_args, ctx)
````

#### __init__

```python
__init__(
    tools: Sequence[
        Tool[AgentDepsT] | ToolFuncEither[AgentDepsT, ...]
    ] = [],
    *,
    max_retries: int = 1,
    timeout: float | None = None,
    docstring_format: DocstringFormat = "auto",
    require_parameter_descriptions: bool = False,
    schema_generator: type[
        GenerateJsonSchema
    ] = GenerateToolJsonSchema,
    strict: bool | None = None,
    sequential: bool = False,
    requires_approval: bool = False,
    metadata: dict[str, Any] | None = None,
    id: str | None = None
)
```

Build a new function toolset.

Parameters:

| Name                             | Type                         | Description                                                                                                                                                                                          | Default                                                                                                                                                                                                                                    |
| -------------------------------- | ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `tools`                          | \`Sequence\[Tool[AgentDepsT] | ToolFuncEither[AgentDepsT, ...]\]\`                                                                                                                                                                  | The tools to add to the toolset.                                                                                                                                                                                                           |
| `max_retries`                    | `int`                        | The maximum number of retries for each tool during a run. Applies to all tools, unless overridden when adding a tool.                                                                                | `1`                                                                                                                                                                                                                                        |
| `timeout`                        | \`float                      | None\`                                                                                                                                                                                               | Timeout in seconds for tool execution. If a tool takes longer than this, a retry prompt is returned to the model. Individual tools can override this with their own timeout. Defaults to None (no timeout).                                |
| `docstring_format`               | `DocstringFormat`            | Format of tool docstring, see DocstringFormat. Defaults to 'auto', such that the format is inferred from the structure of the docstring. Applies to all tools, unless overridden when adding a tool. | `'auto'`                                                                                                                                                                                                                                   |
| `require_parameter_descriptions` | `bool`                       | If True, raise an error if a parameter description is missing. Defaults to False. Applies to all tools, unless overridden when adding a tool.                                                        | `False`                                                                                                                                                                                                                                    |
| `schema_generator`               | `type[GenerateJsonSchema]`   | The JSON schema generator class to use for this tool. Defaults to GenerateToolJsonSchema. Applies to all tools, unless overridden when adding a tool.                                                | `GenerateToolJsonSchema`                                                                                                                                                                                                                   |
| `strict`                         | \`bool                       | None\`                                                                                                                                                                                               | Whether to enforce JSON schema compliance (only affects OpenAI). See ToolDefinition for more info.                                                                                                                                         |
| `sequential`                     | `bool`                       | Whether the function requires a sequential/serial execution environment. Defaults to False. Applies to all tools, unless overridden when adding a tool.                                              | `False`                                                                                                                                                                                                                                    |
| `requires_approval`              | `bool`                       | Whether this tool requires human-in-the-loop approval. Defaults to False. See the tools documentation for more info. Applies to all tools, unless overridden when adding a tool.                     | `False`                                                                                                                                                                                                                                    |
| `metadata`                       | \`dict[str, Any]             | None\`                                                                                                                                                                                               | Optional metadata for the tool. This is not sent to the model but can be used for filtering and tool behavior customization. Applies to all tools, unless overridden when adding a tool, which will be merged with the toolset's metadata. |
| `id`                             | \`str                        | None\`                                                                                                                                                                                               | An optional unique ID for the toolset. A toolset needs to have an ID in order to be used in a durable execution environment like Temporal, in which case the ID will be used to identify the toolset's activities within the workflow.     |

Source code in `pydantic_ai_slim/pydantic_ai/toolsets/function.py`

```python
def __init__(
    self,
    tools: Sequence[Tool[AgentDepsT] | ToolFuncEither[AgentDepsT, ...]] = [],
    *,
    max_retries: int = 1,
    timeout: float | None = None,
    docstring_format: DocstringFormat = 'auto',
    require_parameter_descriptions: bool = False,
    schema_generator: type[GenerateJsonSchema] = GenerateToolJsonSchema,
    strict: bool | None = None,
    sequential: bool = False,
    requires_approval: bool = False,
    metadata: dict[str, Any] | None = None,
    id: str | None = None,
):
    """Build a new function toolset.

    Args:
        tools: The tools to add to the toolset.
        max_retries: The maximum number of retries for each tool during a run.
            Applies to all tools, unless overridden when adding a tool.
        timeout: Timeout in seconds for tool execution. If a tool takes longer than this,
            a retry prompt is returned to the model. Individual tools can override this with their own timeout.
            Defaults to None (no timeout).
        docstring_format: Format of tool docstring, see [`DocstringFormat`][pydantic_ai.tools.DocstringFormat].
            Defaults to `'auto'`, such that the format is inferred from the structure of the docstring.
            Applies to all tools, unless overridden when adding a tool.
        require_parameter_descriptions: If True, raise an error if a parameter description is missing. Defaults to False.
            Applies to all tools, unless overridden when adding a tool.
        schema_generator: The JSON schema generator class to use for this tool. Defaults to `GenerateToolJsonSchema`.
            Applies to all tools, unless overridden when adding a tool.
        strict: Whether to enforce JSON schema compliance (only affects OpenAI).
            See [`ToolDefinition`][pydantic_ai.tools.ToolDefinition] for more info.
        sequential: Whether the function requires a sequential/serial execution environment. Defaults to False.
            Applies to all tools, unless overridden when adding a tool.
        requires_approval: Whether this tool requires human-in-the-loop approval. Defaults to False.
            See the [tools documentation](../deferred-tools.md#human-in-the-loop-tool-approval) for more info.
            Applies to all tools, unless overridden when adding a tool.
        metadata: Optional metadata for the tool. This is not sent to the model but can be used for filtering and tool behavior customization.
            Applies to all tools, unless overridden when adding a tool, which will be merged with the toolset's metadata.
        id: An optional unique ID for the toolset. A toolset needs to have an ID in order to be used in a durable execution environment like Temporal,
            in which case the ID will be used to identify the toolset's activities within the workflow.
    """
    self.max_retries = max_retries
    self.timeout = timeout
    self._id = id
    self.docstring_format = docstring_format
    self.require_parameter_descriptions = require_parameter_descriptions
    self.schema_generator = schema_generator
    self.strict = strict
    self.sequential = sequential
    self.requires_approval = requires_approval
    self.metadata = metadata

    self.tools = {}
    for tool in tools:
        if isinstance(tool, Tool):
            self.add_tool(tool)  # pyright: ignore[reportUnknownArgumentType]
        else:
            self.add_function(tool)
```

#### tool

```python
tool(
    func: ToolFuncEither[AgentDepsT, ToolParams],
) -> ToolFuncEither[AgentDepsT, ToolParams]
```

```python
tool(
    *,
    name: str | None = None,
    description: str | None = None,
    retries: int | None = None,
    prepare: ToolPrepareFunc[AgentDepsT] | None = None,
    docstring_format: DocstringFormat | None = None,
    require_parameter_descriptions: bool | None = None,
    schema_generator: (
        type[GenerateJsonSchema] | None
    ) = None,
    strict: bool | None = None,
    sequential: bool | None = None,
    requires_approval: bool | None = None,
    metadata: dict[str, Any] | None = None,
    timeout: float | None = None
) -> Callable[
    [ToolFuncEither[AgentDepsT, ToolParams]],
    ToolFuncEither[AgentDepsT, ToolParams],
]
```

```python
tool(
    func: (
        ToolFuncEither[AgentDepsT, ToolParams] | None
    ) = None,
    /,
    *,
    name: str | None = None,
    description: str | None = None,
    retries: int | None = None,
    prepare: ToolPrepareFunc[AgentDepsT] | None = None,
    docstring_format: DocstringFormat | None = None,
    require_parameter_descriptions: bool | None = None,
    schema_generator: (
        type[GenerateJsonSchema] | None
    ) = None,
    strict: bool | None = None,
    sequential: bool | None = None,
    requires_approval: bool | None = None,
    metadata: dict[str, Any] | None = None,
    timeout: float | None = None,
) -> Any
```

Decorator to register a tool function which takes RunContext as its first argument.

Can decorate a sync or async functions.

The docstring is inspected to extract both the tool description and description of each parameter, [learn more](https://ai.pydantic.dev/tools/#function-tools-and-schema).

We can't add overloads for every possible signature of tool, since the return type is a recursive union so the signature of functions decorated with `@toolset.tool` is obscured.

Example:

```python
from pydantic_ai import Agent, FunctionToolset, RunContext

toolset = FunctionToolset()

@toolset.tool
def foobar(ctx: RunContext[int], x: int) -> int:
    return ctx.deps + x

@toolset.tool(retries=2)
async def spam(ctx: RunContext[str], y: float) -> float:
    return ctx.deps + y

agent = Agent('test', toolsets=[toolset], deps_type=int)
result = agent.run_sync('foobar', deps=1)
print(result.output)
#> {"foobar":1,"spam":1.0}
```

Parameters:

| Name                             | Type                                     | Description | Default                                                                                                                                                                                                                                           |
| -------------------------------- | ---------------------------------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `func`                           | \`ToolFuncEither[AgentDepsT, ToolParams] | None\`      | The tool function to register.                                                                                                                                                                                                                    |
| `name`                           | \`str                                    | None\`      | The name of the tool, defaults to the function name.                                                                                                                                                                                              |
| `description`                    | \`str                                    | None\`      | The description of the tool,defaults to the function docstring.                                                                                                                                                                                   |
| `retries`                        | \`int                                    | None\`      | The number of retries to allow for this tool, defaults to the agent's default retries, which defaults to 1.                                                                                                                                       |
| `prepare`                        | \`ToolPrepareFunc[AgentDepsT]            | None\`      | custom method to prepare the tool definition for each step, return None to omit this tool from a given step. This is useful if you want to customise a tool at call time, or omit it completely from a step. See ToolPrepareFunc.                 |
| `docstring_format`               | \`DocstringFormat                        | None\`      | The format of the docstring, see DocstringFormat. If None, the default value is determined by the toolset.                                                                                                                                        |
| `require_parameter_descriptions` | \`bool                                   | None\`      | If True, raise an error if a parameter description is missing. If None, the default value is determined by the toolset.                                                                                                                           |
| `schema_generator`               | \`type[GenerateJsonSchema]               | None\`      | The JSON schema generator class to use for this tool. If None, the default value is determined by the toolset.                                                                                                                                    |
| `strict`                         | \`bool                                   | None\`      | Whether to enforce JSON schema compliance (only affects OpenAI). See ToolDefinition for more info. If None, the default value is determined by the toolset.                                                                                       |
| `sequential`                     | \`bool                                   | None\`      | Whether the function requires a sequential/serial execution environment. Defaults to False. If None, the default value is determined by the toolset.                                                                                              |
| `requires_approval`              | \`bool                                   | None\`      | Whether this tool requires human-in-the-loop approval. Defaults to False. See the tools documentation for more info. If None, the default value is determined by the toolset.                                                                     |
| `metadata`                       | \`dict[str, Any]                         | None\`      | Optional metadata for the tool. This is not sent to the model but can be used for filtering and tool behavior customization. If None, the default value is determined by the toolset. If provided, it will be merged with the toolset's metadata. |
| `timeout`                        | \`float                                  | None\`      | Timeout in seconds for tool execution. If the tool takes longer, a retry prompt is returned to the model. Defaults to None (no timeout).                                                                                                          |

Source code in `pydantic_ai_slim/pydantic_ai/toolsets/function.py`

````python
def tool(
    self,
    func: ToolFuncEither[AgentDepsT, ToolParams] | None = None,
    /,
    *,
    name: str | None = None,
    description: str | None = None,
    retries: int | None = None,
    prepare: ToolPrepareFunc[AgentDepsT] | None = None,
    docstring_format: DocstringFormat | None = None,
    require_parameter_descriptions: bool | None = None,
    schema_generator: type[GenerateJsonSchema] | None = None,
    strict: bool | None = None,
    sequential: bool | None = None,
    requires_approval: bool | None = None,
    metadata: dict[str, Any] | None = None,
    timeout: float | None = None,
) -> Any:
    """Decorator to register a tool function which takes [`RunContext`][pydantic_ai.tools.RunContext] as its first argument.

    Can decorate a sync or async functions.

    The docstring is inspected to extract both the tool description and description of each parameter,
    [learn more](../tools.md#function-tools-and-schema).

    We can't add overloads for every possible signature of tool, since the return type is a recursive union
    so the signature of functions decorated with `@toolset.tool` is obscured.

    Example:
    ```python
    from pydantic_ai import Agent, FunctionToolset, RunContext

    toolset = FunctionToolset()

    @toolset.tool
    def foobar(ctx: RunContext[int], x: int) -> int:
        return ctx.deps + x

    @toolset.tool(retries=2)
    async def spam(ctx: RunContext[str], y: float) -> float:
        return ctx.deps + y

    agent = Agent('test', toolsets=[toolset], deps_type=int)
    result = agent.run_sync('foobar', deps=1)
    print(result.output)
    #> {"foobar":1,"spam":1.0}
    ```

    Args:
        func: The tool function to register.
        name: The name of the tool, defaults to the function name.
        description: The description of the tool,defaults to the function docstring.
        retries: The number of retries to allow for this tool, defaults to the agent's default retries,
            which defaults to 1.
        prepare: custom method to prepare the tool definition for each step, return `None` to omit this
            tool from a given step. This is useful if you want to customise a tool at call time,
            or omit it completely from a step. See [`ToolPrepareFunc`][pydantic_ai.tools.ToolPrepareFunc].
        docstring_format: The format of the docstring, see [`DocstringFormat`][pydantic_ai.tools.DocstringFormat].
            If `None`, the default value is determined by the toolset.
        require_parameter_descriptions: If True, raise an error if a parameter description is missing.
            If `None`, the default value is determined by the toolset.
        schema_generator: The JSON schema generator class to use for this tool.
            If `None`, the default value is determined by the toolset.
        strict: Whether to enforce JSON schema compliance (only affects OpenAI).
            See [`ToolDefinition`][pydantic_ai.tools.ToolDefinition] for more info.
            If `None`, the default value is determined by the toolset.
        sequential: Whether the function requires a sequential/serial execution environment. Defaults to False.
            If `None`, the default value is determined by the toolset.
        requires_approval: Whether this tool requires human-in-the-loop approval. Defaults to False.
            See the [tools documentation](../deferred-tools.md#human-in-the-loop-tool-approval) for more info.
            If `None`, the default value is determined by the toolset.
        metadata: Optional metadata for the tool. This is not sent to the model but can be used for filtering and tool behavior customization.
            If `None`, the default value is determined by the toolset. If provided, it will be merged with the toolset's metadata.
        timeout: Timeout in seconds for tool execution. If the tool takes longer, a retry prompt is returned to the model.
            Defaults to None (no timeout).
    """

    def tool_decorator(
        func_: ToolFuncEither[AgentDepsT, ToolParams],
    ) -> ToolFuncEither[AgentDepsT, ToolParams]:
        # noinspection PyTypeChecker
        self.add_function(
            func=func_,
            takes_ctx=None,
            name=name,
            description=description,
            retries=retries,
            prepare=prepare,
            docstring_format=docstring_format,
            require_parameter_descriptions=require_parameter_descriptions,
            schema_generator=schema_generator,
            strict=strict,
            sequential=sequential,
            requires_approval=requires_approval,
            metadata=metadata,
            timeout=timeout,
        )
        return func_

    return tool_decorator if func is None else tool_decorator(func)
````

#### add_function

```python
add_function(
    func: ToolFuncEither[AgentDepsT, ToolParams],
    takes_ctx: bool | None = None,
    name: str | None = None,
    description: str | None = None,
    retries: int | None = None,
    prepare: ToolPrepareFunc[AgentDepsT] | None = None,
    docstring_format: DocstringFormat | None = None,
    require_parameter_descriptions: bool | None = None,
    schema_generator: (
        type[GenerateJsonSchema] | None
    ) = None,
    strict: bool | None = None,
    sequential: bool | None = None,
    requires_approval: bool | None = None,
    metadata: dict[str, Any] | None = None,
    timeout: float | None = None,
) -> None
```

Add a function as a tool to the toolset.

Can take a sync or async function.

The docstring is inspected to extract both the tool description and description of each parameter, [learn more](https://ai.pydantic.dev/tools/#function-tools-and-schema).

Parameters:

| Name                             | Type                                     | Description                    | Default                                                                                                                                                                                                                                           |
| -------------------------------- | ---------------------------------------- | ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `func`                           | `ToolFuncEither[AgentDepsT, ToolParams]` | The tool function to register. | *required*                                                                                                                                                                                                                                        |
| `takes_ctx`                      | \`bool                                   | None\`                         | Whether the function takes a RunContext as its first argument. If None, this is inferred from the function signature.                                                                                                                             |
| `name`                           | \`str                                    | None\`                         | The name of the tool, defaults to the function name.                                                                                                                                                                                              |
| `description`                    | \`str                                    | None\`                         | The description of the tool, defaults to the function docstring.                                                                                                                                                                                  |
| `retries`                        | \`int                                    | None\`                         | The number of retries to allow for this tool, defaults to the agent's default retries, which defaults to 1.                                                                                                                                       |
| `prepare`                        | \`ToolPrepareFunc[AgentDepsT]            | None\`                         | custom method to prepare the tool definition for each step, return None to omit this tool from a given step. This is useful if you want to customise a tool at call time, or omit it completely from a step. See ToolPrepareFunc.                 |
| `docstring_format`               | \`DocstringFormat                        | None\`                         | The format of the docstring, see DocstringFormat. If None, the default value is determined by the toolset.                                                                                                                                        |
| `require_parameter_descriptions` | \`bool                                   | None\`                         | If True, raise an error if a parameter description is missing. If None, the default value is determined by the toolset.                                                                                                                           |
| `schema_generator`               | \`type[GenerateJsonSchema]               | None\`                         | The JSON schema generator class to use for this tool. If None, the default value is determined by the toolset.                                                                                                                                    |
| `strict`                         | \`bool                                   | None\`                         | Whether to enforce JSON schema compliance (only affects OpenAI). See ToolDefinition for more info. If None, the default value is determined by the toolset.                                                                                       |
| `sequential`                     | \`bool                                   | None\`                         | Whether the function requires a sequential/serial execution environment. Defaults to False. If None, the default value is determined by the toolset.                                                                                              |
| `requires_approval`              | \`bool                                   | None\`                         | Whether this tool requires human-in-the-loop approval. Defaults to False. See the tools documentation for more info. If None, the default value is determined by the toolset.                                                                     |
| `metadata`                       | \`dict[str, Any]                         | None\`                         | Optional metadata for the tool. This is not sent to the model but can be used for filtering and tool behavior customization. If None, the default value is determined by the toolset. If provided, it will be merged with the toolset's metadata. |
| `timeout`                        | \`float                                  | None\`                         | Timeout in seconds for tool execution. If the tool takes longer, a retry prompt is returned to the model. Defaults to None (no timeout).                                                                                                          |

Source code in `pydantic_ai_slim/pydantic_ai/toolsets/function.py`

```python
def add_function(
    self,
    func: ToolFuncEither[AgentDepsT, ToolParams],
    takes_ctx: bool | None = None,
    name: str | None = None,
    description: str | None = None,
    retries: int | None = None,
    prepare: ToolPrepareFunc[AgentDepsT] | None = None,
    docstring_format: DocstringFormat | None = None,
    require_parameter_descriptions: bool | None = None,
    schema_generator: type[GenerateJsonSchema] | None = None,
    strict: bool | None = None,
    sequential: bool | None = None,
    requires_approval: bool | None = None,
    metadata: dict[str, Any] | None = None,
    timeout: float | None = None,
) -> None:
    """Add a function as a tool to the toolset.

    Can take a sync or async function.

    The docstring is inspected to extract both the tool description and description of each parameter,
    [learn more](../tools.md#function-tools-and-schema).

    Args:
        func: The tool function to register.
        takes_ctx: Whether the function takes a [`RunContext`][pydantic_ai.tools.RunContext] as its first argument. If `None`, this is inferred from the function signature.
        name: The name of the tool, defaults to the function name.
        description: The description of the tool, defaults to the function docstring.
        retries: The number of retries to allow for this tool, defaults to the agent's default retries,
            which defaults to 1.
        prepare: custom method to prepare the tool definition for each step, return `None` to omit this
            tool from a given step. This is useful if you want to customise a tool at call time,
            or omit it completely from a step. See [`ToolPrepareFunc`][pydantic_ai.tools.ToolPrepareFunc].
        docstring_format: The format of the docstring, see [`DocstringFormat`][pydantic_ai.tools.DocstringFormat].
            If `None`, the default value is determined by the toolset.
        require_parameter_descriptions: If True, raise an error if a parameter description is missing.
            If `None`, the default value is determined by the toolset.
        schema_generator: The JSON schema generator class to use for this tool.
            If `None`, the default value is determined by the toolset.
        strict: Whether to enforce JSON schema compliance (only affects OpenAI).
            See [`ToolDefinition`][pydantic_ai.tools.ToolDefinition] for more info.
            If `None`, the default value is determined by the toolset.
        sequential: Whether the function requires a sequential/serial execution environment. Defaults to False.
            If `None`, the default value is determined by the toolset.
        requires_approval: Whether this tool requires human-in-the-loop approval. Defaults to False.
            See the [tools documentation](../deferred-tools.md#human-in-the-loop-tool-approval) for more info.
            If `None`, the default value is determined by the toolset.
        metadata: Optional metadata for the tool. This is not sent to the model but can be used for filtering and tool behavior customization.
            If `None`, the default value is determined by the toolset. If provided, it will be merged with the toolset's metadata.
        timeout: Timeout in seconds for tool execution. If the tool takes longer, a retry prompt is returned to the model.
            Defaults to None (no timeout).
    """
    if docstring_format is None:
        docstring_format = self.docstring_format
    if require_parameter_descriptions is None:
        require_parameter_descriptions = self.require_parameter_descriptions
    if schema_generator is None:
        schema_generator = self.schema_generator
    if strict is None:
        strict = self.strict
    if sequential is None:
        sequential = self.sequential
    if requires_approval is None:
        requires_approval = self.requires_approval

    tool = Tool[AgentDepsT](
        func,
        takes_ctx=takes_ctx,
        name=name,
        description=description,
        max_retries=retries,
        prepare=prepare,
        docstring_format=docstring_format,
        require_parameter_descriptions=require_parameter_descriptions,
        schema_generator=schema_generator,
        strict=strict,
        sequential=sequential,
        requires_approval=requires_approval,
        metadata=metadata,
        timeout=timeout,
    )
    self.add_tool(tool)
```

#### add_tool

```python
add_tool(tool: Tool[AgentDepsT]) -> None
```

Add a tool to the toolset.

Parameters:

| Name   | Type               | Description      | Default    |
| ------ | ------------------ | ---------------- | ---------- |
| `tool` | `Tool[AgentDepsT]` | The tool to add. | *required* |

Source code in `pydantic_ai_slim/pydantic_ai/toolsets/function.py`

```python
def add_tool(self, tool: Tool[AgentDepsT]) -> None:
    """Add a tool to the toolset.

    Args:
        tool: The tool to add.
    """
    if tool.name in self.tools:
        raise UserError(f'Tool name conflicts with existing tool: {tool.name!r}')
    if tool.max_retries is None:
        tool.max_retries = self.max_retries
    if self.metadata is not None:
        tool.metadata = self.metadata | (tool.metadata or {})
    self.tools[tool.name] = tool
```

### PrefixedToolset

Bases: `WrapperToolset[AgentDepsT]`

A toolset that prefixes the names of the tools it contains.

See [toolset docs](https://ai.pydantic.dev/toolsets/#prefixing-tool-names) for more information.

Source code in `pydantic_ai_slim/pydantic_ai/toolsets/prefixed.py`

```python
@dataclass
class PrefixedToolset(WrapperToolset[AgentDepsT]):
    """A toolset that prefixes the names of the tools it contains.

    See [toolset docs](../toolsets.md#prefixing-tool-names) for more information.
    """

    prefix: str

    @property
    def tool_name_conflict_hint(self) -> str:
        return 'Change the `prefix` attribute to avoid name conflicts.'

    async def get_tools(self, ctx: RunContext[AgentDepsT]) -> dict[str, ToolsetTool[AgentDepsT]]:
        return {
            new_name: replace(
                tool,
                toolset=self,
                tool_def=replace(tool.tool_def, name=new_name),
            )
            for name, tool in (await super().get_tools(ctx)).items()
            if (new_name := f'{self.prefix}_{name}')
        }

    async def call_tool(
        self, name: str, tool_args: dict[str, Any], ctx: RunContext[AgentDepsT], tool: ToolsetTool[AgentDepsT]
    ) -> Any:
        original_name = name.removeprefix(self.prefix + '_')
        ctx = replace(ctx, tool_name=original_name)
        tool = replace(tool, tool_def=replace(tool.tool_def, name=original_name))
        return await super().call_tool(original_name, tool_args, ctx, tool)
```

### RenamedToolset

Bases: `WrapperToolset[AgentDepsT]`

A toolset that renames the tools it contains using a dictionary mapping new names to original names.

See [toolset docs](https://ai.pydantic.dev/toolsets/#renaming-tools) for more information.

Source code in `pydantic_ai_slim/pydantic_ai/toolsets/renamed.py`

```python
@dataclass
class RenamedToolset(WrapperToolset[AgentDepsT]):
    """A toolset that renames the tools it contains using a dictionary mapping new names to original names.

    See [toolset docs](../toolsets.md#renaming-tools) for more information.
    """

    name_map: dict[str, str]

    async def get_tools(self, ctx: RunContext[AgentDepsT]) -> dict[str, ToolsetTool[AgentDepsT]]:
        original_to_new_name_map = {v: k for k, v in self.name_map.items()}
        original_tools = await super().get_tools(ctx)
        tools: dict[str, ToolsetTool[AgentDepsT]] = {}
        for original_name, tool in original_tools.items():
            new_name = original_to_new_name_map.get(original_name, None)
            if new_name:
                tools[new_name] = replace(
                    tool,
                    toolset=self,
                    tool_def=replace(tool.tool_def, name=new_name),
                )
            else:
                tools[original_name] = tool
        return tools

    async def call_tool(
        self, name: str, tool_args: dict[str, Any], ctx: RunContext[AgentDepsT], tool: ToolsetTool[AgentDepsT]
    ) -> Any:
        original_name = self.name_map.get(name, name)
        ctx = replace(ctx, tool_name=original_name)
        tool = replace(tool, tool_def=replace(tool.tool_def, name=original_name))
        return await super().call_tool(original_name, tool_args, ctx, tool)
```

### PreparedToolset

Bases: `WrapperToolset[AgentDepsT]`

A toolset that prepares the tools it contains using a prepare function that takes the agent context and the original tool definitions.

See [toolset docs](https://ai.pydantic.dev/toolsets/#preparing-tool-definitions) for more information.

Source code in `pydantic_ai_slim/pydantic_ai/toolsets/prepared.py`

```python
@dataclass
class PreparedToolset(WrapperToolset[AgentDepsT]):
    """A toolset that prepares the tools it contains using a prepare function that takes the agent context and the original tool definitions.

    See [toolset docs](../toolsets.md#preparing-tool-definitions) for more information.
    """

    prepare_func: ToolsPrepareFunc[AgentDepsT]

    async def get_tools(self, ctx: RunContext[AgentDepsT]) -> dict[str, ToolsetTool[AgentDepsT]]:
        original_tools = await super().get_tools(ctx)
        original_tool_defs = [tool.tool_def for tool in original_tools.values()]
        prepared_tool_defs_by_name = {
            tool_def.name: tool_def for tool_def in (await self.prepare_func(ctx, original_tool_defs) or [])
        }

        if len(prepared_tool_defs_by_name.keys() - original_tools.keys()) > 0:
            raise UserError(
                'Prepare function cannot add or rename tools. Use `FunctionToolset.add_function()` or `RenamedToolset` instead.'
            )

        return {
            name: replace(original_tools[name], tool_def=tool_def)
            for name, tool_def in prepared_tool_defs_by_name.items()
        }
```

### WrapperToolset

Bases: `AbstractToolset[AgentDepsT]`

A toolset that wraps another toolset and delegates to it.

See [toolset docs](https://ai.pydantic.dev/toolsets/#wrapping-a-toolset) for more information.

Source code in `pydantic_ai_slim/pydantic_ai/toolsets/wrapper.py`

```python
@dataclass
class WrapperToolset(AbstractToolset[AgentDepsT]):
    """A toolset that wraps another toolset and delegates to it.

    See [toolset docs](../toolsets.md#wrapping-a-toolset) for more information.
    """

    wrapped: AbstractToolset[AgentDepsT]

    @property
    def id(self) -> str | None:
        return None  # pragma: no cover

    @property
    def label(self) -> str:
        return f'{self.__class__.__name__}({self.wrapped.label})'

    async def __aenter__(self) -> Self:
        await self.wrapped.__aenter__()
        return self

    async def __aexit__(self, *args: Any) -> bool | None:
        return await self.wrapped.__aexit__(*args)

    async def get_tools(self, ctx: RunContext[AgentDepsT]) -> dict[str, ToolsetTool[AgentDepsT]]:
        return await self.wrapped.get_tools(ctx)

    async def call_tool(
        self, name: str, tool_args: dict[str, Any], ctx: RunContext[AgentDepsT], tool: ToolsetTool[AgentDepsT]
    ) -> Any:
        return await self.wrapped.call_tool(name, tool_args, ctx, tool)

    def apply(self, visitor: Callable[[AbstractToolset[AgentDepsT]], None]) -> None:
        self.wrapped.apply(visitor)

    def visit_and_replace(
        self, visitor: Callable[[AbstractToolset[AgentDepsT]], AbstractToolset[AgentDepsT]]
    ) -> AbstractToolset[AgentDepsT]:
        return replace(self, wrapped=self.wrapped.visit_and_replace(visitor))
```

### ToolsetFunc

```python
ToolsetFunc: TypeAlias = Callable[
    [RunContext[AgentDepsT]],
    AbstractToolset[AgentDepsT]
    | None
    | Awaitable[AbstractToolset[AgentDepsT] | None],
]
```

A sync/async function which takes a run context and returns a toolset.

### FastMCPToolset

Bases: `AbstractToolset[AgentDepsT]`

A FastMCP Toolset that uses the FastMCP Client to call tools from a local or remote MCP Server.

The Toolset can accept a FastMCP Client, a FastMCP Transport, or any other object which a FastMCP Transport can be created from.

See https://gofastmcp.com/clients/transports for a full list of transports available.

Source code in `pydantic_ai_slim/pydantic_ai/toolsets/fastmcp.py`

```python
@dataclass(init=False)
class FastMCPToolset(AbstractToolset[AgentDepsT]):
    """A FastMCP Toolset that uses the FastMCP Client to call tools from a local or remote MCP Server.

    The Toolset can accept a FastMCP Client, a FastMCP Transport, or any other object which a FastMCP Transport can be created from.

    See https://gofastmcp.com/clients/transports for a full list of transports available.
    """

    client: Client[Any]
    """The FastMCP client to use."""

    _: KW_ONLY

    tool_error_behavior: Literal['model_retry', 'error']
    """The behavior to take when a tool error occurs."""

    max_retries: int
    """The maximum number of retries to attempt if a tool call fails."""

    _id: str | None

    def __init__(
        self,
        client: Client[Any]
        | ClientTransport
        | FastMCP
        | FastMCP1Server
        | AnyUrl
        | Path
        | MCPConfig
        | dict[str, Any]
        | str,
        *,
        max_retries: int = 1,
        tool_error_behavior: Literal['model_retry', 'error'] = 'model_retry',
        id: str | None = None,
    ) -> None:
        if isinstance(client, Client):
            self.client = client
        else:
            self.client = Client[Any](transport=client)

        self._id = id
        self.max_retries = max_retries
        self.tool_error_behavior = tool_error_behavior

        self._enter_lock: Lock = Lock()
        self._running_count: int = 0
        self._exit_stack: AsyncExitStack | None = None

    @property
    def id(self) -> str | None:
        return self._id

    async def __aenter__(self) -> Self:
        async with self._enter_lock:
            if self._running_count == 0:
                self._exit_stack = AsyncExitStack()
                await self._exit_stack.enter_async_context(self.client)

            self._running_count += 1

        return self

    async def __aexit__(self, *args: Any) -> bool | None:
        async with self._enter_lock:
            self._running_count -= 1
            if self._running_count == 0 and self._exit_stack:
                await self._exit_stack.aclose()
                self._exit_stack = None

        return None

    async def get_tools(self, ctx: RunContext[AgentDepsT]) -> dict[str, ToolsetTool[AgentDepsT]]:
        async with self:
            return {
                mcp_tool.name: self.tool_for_tool_def(
                    ToolDefinition(
                        name=mcp_tool.name,
                        description=mcp_tool.description,
                        parameters_json_schema=mcp_tool.inputSchema,
                        metadata={
                            'meta': mcp_tool.meta,
                            'annotations': mcp_tool.annotations.model_dump() if mcp_tool.annotations else None,
                            'output_schema': mcp_tool.outputSchema or None,
                        },
                    )
                )
                for mcp_tool in await self.client.list_tools()
            }

    async def call_tool(
        self, name: str, tool_args: dict[str, Any], ctx: RunContext[AgentDepsT], tool: ToolsetTool[AgentDepsT]
    ) -> Any:
        async with self:
            try:
                call_tool_result: CallToolResult = await self.client.call_tool(name=name, arguments=tool_args)
            except ToolError as e:
                if self.tool_error_behavior == 'model_retry':
                    raise ModelRetry(message=str(e)) from e
                else:
                    raise e

        # If we have structured content, return that
        if call_tool_result.structured_content:
            return call_tool_result.structured_content

        # Otherwise, return the content
        return _map_fastmcp_tool_results(parts=call_tool_result.content)

    def tool_for_tool_def(self, tool_def: ToolDefinition) -> ToolsetTool[AgentDepsT]:
        return ToolsetTool[AgentDepsT](
            tool_def=tool_def,
            toolset=self,
            max_retries=self.max_retries,
            args_validator=TOOL_SCHEMA_VALIDATOR,
        )
```

#### client

```python
client: Client[Any]
```

The FastMCP client to use.

#### max_retries

```python
max_retries: int = max_retries
```

The maximum number of retries to attempt if a tool call fails.

#### tool_error_behavior

```python
tool_error_behavior: Literal["model_retry", "error"] = (
    tool_error_behavior
)
```

The behavior to take when a tool error occurs.
