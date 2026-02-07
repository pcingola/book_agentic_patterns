# `pydantic_ai.tools`

### AgentDepsT

```python
AgentDepsT = TypeVar(
    "AgentDepsT", default=None, contravariant=True
)
```

Type variable for agent dependencies.

### RunContext

Bases: `Generic[RunContextAgentDepsT]`

Information about the current call.

Source code in `pydantic_ai_slim/pydantic_ai/_run_context.py`

```python
@dataclasses.dataclass(repr=False, kw_only=True)
class RunContext(Generic[RunContextAgentDepsT]):
    """Information about the current call."""

    deps: RunContextAgentDepsT
    """Dependencies for the agent."""
    model: Model
    """The model used in this run."""
    usage: RunUsage
    """LLM usage associated with the run."""
    prompt: str | Sequence[_messages.UserContent] | None = None
    """The original user prompt passed to the run."""
    messages: list[_messages.ModelMessage] = field(default_factory=list[_messages.ModelMessage])
    """Messages exchanged in the conversation so far."""
    validation_context: Any = None
    """Pydantic [validation context](https://docs.pydantic.dev/latest/concepts/validators/#validation-context) for tool args and run outputs."""
    tracer: Tracer = field(default_factory=NoOpTracer)
    """The tracer to use for tracing the run."""
    trace_include_content: bool = False
    """Whether to include the content of the messages in the trace."""
    instrumentation_version: int = DEFAULT_INSTRUMENTATION_VERSION
    """Instrumentation settings version, if instrumentation is enabled."""
    retries: dict[str, int] = field(default_factory=dict[str, int])
    """Number of retries for each tool so far."""
    tool_call_id: str | None = None
    """The ID of the tool call."""
    tool_name: str | None = None
    """Name of the tool being called."""
    retry: int = 0
    """Number of retries so far.

    For tool calls, this is the number of retries of the specific tool.
    For output validation, this is the number of output validation retries.
    """
    max_retries: int = 0
    """The maximum number of retries allowed.

    For tool calls, this is the maximum retries for the specific tool.
    For output validation, this is the maximum output validation retries.
    """
    run_step: int = 0
    """The current step in the run."""
    tool_call_approved: bool = False
    """Whether a tool call that required approval has now been approved."""
    tool_call_metadata: Any = None
    """Metadata from `DeferredToolResults.metadata[tool_call_id]`, available when `tool_call_approved=True`."""
    partial_output: bool = False
    """Whether the output passed to an output validator is partial."""
    run_id: str | None = None
    """"Unique identifier for the agent run."""
    metadata: dict[str, Any] | None = None
    """Metadata associated with this agent run, if configured."""

    @property
    def last_attempt(self) -> bool:
        """Whether this is the last attempt at running this tool before an error is raised."""
        return self.retry == self.max_retries

    __repr__ = _utils.dataclasses_no_defaults_repr
```

#### deps

```python
deps: RunContextAgentDepsT
```

Dependencies for the agent.

#### model

```python
model: Model
```

The model used in this run.

#### usage

```python
usage: RunUsage
```

LLM usage associated with the run.

#### prompt

```python
prompt: str | Sequence[UserContent] | None = None
```

The original user prompt passed to the run.

#### messages

```python
messages: list[ModelMessage] = field(
    default_factory=list[ModelMessage]
)
```

Messages exchanged in the conversation so far.

#### validation_context

```python
validation_context: Any = None
```

Pydantic [validation context](https://docs.pydantic.dev/latest/concepts/validators/#validation-context) for tool args and run outputs.

#### tracer

```python
tracer: Tracer = field(default_factory=NoOpTracer)
```

The tracer to use for tracing the run.

#### trace_include_content

```python
trace_include_content: bool = False
```

Whether to include the content of the messages in the trace.

#### instrumentation_version

```python
instrumentation_version: int = (
    DEFAULT_INSTRUMENTATION_VERSION
)
```

Instrumentation settings version, if instrumentation is enabled.

#### retries

```python
retries: dict[str, int] = field(
    default_factory=dict[str, int]
)
```

Number of retries for each tool so far.

#### tool_call_id

```python
tool_call_id: str | None = None
```

The ID of the tool call.

#### tool_name

```python
tool_name: str | None = None
```

Name of the tool being called.

#### retry

```python
retry: int = 0
```

Number of retries so far.

For tool calls, this is the number of retries of the specific tool. For output validation, this is the number of output validation retries.

#### max_retries

```python
max_retries: int = 0
```

The maximum number of retries allowed.

For tool calls, this is the maximum retries for the specific tool. For output validation, this is the maximum output validation retries.

#### run_step

```python
run_step: int = 0
```

The current step in the run.

#### tool_call_approved

```python
tool_call_approved: bool = False
```

Whether a tool call that required approval has now been approved.

#### tool_call_metadata

```python
tool_call_metadata: Any = None
```

Metadata from `DeferredToolResults.metadata[tool_call_id]`, available when `tool_call_approved=True`.

#### partial_output

```python
partial_output: bool = False
```

Whether the output passed to an output validator is partial.

#### run_id

```python
run_id: str | None = None
```

"Unique identifier for the agent run.

#### metadata

```python
metadata: dict[str, Any] | None = None
```

Metadata associated with this agent run, if configured.

#### last_attempt

```python
last_attempt: bool
```

Whether this is the last attempt at running this tool before an error is raised.

### ToolParams

```python
ToolParams = ParamSpec('ToolParams', default=...)
```

Retrieval function param spec.

### SystemPromptFunc

```python
SystemPromptFunc: TypeAlias = (
    Callable[[RunContext[AgentDepsT]], str | None]
    | Callable[
        [RunContext[AgentDepsT]], Awaitable[str | None]
    ]
    | Callable[[], str | None]
    | Callable[[], Awaitable[str | None]]
)
```

A function that may or maybe not take `RunContext` as an argument, and may or may not be async.

Functions which return None are excluded from model requests.

Usage `SystemPromptFunc[AgentDepsT]`.

### ToolFuncContext

```python
ToolFuncContext: TypeAlias = Callable[
    Concatenate[RunContext[AgentDepsT], ToolParams], Any
]
```

A tool function that takes `RunContext` as the first argument.

Usage `ToolContextFunc[AgentDepsT, ToolParams]`.

### ToolFuncPlain

```python
ToolFuncPlain: TypeAlias = Callable[ToolParams, Any]
```

A tool function that does not take `RunContext` as the first argument.

Usage `ToolPlainFunc[ToolParams]`.

### ToolFuncEither

```python
ToolFuncEither: TypeAlias = (
    ToolFuncContext[AgentDepsT, ToolParams]
    | ToolFuncPlain[ToolParams]
)
```

Either kind of tool function.

This is just a union of ToolFuncContext and ToolFuncPlain.

Usage `ToolFuncEither[AgentDepsT, ToolParams]`.

### ToolPrepareFunc

```python
ToolPrepareFunc: TypeAlias = Callable[
    [RunContext[AgentDepsT], "ToolDefinition"],
    Awaitable["ToolDefinition | None"],
]
```

Definition of a function that can prepare a tool definition at call time.

See [tool docs](https://ai.pydantic.dev/tools-advanced/#tool-prepare) for more information.

Example â€” here `only_if_42` is valid as a `ToolPrepareFunc`:

```python
from pydantic_ai import RunContext, Tool
from pydantic_ai.tools import ToolDefinition

async def only_if_42(
    ctx: RunContext[int], tool_def: ToolDefinition
) -> ToolDefinition | None:
    if ctx.deps == 42:
        return tool_def

def hitchhiker(ctx: RunContext[int], answer: str) -> str:
    return f'{ctx.deps} {answer}'

hitchhiker = Tool(hitchhiker, prepare=only_if_42)
```

Usage `ToolPrepareFunc[AgentDepsT]`.

### ToolsPrepareFunc

```python
ToolsPrepareFunc: TypeAlias = Callable[
    [RunContext[AgentDepsT], list["ToolDefinition"]],
    Awaitable["list[ToolDefinition] | None"],
]
```

Definition of a function that can prepare the tool definition of all tools for each step. This is useful if you want to customize the definition of multiple tools or you want to register a subset of tools for a given step.

Example â€” here `turn_on_strict_if_openai` is valid as a `ToolsPrepareFunc`:

```python
from dataclasses import replace

from pydantic_ai import Agent, RunContext
from pydantic_ai.tools import ToolDefinition


async def turn_on_strict_if_openai(
    ctx: RunContext[None], tool_defs: list[ToolDefinition]
) -> list[ToolDefinition] | None:
    if ctx.model.system == 'openai':
        return [replace(tool_def, strict=True) for tool_def in tool_defs]
    return tool_defs

agent = Agent('openai:gpt-5.2', prepare_tools=turn_on_strict_if_openai)
```

Usage `ToolsPrepareFunc[AgentDepsT]`.

### BuiltinToolFunc

```python
BuiltinToolFunc: TypeAlias = Callable[
    [RunContext[AgentDepsT]],
    Awaitable[AbstractBuiltinTool | None]
    | AbstractBuiltinTool
    | None,
]
```

Definition of a function that can prepare a builtin tool at call time.

This is useful if you want to customize the builtin tool based on the run context (e.g. user dependencies), or omit it completely from a step.

### DocstringFormat

```python
DocstringFormat: TypeAlias = Literal[
    "google", "numpy", "sphinx", "auto"
]
```

Supported docstring formats.

- `'google'` â€” [Google-style](https://google.github.io/styleguide/pyguide.html#381-docstrings) docstrings.
- `'numpy'` â€” [Numpy-style](https://numpydoc.readthedocs.io/en/latest/format.html) docstrings.
- `'sphinx'` â€” [Sphinx-style](https://sphinx-rtd-tutorial.readthedocs.io/en/latest/docstrings.html#the-sphinx-docstring-format) docstrings.
- `'auto'` â€” Automatically infer the format based on the structure of the docstring.

### DeferredToolRequests

Tool calls that require approval or external execution.

This can be used as an agent's `output_type` and will be used as the output of the agent run if the model called any deferred tools.

Results can be passed to the next agent run using a DeferredToolResults object with the same tool call IDs.

See [deferred tools docs](https://ai.pydantic.dev/deferred-tools/#deferred-tools) for more information.

Source code in `pydantic_ai_slim/pydantic_ai/tools.py`

```python
@dataclass(kw_only=True)
class DeferredToolRequests:
    """Tool calls that require approval or external execution.

    This can be used as an agent's `output_type` and will be used as the output of the agent run if the model called any deferred tools.

    Results can be passed to the next agent run using a [`DeferredToolResults`][pydantic_ai.tools.DeferredToolResults] object with the same tool call IDs.

    See [deferred tools docs](../deferred-tools.md#deferred-tools) for more information.
    """

    calls: list[ToolCallPart] = field(default_factory=list[ToolCallPart])
    """Tool calls that require external execution."""
    approvals: list[ToolCallPart] = field(default_factory=list[ToolCallPart])
    """Tool calls that require human-in-the-loop approval."""
    metadata: dict[str, dict[str, Any]] = field(default_factory=dict[str, dict[str, Any]])
    """Metadata for deferred tool calls, keyed by `tool_call_id`."""
```

#### calls

```python
calls: list[ToolCallPart] = field(
    default_factory=list[ToolCallPart]
)
```

Tool calls that require external execution.

#### approvals

```python
approvals: list[ToolCallPart] = field(
    default_factory=list[ToolCallPart]
)
```

Tool calls that require human-in-the-loop approval.

#### metadata

```python
metadata: dict[str, dict[str, Any]] = field(
    default_factory=dict[str, dict[str, Any]]
)
```

Metadata for deferred tool calls, keyed by `tool_call_id`.

### ToolApproved

Indicates that a tool call has been approved and that the tool function should be executed.

Source code in `pydantic_ai_slim/pydantic_ai/tools.py`

```python
@dataclass(kw_only=True)
class ToolApproved:
    """Indicates that a tool call has been approved and that the tool function should be executed."""

    override_args: dict[str, Any] | None = None
    """Optional tool call arguments to use instead of the original arguments."""

    kind: Literal['tool-approved'] = 'tool-approved'
```

#### override_args

```python
override_args: dict[str, Any] | None = None
```

Optional tool call arguments to use instead of the original arguments.

### ToolDenied

Indicates that a tool call has been denied and that a denial message should be returned to the model.

Source code in `pydantic_ai_slim/pydantic_ai/tools.py`

```python
@dataclass
class ToolDenied:
    """Indicates that a tool call has been denied and that a denial message should be returned to the model."""

    message: str = 'The tool call was denied.'
    """The message to return to the model."""

    _: KW_ONLY

    kind: Literal['tool-denied'] = 'tool-denied'
```

#### message

```python
message: str = 'The tool call was denied.'
```

The message to return to the model.

### DeferredToolApprovalResult

```python
DeferredToolApprovalResult: TypeAlias = Annotated[
    ToolApproved | ToolDenied, Discriminator("kind")
]
```

Result for a tool call that required human-in-the-loop approval.

### DeferredToolCallResult

```python
DeferredToolCallResult: TypeAlias = Annotated[
    Annotated[ToolReturn, Tag("tool-return")]
    | Annotated[ModelRetry, Tag("model-retry")]
    | Annotated[RetryPromptPart, Tag("retry-prompt")],
    Discriminator(_deferred_tool_call_result_discriminator),
]
```

Result for a tool call that required external execution.

### DeferredToolResult

```python
DeferredToolResult = (
    DeferredToolApprovalResult | DeferredToolCallResult
)
```

Result for a tool call that required approval or external execution.

### DeferredToolResults

Results for deferred tool calls from a previous run that required approval or external execution.

The tool call IDs need to match those from the DeferredToolRequests output object from the previous run.

See [deferred tools docs](https://ai.pydantic.dev/deferred-tools/#deferred-tools) for more information.

Source code in `pydantic_ai_slim/pydantic_ai/tools.py`

```python
@dataclass(kw_only=True)
class DeferredToolResults:
    """Results for deferred tool calls from a previous run that required approval or external execution.

    The tool call IDs need to match those from the [`DeferredToolRequests`][pydantic_ai.output.DeferredToolRequests] output object from the previous run.

    See [deferred tools docs](../deferred-tools.md#deferred-tools) for more information.
    """

    calls: dict[str, DeferredToolCallResult | Any] = field(default_factory=dict[str, DeferredToolCallResult | Any])
    """Map of tool call IDs to results for tool calls that required external execution."""
    approvals: dict[str, bool | DeferredToolApprovalResult] = field(
        default_factory=dict[str, bool | DeferredToolApprovalResult]
    )
    """Map of tool call IDs to results for tool calls that required human-in-the-loop approval."""
    metadata: dict[str, dict[str, Any]] = field(default_factory=dict[str, dict[str, Any]])
    """Metadata for deferred tool calls, keyed by `tool_call_id`. Each value will be available in the tool's RunContext as `tool_call_metadata`."""
```

#### calls

```python
calls: dict[str, DeferredToolCallResult | Any] = field(
    default_factory=dict[str, DeferredToolCallResult | Any]
)
```

Map of tool call IDs to results for tool calls that required external execution.

#### approvals

```python
approvals: dict[str, bool | DeferredToolApprovalResult] = (
    field(
        default_factory=dict[
            str, bool | DeferredToolApprovalResult
        ]
    )
)
```

Map of tool call IDs to results for tool calls that required human-in-the-loop approval.

#### metadata

```python
metadata: dict[str, dict[str, Any]] = field(
    default_factory=dict[str, dict[str, Any]]
)
```

Metadata for deferred tool calls, keyed by `tool_call_id`. Each value will be available in the tool's RunContext as `tool_call_metadata`.

### ToolAgentDepsT

```python
ToolAgentDepsT = TypeVar(
    "ToolAgentDepsT", default=object, contravariant=True
)
```

Type variable for agent dependencies for a tool.

### Tool

Bases: `Generic[ToolAgentDepsT]`

A tool function for an agent.

Source code in `pydantic_ai_slim/pydantic_ai/tools.py`

````python
@dataclass(init=False)
class Tool(Generic[ToolAgentDepsT]):
    """A tool function for an agent."""

    function: ToolFuncEither[ToolAgentDepsT]
    takes_ctx: bool
    max_retries: int | None
    name: str
    description: str | None
    prepare: ToolPrepareFunc[ToolAgentDepsT] | None
    docstring_format: DocstringFormat
    require_parameter_descriptions: bool
    strict: bool | None
    sequential: bool
    requires_approval: bool
    metadata: dict[str, Any] | None
    timeout: float | None
    function_schema: _function_schema.FunctionSchema
    """
    The base JSON schema for the tool's parameters.

    This schema may be modified by the `prepare` function or by the Model class prior to including it in an API request.
    """

    def __init__(
        self,
        function: ToolFuncEither[ToolAgentDepsT],
        *,
        takes_ctx: bool | None = None,
        max_retries: int | None = None,
        name: str | None = None,
        description: str | None = None,
        prepare: ToolPrepareFunc[ToolAgentDepsT] | None = None,
        docstring_format: DocstringFormat = 'auto',
        require_parameter_descriptions: bool = False,
        schema_generator: type[GenerateJsonSchema] = GenerateToolJsonSchema,
        strict: bool | None = None,
        sequential: bool = False,
        requires_approval: bool = False,
        metadata: dict[str, Any] | None = None,
        timeout: float | None = None,
        function_schema: _function_schema.FunctionSchema | None = None,
    ):
        """Create a new tool instance.

        Example usage:

        ```python {noqa="I001"}
        from pydantic_ai import Agent, RunContext, Tool

        async def my_tool(ctx: RunContext[int], x: int, y: int) -> str:
            return f'{ctx.deps} {x} {y}'

        agent = Agent('test', tools=[Tool(my_tool)])
        ```

        or with a custom prepare method:

        ```python {noqa="I001"}

        from pydantic_ai import Agent, RunContext, Tool
        from pydantic_ai.tools import ToolDefinition

        async def my_tool(ctx: RunContext[int], x: int, y: int) -> str:
            return f'{ctx.deps} {x} {y}'

        async def prep_my_tool(
            ctx: RunContext[int], tool_def: ToolDefinition
        ) -> ToolDefinition | None:
            # only register the tool if `deps == 42`
            if ctx.deps == 42:
                return tool_def

        agent = Agent('test', tools=[Tool(my_tool, prepare=prep_my_tool)])
        ```


        Args:
            function: The Python function to call as the tool.
            takes_ctx: Whether the function takes a [`RunContext`][pydantic_ai.tools.RunContext] first argument,
                this is inferred if unset.
            max_retries: Maximum number of retries allowed for this tool, set to the agent default if `None`.
            name: Name of the tool, inferred from the function if `None`.
            description: Description of the tool, inferred from the function if `None`.
            prepare: custom method to prepare the tool definition for each step, return `None` to omit this
                tool from a given step. This is useful if you want to customise a tool at call time,
                or omit it completely from a step. See [`ToolPrepareFunc`][pydantic_ai.tools.ToolPrepareFunc].
            docstring_format: The format of the docstring, see [`DocstringFormat`][pydantic_ai.tools.DocstringFormat].
                Defaults to `'auto'`, such that the format is inferred from the structure of the docstring.
            require_parameter_descriptions: If True, raise an error if a parameter description is missing. Defaults to False.
            schema_generator: The JSON schema generator class to use. Defaults to `GenerateToolJsonSchema`.
            strict: Whether to enforce JSON schema compliance (only affects OpenAI).
                See [`ToolDefinition`][pydantic_ai.tools.ToolDefinition] for more info.
            sequential: Whether the function requires a sequential/serial execution environment. Defaults to False.
            requires_approval: Whether this tool requires human-in-the-loop approval. Defaults to False.
                See the [tools documentation](../deferred-tools.md#human-in-the-loop-tool-approval) for more info.
            metadata: Optional metadata for the tool. This is not sent to the model but can be used for filtering and tool behavior customization.
            timeout: Timeout in seconds for tool execution. If the tool takes longer, a retry prompt is returned to the model.
                Defaults to None (no timeout).
            function_schema: The function schema to use for the tool. If not provided, it will be generated.
        """
        self.function = function
        self.function_schema = function_schema or _function_schema.function_schema(
            function,
            schema_generator,
            takes_ctx=takes_ctx,
            docstring_format=docstring_format,
            require_parameter_descriptions=require_parameter_descriptions,
        )
        self.takes_ctx = self.function_schema.takes_ctx
        self.max_retries = max_retries
        self.name = name or function.__name__
        self.description = description or self.function_schema.description
        self.prepare = prepare
        self.docstring_format = docstring_format
        self.require_parameter_descriptions = require_parameter_descriptions
        self.strict = strict
        self.sequential = sequential
        self.requires_approval = requires_approval
        self.metadata = metadata
        self.timeout = timeout

    @classmethod
    def from_schema(
        cls,
        function: Callable[..., Any],
        name: str,
        description: str | None,
        json_schema: JsonSchemaValue,
        takes_ctx: bool = False,
        sequential: bool = False,
    ) -> Self:
        """Creates a Pydantic tool from a function and a JSON schema.

        Args:
            function: The function to call.
                This will be called with keywords only, and no validation of
                the arguments will be performed.
            name: The unique name of the tool that clearly communicates its purpose
            description: Used to tell the model how/when/why to use the tool.
                You can provide few-shot examples as a part of the description.
            json_schema: The schema for the function arguments
            takes_ctx: An optional boolean parameter indicating whether the function
                accepts the context object as an argument.
            sequential: Whether the function requires a sequential/serial execution environment. Defaults to False.

        Returns:
            A Pydantic tool that calls the function
        """
        function_schema = _function_schema.FunctionSchema(
            function=function,
            description=description,
            validator=SchemaValidator(schema=core_schema.any_schema()),
            json_schema=json_schema,
            takes_ctx=takes_ctx,
            is_async=_utils.is_async_callable(function),
        )

        return cls(
            function,
            takes_ctx=takes_ctx,
            name=name,
            description=description,
            function_schema=function_schema,
            sequential=sequential,
        )

    @property
    def tool_def(self):
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters_json_schema=self.function_schema.json_schema,
            strict=self.strict,
            sequential=self.sequential,
            metadata=self.metadata,
            timeout=self.timeout,
            kind='unapproved' if self.requires_approval else 'function',
        )

    async def prepare_tool_def(self, ctx: RunContext[ToolAgentDepsT]) -> ToolDefinition | None:
        """Get the tool definition.

        By default, this method creates a tool definition, then either returns it, or calls `self.prepare`
        if it's set.

        Returns:
            return a `ToolDefinition` or `None` if the tools should not be registered for this run.
        """
        base_tool_def = self.tool_def

        if self.prepare is not None:
            return await self.prepare(ctx, base_tool_def)
        else:
            return base_tool_def
````

#### __init__

```python
__init__(
    function: ToolFuncEither[ToolAgentDepsT],
    *,
    takes_ctx: bool | None = None,
    max_retries: int | None = None,
    name: str | None = None,
    description: str | None = None,
    prepare: ToolPrepareFunc[ToolAgentDepsT] | None = None,
    docstring_format: DocstringFormat = "auto",
    require_parameter_descriptions: bool = False,
    schema_generator: type[
        GenerateJsonSchema
    ] = GenerateToolJsonSchema,
    strict: bool | None = None,
    sequential: bool = False,
    requires_approval: bool = False,
    metadata: dict[str, Any] | None = None,
    timeout: float | None = None,
    function_schema: FunctionSchema | None = None
)
```

Create a new tool instance.

Example usage:

```python
from pydantic_ai import Agent, RunContext, Tool

async def my_tool(ctx: RunContext[int], x: int, y: int) -> str:
    return f'{ctx.deps} {x} {y}'

agent = Agent('test', tools=[Tool(my_tool)])
```

or with a custom prepare method:

```python
from pydantic_ai import Agent, RunContext, Tool
from pydantic_ai.tools import ToolDefinition

async def my_tool(ctx: RunContext[int], x: int, y: int) -> str:
    return f'{ctx.deps} {x} {y}'

async def prep_my_tool(
    ctx: RunContext[int], tool_def: ToolDefinition
) -> ToolDefinition | None:
    # only register the tool if `deps == 42`
    if ctx.deps == 42:
        return tool_def

agent = Agent('test', tools=[Tool(my_tool, prepare=prep_my_tool)])
```

Parameters:

| Name                             | Type                              | Description                                                                                                                                 | Default                                                                                                                                                                                                                           |
| -------------------------------- | --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `function`                       | `ToolFuncEither[ToolAgentDepsT]`  | The Python function to call as the tool.                                                                                                    | *required*                                                                                                                                                                                                                        |
| `takes_ctx`                      | \`bool                            | None\`                                                                                                                                      | Whether the function takes a RunContext first argument, this is inferred if unset.                                                                                                                                                |
| `max_retries`                    | \`int                             | None\`                                                                                                                                      | Maximum number of retries allowed for this tool, set to the agent default if None.                                                                                                                                                |
| `name`                           | \`str                             | None\`                                                                                                                                      | Name of the tool, inferred from the function if None.                                                                                                                                                                             |
| `description`                    | \`str                             | None\`                                                                                                                                      | Description of the tool, inferred from the function if None.                                                                                                                                                                      |
| `prepare`                        | \`ToolPrepareFunc[ToolAgentDepsT] | None\`                                                                                                                                      | custom method to prepare the tool definition for each step, return None to omit this tool from a given step. This is useful if you want to customise a tool at call time, or omit it completely from a step. See ToolPrepareFunc. |
| `docstring_format`               | `DocstringFormat`                 | The format of the docstring, see DocstringFormat. Defaults to 'auto', such that the format is inferred from the structure of the docstring. | `'auto'`                                                                                                                                                                                                                          |
| `require_parameter_descriptions` | `bool`                            | If True, raise an error if a parameter description is missing. Defaults to False.                                                           | `False`                                                                                                                                                                                                                           |
| `schema_generator`               | `type[GenerateJsonSchema]`        | The JSON schema generator class to use. Defaults to GenerateToolJsonSchema.                                                                 | `GenerateToolJsonSchema`                                                                                                                                                                                                          |
| `strict`                         | \`bool                            | None\`                                                                                                                                      | Whether to enforce JSON schema compliance (only affects OpenAI). See ToolDefinition for more info.                                                                                                                                |
| `sequential`                     | `bool`                            | Whether the function requires a sequential/serial execution environment. Defaults to False.                                                 | `False`                                                                                                                                                                                                                           |
| `requires_approval`              | `bool`                            | Whether this tool requires human-in-the-loop approval. Defaults to False. See the tools documentation for more info.                        | `False`                                                                                                                                                                                                                           |
| `metadata`                       | \`dict[str, Any]                  | None\`                                                                                                                                      | Optional metadata for the tool. This is not sent to the model but can be used for filtering and tool behavior customization.                                                                                                      |
| `timeout`                        | \`float                           | None\`                                                                                                                                      | Timeout in seconds for tool execution. If the tool takes longer, a retry prompt is returned to the model. Defaults to None (no timeout).                                                                                          |
| `function_schema`                | \`FunctionSchema                  | None\`                                                                                                                                      | The function schema to use for the tool. If not provided, it will be generated.                                                                                                                                                   |

Source code in `pydantic_ai_slim/pydantic_ai/tools.py`

````python
def __init__(
    self,
    function: ToolFuncEither[ToolAgentDepsT],
    *,
    takes_ctx: bool | None = None,
    max_retries: int | None = None,
    name: str | None = None,
    description: str | None = None,
    prepare: ToolPrepareFunc[ToolAgentDepsT] | None = None,
    docstring_format: DocstringFormat = 'auto',
    require_parameter_descriptions: bool = False,
    schema_generator: type[GenerateJsonSchema] = GenerateToolJsonSchema,
    strict: bool | None = None,
    sequential: bool = False,
    requires_approval: bool = False,
    metadata: dict[str, Any] | None = None,
    timeout: float | None = None,
    function_schema: _function_schema.FunctionSchema | None = None,
):
    """Create a new tool instance.

    Example usage:

    ```python {noqa="I001"}
    from pydantic_ai import Agent, RunContext, Tool

    async def my_tool(ctx: RunContext[int], x: int, y: int) -> str:
        return f'{ctx.deps} {x} {y}'

    agent = Agent('test', tools=[Tool(my_tool)])
    ```

    or with a custom prepare method:

    ```python {noqa="I001"}

    from pydantic_ai import Agent, RunContext, Tool
    from pydantic_ai.tools import ToolDefinition

    async def my_tool(ctx: RunContext[int], x: int, y: int) -> str:
        return f'{ctx.deps} {x} {y}'

    async def prep_my_tool(
        ctx: RunContext[int], tool_def: ToolDefinition
    ) -> ToolDefinition | None:
        # only register the tool if `deps == 42`
        if ctx.deps == 42:
            return tool_def

    agent = Agent('test', tools=[Tool(my_tool, prepare=prep_my_tool)])
    ```


    Args:
        function: The Python function to call as the tool.
        takes_ctx: Whether the function takes a [`RunContext`][pydantic_ai.tools.RunContext] first argument,
            this is inferred if unset.
        max_retries: Maximum number of retries allowed for this tool, set to the agent default if `None`.
        name: Name of the tool, inferred from the function if `None`.
        description: Description of the tool, inferred from the function if `None`.
        prepare: custom method to prepare the tool definition for each step, return `None` to omit this
            tool from a given step. This is useful if you want to customise a tool at call time,
            or omit it completely from a step. See [`ToolPrepareFunc`][pydantic_ai.tools.ToolPrepareFunc].
        docstring_format: The format of the docstring, see [`DocstringFormat`][pydantic_ai.tools.DocstringFormat].
            Defaults to `'auto'`, such that the format is inferred from the structure of the docstring.
        require_parameter_descriptions: If True, raise an error if a parameter description is missing. Defaults to False.
        schema_generator: The JSON schema generator class to use. Defaults to `GenerateToolJsonSchema`.
        strict: Whether to enforce JSON schema compliance (only affects OpenAI).
            See [`ToolDefinition`][pydantic_ai.tools.ToolDefinition] for more info.
        sequential: Whether the function requires a sequential/serial execution environment. Defaults to False.
        requires_approval: Whether this tool requires human-in-the-loop approval. Defaults to False.
            See the [tools documentation](../deferred-tools.md#human-in-the-loop-tool-approval) for more info.
        metadata: Optional metadata for the tool. This is not sent to the model but can be used for filtering and tool behavior customization.
        timeout: Timeout in seconds for tool execution. If the tool takes longer, a retry prompt is returned to the model.
            Defaults to None (no timeout).
        function_schema: The function schema to use for the tool. If not provided, it will be generated.
    """
    self.function = function
    self.function_schema = function_schema or _function_schema.function_schema(
        function,
        schema_generator,
        takes_ctx=takes_ctx,
        docstring_format=docstring_format,
        require_parameter_descriptions=require_parameter_descriptions,
    )
    self.takes_ctx = self.function_schema.takes_ctx
    self.max_retries = max_retries
    self.name = name or function.__name__
    self.description = description or self.function_schema.description
    self.prepare = prepare
    self.docstring_format = docstring_format
    self.require_parameter_descriptions = require_parameter_descriptions
    self.strict = strict
    self.sequential = sequential
    self.requires_approval = requires_approval
    self.metadata = metadata
    self.timeout = timeout
````

#### function_schema

```python
function_schema: FunctionSchema = (
    function_schema
    or function_schema(
        function,
        schema_generator,
        takes_ctx=takes_ctx,
        docstring_format=docstring_format,
        require_parameter_descriptions=require_parameter_descriptions,
    )
)
```

The base JSON schema for the tool's parameters.

This schema may be modified by the `prepare` function or by the Model class prior to including it in an API request.

#### from_schema

```python
from_schema(
    function: Callable[..., Any],
    name: str,
    description: str | None,
    json_schema: JsonSchemaValue,
    takes_ctx: bool = False,
    sequential: bool = False,
) -> Self
```

Creates a Pydantic tool from a function and a JSON schema.

Parameters:

| Name          | Type                 | Description                                                                                                         | Default                                                                                                              |
| ------------- | -------------------- | ------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `function`    | `Callable[..., Any]` | The function to call. This will be called with keywords only, and no validation of the arguments will be performed. | *required*                                                                                                           |
| `name`        | `str`                | The unique name of the tool that clearly communicates its purpose                                                   | *required*                                                                                                           |
| `description` | \`str                | None\`                                                                                                              | Used to tell the model how/when/why to use the tool. You can provide few-shot examples as a part of the description. |
| `json_schema` | `JsonSchemaValue`    | The schema for the function arguments                                                                               | *required*                                                                                                           |
| `takes_ctx`   | `bool`               | An optional boolean parameter indicating whether the function accepts the context object as an argument.            | `False`                                                                                                              |
| `sequential`  | `bool`               | Whether the function requires a sequential/serial execution environment. Defaults to False.                         | `False`                                                                                                              |

Returns:

| Type   | Description                             |
| ------ | --------------------------------------- |
| `Self` | A Pydantic tool that calls the function |

Source code in `pydantic_ai_slim/pydantic_ai/tools.py`

```python
@classmethod
def from_schema(
    cls,
    function: Callable[..., Any],
    name: str,
    description: str | None,
    json_schema: JsonSchemaValue,
    takes_ctx: bool = False,
    sequential: bool = False,
) -> Self:
    """Creates a Pydantic tool from a function and a JSON schema.

    Args:
        function: The function to call.
            This will be called with keywords only, and no validation of
            the arguments will be performed.
        name: The unique name of the tool that clearly communicates its purpose
        description: Used to tell the model how/when/why to use the tool.
            You can provide few-shot examples as a part of the description.
        json_schema: The schema for the function arguments
        takes_ctx: An optional boolean parameter indicating whether the function
            accepts the context object as an argument.
        sequential: Whether the function requires a sequential/serial execution environment. Defaults to False.

    Returns:
        A Pydantic tool that calls the function
    """
    function_schema = _function_schema.FunctionSchema(
        function=function,
        description=description,
        validator=SchemaValidator(schema=core_schema.any_schema()),
        json_schema=json_schema,
        takes_ctx=takes_ctx,
        is_async=_utils.is_async_callable(function),
    )

    return cls(
        function,
        takes_ctx=takes_ctx,
        name=name,
        description=description,
        function_schema=function_schema,
        sequential=sequential,
    )
```

#### prepare_tool_def

```python
prepare_tool_def(
    ctx: RunContext[ToolAgentDepsT],
) -> ToolDefinition | None
```

Get the tool definition.

By default, this method creates a tool definition, then either returns it, or calls `self.prepare` if it's set.

Returns:

| Type             | Description |
| ---------------- | ----------- |
| \`ToolDefinition | None\`      |

Source code in `pydantic_ai_slim/pydantic_ai/tools.py`

```python
async def prepare_tool_def(self, ctx: RunContext[ToolAgentDepsT]) -> ToolDefinition | None:
    """Get the tool definition.

    By default, this method creates a tool definition, then either returns it, or calls `self.prepare`
    if it's set.

    Returns:
        return a `ToolDefinition` or `None` if the tools should not be registered for this run.
    """
    base_tool_def = self.tool_def

    if self.prepare is not None:
        return await self.prepare(ctx, base_tool_def)
    else:
        return base_tool_def
```

### ObjectJsonSchema

```python
ObjectJsonSchema: TypeAlias = dict[str, Any]
```

Type representing JSON schema of an object, e.g. where `"type": "object"`.

This type is used to define tools parameters (aka arguments) in ToolDefinition.

With PEP-728 this should be a TypedDict with `type: Literal['object']`, and `extra_parts=Any`

### ToolKind

```python
ToolKind: TypeAlias = Literal[
    "function", "output", "external", "unapproved"
]
```

Kind of tool.

### ToolDefinition

Definition of a tool passed to a model.

This is used for both function tools and output tools.

Source code in `pydantic_ai_slim/pydantic_ai/tools.py`

```python
@dataclass(repr=False, kw_only=True)
class ToolDefinition:
    """Definition of a tool passed to a model.

    This is used for both function tools and output tools.
    """

    name: str
    """The name of the tool."""

    parameters_json_schema: ObjectJsonSchema = field(default_factory=lambda: {'type': 'object', 'properties': {}})
    """The JSON schema for the tool's parameters."""

    description: str | None = None
    """The description of the tool."""

    outer_typed_dict_key: str | None = None
    """The key in the outer [TypedDict] that wraps an output tool.

    This will only be set for output tools which don't have an `object` JSON schema.
    """

    strict: bool | None = None
    """Whether to enforce (vendor-specific) strict JSON schema validation for tool calls.

    Setting this to `True` while using a supported model generally imposes some restrictions on the tool's JSON schema
    in exchange for guaranteeing the API responses strictly match that schema.

    When `False`, the model may be free to generate other properties or types (depending on the vendor).
    When `None` (the default), the value will be inferred based on the compatibility of the parameters_json_schema.

    Note: this is currently supported by OpenAI and Anthropic models.
    """

    sequential: bool = False
    """Whether this tool requires a sequential/serial execution environment."""

    kind: ToolKind = field(default='function')
    """The kind of tool:

    - `'function'`: a tool that will be executed by Pydantic AI during an agent run and has its result returned to the model
    - `'output'`: a tool that passes through an output value that ends the run
    - `'external'`: a tool whose result will be produced outside of the Pydantic AI agent run in which it was called, because it depends on an upstream service (or user) or could take longer to generate than it's reasonable to keep the agent process running.
        See the [tools documentation](../deferred-tools.md#deferred-tools) for more info.
    - `'unapproved'`: a tool that requires human-in-the-loop approval.
        See the [tools documentation](../deferred-tools.md#human-in-the-loop-tool-approval) for more info.
    """

    metadata: dict[str, Any] | None = None
    """Tool metadata that can be set by the toolset this tool came from. It is not sent to the model, but can be used for filtering and tool behavior customization.

    For MCP tools, this contains the `meta`, `annotations`, and `output_schema` fields from the tool definition.
    """

    timeout: float | None = None
    """Timeout in seconds for tool execution.

    If the tool takes longer than this, a retry prompt is returned to the model.
    Defaults to None (no timeout).
    """

    @property
    def defer(self) -> bool:
        """Whether calls to this tool will be deferred.

        See the [tools documentation](../deferred-tools.md#deferred-tools) for more info.
        """
        return self.kind in ('external', 'unapproved')

    __repr__ = _utils.dataclasses_no_defaults_repr
```

#### name

```python
name: str
```

The name of the tool.

#### parameters_json_schema

```python
parameters_json_schema: ObjectJsonSchema = field(
    default_factory=lambda: {
        "type": "object",
        "properties": {},
    }
)
```

The JSON schema for the tool's parameters.

#### description

```python
description: str | None = None
```

The description of the tool.

#### outer_typed_dict_key

```python
outer_typed_dict_key: str | None = None
```

The key in the outer [TypedDict] that wraps an output tool.

This will only be set for output tools which don't have an `object` JSON schema.

#### strict

```python
strict: bool | None = None
```

Whether to enforce (vendor-specific) strict JSON schema validation for tool calls.

Setting this to `True` while using a supported model generally imposes some restrictions on the tool's JSON schema in exchange for guaranteeing the API responses strictly match that schema.

When `False`, the model may be free to generate other properties or types (depending on the vendor). When `None` (the default), the value will be inferred based on the compatibility of the parameters_json_schema.

Note: this is currently supported by OpenAI and Anthropic models.

#### sequential

```python
sequential: bool = False
```

Whether this tool requires a sequential/serial execution environment.

#### kind

```python
kind: ToolKind = field(default='function')
```

The kind of tool:

- `'function'`: a tool that will be executed by Pydantic AI during an agent run and has its result returned to the model
- `'output'`: a tool that passes through an output value that ends the run
- `'external'`: a tool whose result will be produced outside of the Pydantic AI agent run in which it was called, because it depends on an upstream service (or user) or could take longer to generate than it's reasonable to keep the agent process running. See the [tools documentation](https://ai.pydantic.dev/deferred-tools/#deferred-tools) for more info.
- `'unapproved'`: a tool that requires human-in-the-loop approval. See the [tools documentation](https://ai.pydantic.dev/deferred-tools/#human-in-the-loop-tool-approval) for more info.

#### metadata

```python
metadata: dict[str, Any] | None = None
```

Tool metadata that can be set by the toolset this tool came from. It is not sent to the model, but can be used for filtering and tool behavior customization.

For MCP tools, this contains the `meta`, `annotations`, and `output_schema` fields from the tool definition.

#### timeout

```python
timeout: float | None = None
```

Timeout in seconds for tool execution.

If the tool takes longer than this, a retry prompt is returned to the model. Defaults to None (no timeout).

#### defer

```python
defer: bool
```

Whether calls to this tool will be deferred.

See the [tools documentation](https://ai.pydantic.dev/deferred-tools/#deferred-tools) for more info.
