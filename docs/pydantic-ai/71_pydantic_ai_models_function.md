# `pydantic_ai.models.function`

A model controlled by a local function.

FunctionModel is similar to [`TestModel`](https://ai.pydantic.dev/api/models/test/index.md), but allows greater control over the model's behavior.

Its primary use case is for more advanced unit testing than is possible with `TestModel`.

Here's a minimal example:

[Learn about Gateway](https://ai.pydantic.dev/gateway) function_model_usage.py

```python
from pydantic_ai import Agent
from pydantic_ai import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import FunctionModel, AgentInfo

my_agent = Agent('gateway/openai:gpt-5.2')


async def model_function(
    messages: list[ModelMessage], info: AgentInfo
) -> ModelResponse:
    print(messages)
    """
    [
        ModelRequest(
            parts=[
                UserPromptPart(
                    content='Testing my agent...',
                    timestamp=datetime.datetime(...),
                )
            ],
            timestamp=datetime.datetime(...),
            run_id='...',
        )
    ]
    """
    print(info)
    """
    AgentInfo(
        function_tools=[],
        allow_text_output=True,
        output_tools=[],
        model_settings=None,
        model_request_parameters=ModelRequestParameters(
            function_tools=[], builtin_tools=[], output_tools=[]
        ),
        instructions=None,
    )
    """
    return ModelResponse(parts=[TextPart('hello world')])


async def test_my_agent():
    """Unit test for my_agent, to be run by pytest."""
    with my_agent.override(model=FunctionModel(model_function)):
        result = await my_agent.run('Testing my agent...')
        assert result.output == 'hello world'
```

function_model_usage.py

```python
from pydantic_ai import Agent
from pydantic_ai import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import FunctionModel, AgentInfo

my_agent = Agent('openai:gpt-5.2')


async def model_function(
    messages: list[ModelMessage], info: AgentInfo
) -> ModelResponse:
    print(messages)
    """
    [
        ModelRequest(
            parts=[
                UserPromptPart(
                    content='Testing my agent...',
                    timestamp=datetime.datetime(...),
                )
            ],
            timestamp=datetime.datetime(...),
            run_id='...',
        )
    ]
    """
    print(info)
    """
    AgentInfo(
        function_tools=[],
        allow_text_output=True,
        output_tools=[],
        model_settings=None,
        model_request_parameters=ModelRequestParameters(
            function_tools=[], builtin_tools=[], output_tools=[]
        ),
        instructions=None,
    )
    """
    return ModelResponse(parts=[TextPart('hello world')])


async def test_my_agent():
    """Unit test for my_agent, to be run by pytest."""
    with my_agent.override(model=FunctionModel(model_function)):
        result = await my_agent.run('Testing my agent...')
        assert result.output == 'hello world'
```

See [Unit testing with `FunctionModel`](https://ai.pydantic.dev/testing/#unit-testing-with-functionmodel) for detailed documentation.

### FunctionModel

Bases: `Model`

A model controlled by a local function.

Apart from `__init__`, all methods are private or match those of the base class.

Source code in `pydantic_ai_slim/pydantic_ai/models/function.py`

```python
@dataclass(init=False)
class FunctionModel(Model):
    """A model controlled by a local function.

    Apart from `__init__`, all methods are private or match those of the base class.
    """

    function: FunctionDef | None
    stream_function: StreamFunctionDef | None

    _model_name: str = field(repr=False)
    _system: str = field(default='function', repr=False)

    @overload
    def __init__(
        self,
        function: FunctionDef,
        *,
        model_name: str | None = None,
        profile: ModelProfileSpec | None = None,
        settings: ModelSettings | None = None,
    ) -> None: ...

    @overload
    def __init__(
        self,
        *,
        stream_function: StreamFunctionDef,
        model_name: str | None = None,
        profile: ModelProfileSpec | None = None,
        settings: ModelSettings | None = None,
    ) -> None: ...

    @overload
    def __init__(
        self,
        function: FunctionDef,
        *,
        stream_function: StreamFunctionDef,
        model_name: str | None = None,
        profile: ModelProfileSpec | None = None,
        settings: ModelSettings | None = None,
    ) -> None: ...

    def __init__(
        self,
        function: FunctionDef | None = None,
        *,
        stream_function: StreamFunctionDef | None = None,
        model_name: str | None = None,
        profile: ModelProfileSpec | None = None,
        settings: ModelSettings | None = None,
    ):
        """Initialize a `FunctionModel`.

        Either `function` or `stream_function` must be provided, providing both is allowed.

        Args:
            function: The function to call for non-streamed requests.
            stream_function: The function to call for streamed requests.
            model_name: The name of the model. If not provided, a name is generated from the function names.
            profile: The model profile to use.
            settings: Model-specific settings that will be used as defaults for this model.
        """
        if function is None and stream_function is None:
            raise TypeError('Either `function` or `stream_function` must be provided')

        self.function = function
        self.stream_function = stream_function

        function_name = self.function.__name__ if self.function is not None else ''
        stream_function_name = self.stream_function.__name__ if self.stream_function is not None else ''
        self._model_name = model_name or f'function:{function_name}:{stream_function_name}'

        # Use a default profile that supports JSON schema and object output if none provided
        if profile is None:
            profile = ModelProfile(
                supports_json_schema_output=True,
                supports_json_object_output=True,
            )
        super().__init__(settings=settings, profile=profile)

    async def request(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> ModelResponse:
        model_settings, model_request_parameters = self.prepare_request(
            model_settings,
            model_request_parameters,
        )
        agent_info = AgentInfo(
            function_tools=model_request_parameters.function_tools,
            allow_text_output=model_request_parameters.allow_text_output,
            output_tools=model_request_parameters.output_tools,
            model_settings=model_settings,
            model_request_parameters=model_request_parameters,
            instructions=self._get_instructions(messages, model_request_parameters),
        )

        assert self.function is not None, 'FunctionModel must receive a `function` to support non-streamed requests'

        if inspect.iscoroutinefunction(self.function):
            response = await self.function(messages, agent_info)
        else:
            response_ = await _utils.run_in_executor(self.function, messages, agent_info)
            assert isinstance(response_, ModelResponse), response_
            response = response_
        response.model_name = self._model_name
        # Add usage data if not already present
        if not response.usage.has_values():  # pragma: no branch
            response.usage = _estimate_usage(chain(messages, [response]))
        return response

    @asynccontextmanager
    async def request_stream(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
        run_context: RunContext[Any] | None = None,
    ) -> AsyncIterator[StreamedResponse]:
        model_settings, model_request_parameters = self.prepare_request(
            model_settings,
            model_request_parameters,
        )
        agent_info = AgentInfo(
            function_tools=model_request_parameters.function_tools,
            allow_text_output=model_request_parameters.allow_text_output,
            output_tools=model_request_parameters.output_tools,
            model_settings=model_settings,
            model_request_parameters=model_request_parameters,
            instructions=self._get_instructions(messages, model_request_parameters),
        )

        assert self.stream_function is not None, (
            'FunctionModel must receive a `stream_function` to support streamed requests'
        )

        response_stream = PeekableAsyncStream(self.stream_function(messages, agent_info))

        first = await response_stream.peek()
        if isinstance(first, _utils.Unset):
            raise ValueError('Stream function must return at least one item')

        yield FunctionStreamedResponse(
            model_request_parameters=model_request_parameters,
            _model_name=self._model_name,
            _iter=response_stream,
        )

    @property
    def model_name(self) -> str:
        """The model name."""
        return self._model_name

    @property
    def system(self) -> str:
        """The system / model provider."""
        return self._system

    @classmethod
    def supported_builtin_tools(cls) -> frozenset[type[AbstractBuiltinTool]]:
        """FunctionModel supports all builtin tools for testing flexibility."""
        from ..builtin_tools import SUPPORTED_BUILTIN_TOOLS

        return SUPPORTED_BUILTIN_TOOLS
```

#### __init__

```python
__init__(
    function: FunctionDef,
    *,
    model_name: str | None = None,
    profile: ModelProfileSpec | None = None,
    settings: ModelSettings | None = None
) -> None
```

```python
__init__(
    *,
    stream_function: StreamFunctionDef,
    model_name: str | None = None,
    profile: ModelProfileSpec | None = None,
    settings: ModelSettings | None = None
) -> None
```

```python
__init__(
    function: FunctionDef,
    *,
    stream_function: StreamFunctionDef,
    model_name: str | None = None,
    profile: ModelProfileSpec | None = None,
    settings: ModelSettings | None = None
) -> None
```

```python
__init__(
    function: FunctionDef | None = None,
    *,
    stream_function: StreamFunctionDef | None = None,
    model_name: str | None = None,
    profile: ModelProfileSpec | None = None,
    settings: ModelSettings | None = None
)
```

Initialize a `FunctionModel`.

Either `function` or `stream_function` must be provided, providing both is allowed.

Parameters:

| Name              | Type                | Description | Default                                                                              |
| ----------------- | ------------------- | ----------- | ------------------------------------------------------------------------------------ |
| `function`        | \`FunctionDef       | None\`      | The function to call for non-streamed requests.                                      |
| `stream_function` | \`StreamFunctionDef | None\`      | The function to call for streamed requests.                                          |
| `model_name`      | \`str               | None\`      | The name of the model. If not provided, a name is generated from the function names. |
| `profile`         | \`ModelProfileSpec  | None\`      | The model profile to use.                                                            |
| `settings`        | \`ModelSettings     | None\`      | Model-specific settings that will be used as defaults for this model.                |

Source code in `pydantic_ai_slim/pydantic_ai/models/function.py`

```python
def __init__(
    self,
    function: FunctionDef | None = None,
    *,
    stream_function: StreamFunctionDef | None = None,
    model_name: str | None = None,
    profile: ModelProfileSpec | None = None,
    settings: ModelSettings | None = None,
):
    """Initialize a `FunctionModel`.

    Either `function` or `stream_function` must be provided, providing both is allowed.

    Args:
        function: The function to call for non-streamed requests.
        stream_function: The function to call for streamed requests.
        model_name: The name of the model. If not provided, a name is generated from the function names.
        profile: The model profile to use.
        settings: Model-specific settings that will be used as defaults for this model.
    """
    if function is None and stream_function is None:
        raise TypeError('Either `function` or `stream_function` must be provided')

    self.function = function
    self.stream_function = stream_function

    function_name = self.function.__name__ if self.function is not None else ''
    stream_function_name = self.stream_function.__name__ if self.stream_function is not None else ''
    self._model_name = model_name or f'function:{function_name}:{stream_function_name}'

    # Use a default profile that supports JSON schema and object output if none provided
    if profile is None:
        profile = ModelProfile(
            supports_json_schema_output=True,
            supports_json_object_output=True,
        )
    super().__init__(settings=settings, profile=profile)
```

#### model_name

```python
model_name: str
```

The model name.

#### system

```python
system: str
```

The system / model provider.

#### supported_builtin_tools

```python
supported_builtin_tools() -> (
    frozenset[type[AbstractBuiltinTool]]
)
```

FunctionModel supports all builtin tools for testing flexibility.

Source code in `pydantic_ai_slim/pydantic_ai/models/function.py`

```python
@classmethod
def supported_builtin_tools(cls) -> frozenset[type[AbstractBuiltinTool]]:
    """FunctionModel supports all builtin tools for testing flexibility."""
    from ..builtin_tools import SUPPORTED_BUILTIN_TOOLS

    return SUPPORTED_BUILTIN_TOOLS
```

### AgentInfo

Information about an agent.

This is passed as the second to functions used within FunctionModel.

Source code in `pydantic_ai_slim/pydantic_ai/models/function.py`

```python
@dataclass(frozen=True, kw_only=True)
class AgentInfo:
    """Information about an agent.

    This is passed as the second to functions used within [`FunctionModel`][pydantic_ai.models.function.FunctionModel].
    """

    function_tools: list[ToolDefinition]
    """The function tools available on this agent.

    These are the tools registered via the [`tool`][pydantic_ai.agent.Agent.tool] and
    [`tool_plain`][pydantic_ai.agent.Agent.tool_plain] decorators.
    """
    allow_text_output: bool
    """Whether a plain text output is allowed."""
    output_tools: list[ToolDefinition]
    """The tools that can called to produce the final output of the run."""
    model_settings: ModelSettings | None
    """The model settings passed to the run call."""
    model_request_parameters: ModelRequestParameters
    """The model request parameters passed to the run call."""
    instructions: str | None
    """The instructions passed to model."""
```

#### function_tools

```python
function_tools: list[ToolDefinition]
```

The function tools available on this agent.

These are the tools registered via the tool and tool_plain decorators.

#### allow_text_output

```python
allow_text_output: bool
```

Whether a plain text output is allowed.

#### output_tools

```python
output_tools: list[ToolDefinition]
```

The tools that can called to produce the final output of the run.

#### model_settings

```python
model_settings: ModelSettings | None
```

The model settings passed to the run call.

#### model_request_parameters

```python
model_request_parameters: ModelRequestParameters
```

The model request parameters passed to the run call.

#### instructions

```python
instructions: str | None
```

The instructions passed to model.

### DeltaToolCall

Incremental change to a tool call.

Used to describe a chunk when streaming structured responses.

Source code in `pydantic_ai_slim/pydantic_ai/models/function.py`

```python
@dataclass
class DeltaToolCall:
    """Incremental change to a tool call.

    Used to describe a chunk when streaming structured responses.
    """

    name: str | None = None
    """Incremental change to the name of the tool."""

    json_args: str | None = None
    """Incremental change to the arguments as JSON"""

    _: KW_ONLY

    tool_call_id: str | None = None
    """Incremental change to the tool call ID."""
```

#### name

```python
name: str | None = None
```

Incremental change to the name of the tool.

#### json_args

```python
json_args: str | None = None
```

Incremental change to the arguments as JSON

#### tool_call_id

```python
tool_call_id: str | None = None
```

Incremental change to the tool call ID.

### DeltaThinkingPart

Incremental change to a thinking part.

Used to describe a chunk when streaming thinking responses.

Source code in `pydantic_ai_slim/pydantic_ai/models/function.py`

```python
@dataclass(kw_only=True)
class DeltaThinkingPart:
    """Incremental change to a thinking part.

    Used to describe a chunk when streaming thinking responses.
    """

    content: str | None = None
    """Incremental change to the thinking content."""
    signature: str | None = None
    """Incremental change to the thinking signature."""
```

#### content

```python
content: str | None = None
```

Incremental change to the thinking content.

#### signature

```python
signature: str | None = None
```

Incremental change to the thinking signature.

### DeltaToolCalls

```python
DeltaToolCalls: TypeAlias = dict[int, DeltaToolCall]
```

A mapping of tool call IDs to incremental changes.

### DeltaThinkingCalls

```python
DeltaThinkingCalls: TypeAlias = dict[int, DeltaThinkingPart]
```

A mapping of thinking call IDs to incremental changes.

### FunctionDef

```python
FunctionDef: TypeAlias = Callable[
    [list[ModelMessage], AgentInfo],
    ModelResponse | Awaitable[ModelResponse],
]
```

A function used to generate a non-streamed response.

### StreamFunctionDef

```python
StreamFunctionDef: TypeAlias = Callable[
    [list[ModelMessage], AgentInfo],
    AsyncIterator[
        str
        | DeltaToolCalls
        | DeltaThinkingCalls
        | BuiltinToolCallsReturns
    ],
]
```

A function used to generate a streamed response.

While this is defined as having return type of `AsyncIterator[str | DeltaToolCalls | DeltaThinkingCalls | BuiltinTools]`, it should really be considered as `AsyncIterator[str] | AsyncIterator[DeltaToolCalls] | AsyncIterator[DeltaThinkingCalls]`,

E.g. you need to yield all text, all `DeltaToolCalls`, all `DeltaThinkingCalls`, or all `BuiltinToolCallsReturns`, not mix them.

### FunctionStreamedResponse

Bases: `StreamedResponse`

Implementation of `StreamedResponse` for FunctionModel.

Source code in `pydantic_ai_slim/pydantic_ai/models/function.py`

```python
@dataclass
class FunctionStreamedResponse(StreamedResponse):
    """Implementation of `StreamedResponse` for [FunctionModel][pydantic_ai.models.function.FunctionModel]."""

    _model_name: str
    _iter: AsyncIterator[str | DeltaToolCalls | DeltaThinkingCalls | BuiltinToolCallsReturns]
    _timestamp: datetime = field(default_factory=_utils.now_utc)

    def __post_init__(self):
        self._usage += _estimate_usage([])

    async def _get_event_iterator(self) -> AsyncIterator[ModelResponseStreamEvent]:  # noqa: C901
        async for item in self._iter:
            if isinstance(item, str):
                response_tokens = _estimate_string_tokens(item)
                self._usage += usage.RequestUsage(output_tokens=response_tokens)
                for event in self._parts_manager.handle_text_delta(vendor_part_id='content', content=item):
                    yield event
            elif isinstance(item, dict) and item:
                for dtc_index, delta in item.items():
                    if isinstance(delta, DeltaThinkingPart):
                        if delta.content:  # pragma: no branch
                            response_tokens = _estimate_string_tokens(delta.content)
                            self._usage += usage.RequestUsage(output_tokens=response_tokens)
                        for event in self._parts_manager.handle_thinking_delta(
                            vendor_part_id=dtc_index,
                            content=delta.content,
                            signature=delta.signature,
                            provider_name='function' if delta.signature else None,
                        ):
                            yield event
                    elif isinstance(delta, DeltaToolCall):
                        if delta.json_args:
                            response_tokens = _estimate_string_tokens(delta.json_args)
                            self._usage += usage.RequestUsage(output_tokens=response_tokens)
                        maybe_event = self._parts_manager.handle_tool_call_delta(
                            vendor_part_id=dtc_index,
                            tool_name=delta.name,
                            args=delta.json_args,
                            tool_call_id=delta.tool_call_id,
                        )
                        if maybe_event is not None:  # pragma: no branch
                            yield maybe_event
                    elif isinstance(delta, BuiltinToolCallPart):
                        if content := delta.args_as_json_str():  # pragma: no branch
                            response_tokens = _estimate_string_tokens(content)
                            self._usage += usage.RequestUsage(output_tokens=response_tokens)
                        yield self._parts_manager.handle_part(vendor_part_id=dtc_index, part=delta)
                    elif isinstance(delta, BuiltinToolReturnPart):
                        if content := delta.model_response_str():  # pragma: no branch
                            response_tokens = _estimate_string_tokens(content)
                            self._usage += usage.RequestUsage(output_tokens=response_tokens)
                        yield self._parts_manager.handle_part(vendor_part_id=dtc_index, part=delta)
                    else:
                        assert_never(delta)

    @property
    def model_name(self) -> str:
        """Get the model name of the response."""
        return self._model_name

    @property
    def provider_name(self) -> None:
        """Get the provider name."""
        return None

    @property
    def provider_url(self) -> None:
        """Get the provider base URL."""
        return None

    @property
    def timestamp(self) -> datetime:
        """Get the timestamp of the response."""
        return self._timestamp
```

#### model_name

```python
model_name: str
```

Get the model name of the response.

#### provider_name

```python
provider_name: None
```

Get the provider name.

#### provider_url

```python
provider_url: None
```

Get the provider base URL.

#### timestamp

```python
timestamp: datetime
```

Get the timestamp of the response.
