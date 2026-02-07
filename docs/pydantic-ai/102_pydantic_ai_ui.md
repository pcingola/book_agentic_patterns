# `pydantic_ai.ui`

### StateDeps

Bases: `Generic[StateT]`

Dependency type that holds state.

This class is used to manage the state of an agent run. It allows setting the state of the agent run with a specific type of state model, which must be a subclass of `BaseModel`.

The state is set using the `state` setter by the `Adapter` when the run starts.

Implements the `StateHandler` protocol.

Source code in `pydantic_ai_slim/pydantic_ai/ui/_adapter.py`

```python
@dataclass
class StateDeps(Generic[StateT]):
    """Dependency type that holds state.

    This class is used to manage the state of an agent run. It allows setting
    the state of the agent run with a specific type of state model, which must
    be a subclass of `BaseModel`.

    The state is set using the `state` setter by the `Adapter` when the run starts.

    Implements the `StateHandler` protocol.
    """

    state: StateT
```

### StateHandler

Bases: `Protocol`

Protocol for state handlers in agent runs. Requires the class to be a dataclass with a `state` field.

Source code in `pydantic_ai_slim/pydantic_ai/ui/_adapter.py`

```python
@runtime_checkable
class StateHandler(Protocol):
    """Protocol for state handlers in agent runs. Requires the class to be a dataclass with a `state` field."""

    # Has to be a dataclass so we can use `replace` to update the state.
    # From https://github.com/python/typeshed/blob/9ab7fde0a0cd24ed7a72837fcb21093b811b80d8/stdlib/_typeshed/__init__.pyi#L352
    __dataclass_fields__: ClassVar[dict[str, Field[Any]]]

    @property
    def state(self) -> Any:
        """Get the current state of the agent run."""
        ...

    @state.setter
    def state(self, state: Any) -> None:
        """Set the state of the agent run.

        This method is called to update the state of the agent run with the
        provided state.

        Args:
            state: The run state.
        """
        ...
```

#### state

```python
state: Any
```

Get the current state of the agent run.

### UIAdapter

Bases: `ABC`, `Generic[RunInputT, MessageT, EventT, AgentDepsT, OutputDataT]`

Base class for UI adapters.

This class is responsible for transforming agent run input received from the frontend into arguments for Agent.run_stream_events(), running the agent, and then transforming Pydantic AI events into protocol-specific events.

The event stream transformation is handled by a protocol-specific UIEventStream subclass.

Source code in `pydantic_ai_slim/pydantic_ai/ui/_adapter.py`

```python
@dataclass
class UIAdapter(ABC, Generic[RunInputT, MessageT, EventT, AgentDepsT, OutputDataT]):
    """Base class for UI adapters.

    This class is responsible for transforming agent run input received from the frontend into arguments for [`Agent.run_stream_events()`][pydantic_ai.agent.Agent.run_stream_events], running the agent, and then transforming Pydantic AI events into protocol-specific events.

    The event stream transformation is handled by a protocol-specific [`UIEventStream`][pydantic_ai.ui.UIEventStream] subclass.
    """

    agent: AbstractAgent[AgentDepsT, OutputDataT]
    """The Pydantic AI agent to run."""

    run_input: RunInputT
    """The protocol-specific run input object."""

    _: KW_ONLY

    accept: str | None = None
    """The `Accept` header value of the request, used to determine how to encode the protocol-specific events for the streaming response."""

    @classmethod
    async def from_request(
        cls, request: Request, *, agent: AbstractAgent[AgentDepsT, OutputDataT]
    ) -> UIAdapter[RunInputT, MessageT, EventT, AgentDepsT, OutputDataT]:
        """Create an adapter from a request."""
        return cls(
            agent=agent,
            run_input=cls.build_run_input(await request.body()),
            accept=request.headers.get('accept'),
        )

    @classmethod
    @abstractmethod
    def build_run_input(cls, body: bytes) -> RunInputT:
        """Build a protocol-specific run input object from the request body."""
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def load_messages(cls, messages: Sequence[MessageT]) -> list[ModelMessage]:
        """Transform protocol-specific messages into Pydantic AI messages."""
        raise NotImplementedError

    @classmethod
    def dump_messages(cls, messages: Sequence[ModelMessage]) -> list[MessageT]:
        """Transform Pydantic AI messages into protocol-specific messages."""
        raise NotImplementedError

    @abstractmethod
    def build_event_stream(self) -> UIEventStream[RunInputT, EventT, AgentDepsT, OutputDataT]:
        """Build a protocol-specific event stream transformer."""
        raise NotImplementedError

    @cached_property
    @abstractmethod
    def messages(self) -> list[ModelMessage]:
        """Pydantic AI messages from the protocol-specific run input."""
        raise NotImplementedError

    @cached_property
    def toolset(self) -> AbstractToolset[AgentDepsT] | None:
        """Toolset representing frontend tools from the protocol-specific run input."""
        return None

    @cached_property
    def state(self) -> dict[str, Any] | None:
        """Frontend state from the protocol-specific run input."""
        return None

    def transform_stream(
        self,
        stream: AsyncIterator[NativeEvent],
        on_complete: OnCompleteFunc[EventT] | None = None,
    ) -> AsyncIterator[EventT]:
        """Transform a stream of Pydantic AI events into protocol-specific events.

        Args:
            stream: The stream of Pydantic AI events to transform.
            on_complete: Optional callback function called when the agent run completes successfully.
                The callback receives the completed [`AgentRunResult`][pydantic_ai.agent.AgentRunResult] and can optionally yield additional protocol-specific events.
        """
        return self.build_event_stream().transform_stream(stream, on_complete=on_complete)

    def encode_stream(self, stream: AsyncIterator[EventT]) -> AsyncIterator[str]:
        """Encode a stream of protocol-specific events as strings according to the `Accept` header value.

        Args:
            stream: The stream of protocol-specific events to encode.
        """
        return self.build_event_stream().encode_stream(stream)

    def streaming_response(self, stream: AsyncIterator[EventT]) -> StreamingResponse:
        """Generate a streaming response from a stream of protocol-specific events.

        Args:
            stream: The stream of protocol-specific events to encode.
        """
        return self.build_event_stream().streaming_response(stream)

    def run_stream_native(
        self,
        *,
        output_type: OutputSpec[Any] | None = None,
        message_history: Sequence[ModelMessage] | None = None,
        deferred_tool_results: DeferredToolResults | None = None,
        model: Model | KnownModelName | str | None = None,
        instructions: Instructions[AgentDepsT] = None,
        deps: AgentDepsT = None,
        model_settings: ModelSettings | None = None,
        usage_limits: UsageLimits | None = None,
        usage: RunUsage | None = None,
        metadata: AgentMetadata[AgentDepsT] | None = None,
        infer_name: bool = True,
        toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
        builtin_tools: Sequence[AbstractBuiltinTool] | None = None,
    ) -> AsyncIterator[NativeEvent]:
        """Run the agent with the protocol-specific run input and stream Pydantic AI events.

        Args:
            output_type: Custom output type to use for this run, `output_type` may only be used if the agent has no
                output validators since output validators would expect an argument that matches the agent's output type.
            message_history: History of the conversation so far.
            deferred_tool_results: Optional results for deferred tool calls in the message history.
            model: Optional model to use for this run, required if `model` was not set when creating the agent.
            instructions: Optional additional instructions to use for this run.
            deps: Optional dependencies to use for this run.
            model_settings: Optional settings to use for this model's request.
            usage_limits: Optional limits on model request count or token usage.
            usage: Optional usage to start with, useful for resuming a conversation or agents used in tools.
            metadata: Optional metadata to attach to this run. Accepts a dictionary or a callable taking
                [`RunContext`][pydantic_ai.tools.RunContext]; merged with the agent's configured metadata.
            infer_name: Whether to try to infer the agent name from the call frame if it's not set.
            toolsets: Optional additional toolsets for this run.
            builtin_tools: Optional additional builtin tools to use for this run.
        """
        message_history = [*(message_history or []), *self.messages]

        toolset = self.toolset
        if toolset:
            output_type = [output_type or self.agent.output_type, DeferredToolRequests]
            toolsets = [*(toolsets or []), toolset]

        if isinstance(deps, StateHandler):
            raw_state = self.state or {}
            if isinstance(deps.state, BaseModel):
                state = type(deps.state).model_validate(raw_state)
            else:
                state = raw_state

            deps.state = state
        elif self.state:
            warnings.warn(
                f'State was provided but `deps` of type `{type(deps).__name__}` does not implement the `StateHandler` protocol, so the state was ignored. Use `StateDeps[...]` or implement `StateHandler` to receive AG-UI state.',
                UserWarning,
                stacklevel=2,
            )

        return self.agent.run_stream_events(
            output_type=output_type,
            message_history=message_history,
            deferred_tool_results=deferred_tool_results,
            model=model,
            deps=deps,
            model_settings=model_settings,
            instructions=instructions,
            usage_limits=usage_limits,
            usage=usage,
            metadata=metadata,
            infer_name=infer_name,
            toolsets=toolsets,
            builtin_tools=builtin_tools,
        )

    def run_stream(
        self,
        *,
        output_type: OutputSpec[Any] | None = None,
        message_history: Sequence[ModelMessage] | None = None,
        deferred_tool_results: DeferredToolResults | None = None,
        model: Model | KnownModelName | str | None = None,
        instructions: Instructions[AgentDepsT] = None,
        deps: AgentDepsT = None,
        model_settings: ModelSettings | None = None,
        usage_limits: UsageLimits | None = None,
        usage: RunUsage | None = None,
        metadata: AgentMetadata[AgentDepsT] | None = None,
        infer_name: bool = True,
        toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
        builtin_tools: Sequence[AbstractBuiltinTool] | None = None,
        on_complete: OnCompleteFunc[EventT] | None = None,
    ) -> AsyncIterator[EventT]:
        """Run the agent with the protocol-specific run input and stream protocol-specific events.

        Args:
            output_type: Custom output type to use for this run, `output_type` may only be used if the agent has no
                output validators since output validators would expect an argument that matches the agent's output type.
            message_history: History of the conversation so far.
            deferred_tool_results: Optional results for deferred tool calls in the message history.
            model: Optional model to use for this run, required if `model` was not set when creating the agent.
            instructions: Optional additional instructions to use for this run.
            deps: Optional dependencies to use for this run.
            model_settings: Optional settings to use for this model's request.
            usage_limits: Optional limits on model request count or token usage.
            usage: Optional usage to start with, useful for resuming a conversation or agents used in tools.
            metadata: Optional metadata to attach to this run. Accepts a dictionary or a callable taking
                [`RunContext`][pydantic_ai.tools.RunContext]; merged with the agent's configured metadata.
            infer_name: Whether to try to infer the agent name from the call frame if it's not set.
            toolsets: Optional additional toolsets for this run.
            builtin_tools: Optional additional builtin tools to use for this run.
            on_complete: Optional callback function called when the agent run completes successfully.
                The callback receives the completed [`AgentRunResult`][pydantic_ai.agent.AgentRunResult] and can optionally yield additional protocol-specific events.
        """
        return self.transform_stream(
            self.run_stream_native(
                output_type=output_type,
                message_history=message_history,
                deferred_tool_results=deferred_tool_results,
                model=model,
                instructions=instructions,
                deps=deps,
                model_settings=model_settings,
                usage_limits=usage_limits,
                usage=usage,
                metadata=metadata,
                infer_name=infer_name,
                toolsets=toolsets,
                builtin_tools=builtin_tools,
            ),
            on_complete=on_complete,
        )

    @classmethod
    async def dispatch_request(
        cls,
        request: Request,
        *,
        agent: AbstractAgent[DispatchDepsT, DispatchOutputDataT],
        message_history: Sequence[ModelMessage] | None = None,
        deferred_tool_results: DeferredToolResults | None = None,
        model: Model | KnownModelName | str | None = None,
        instructions: Instructions[DispatchDepsT] = None,
        deps: DispatchDepsT = None,
        output_type: OutputSpec[Any] | None = None,
        model_settings: ModelSettings | None = None,
        usage_limits: UsageLimits | None = None,
        usage: RunUsage | None = None,
        metadata: AgentMetadata[DispatchDepsT] | None = None,
        infer_name: bool = True,
        toolsets: Sequence[AbstractToolset[DispatchDepsT]] | None = None,
        builtin_tools: Sequence[AbstractBuiltinTool] | None = None,
        on_complete: OnCompleteFunc[EventT] | None = None,
    ) -> Response:
        """Handle a protocol-specific HTTP request by running the agent and returning a streaming response of protocol-specific events.

        Args:
            request: The incoming Starlette/FastAPI request.
            agent: The agent to run.
            output_type: Custom output type to use for this run, `output_type` may only be used if the agent has no
                output validators since output validators would expect an argument that matches the agent's output type.
            message_history: History of the conversation so far.
            deferred_tool_results: Optional results for deferred tool calls in the message history.
            model: Optional model to use for this run, required if `model` was not set when creating the agent.
            instructions: Optional additional instructions to use for this run.
            deps: Optional dependencies to use for this run.
            model_settings: Optional settings to use for this model's request.
            usage_limits: Optional limits on model request count or token usage.
            usage: Optional usage to start with, useful for resuming a conversation or agents used in tools.
            metadata: Optional metadata to attach to this run. Accepts a dictionary or a callable taking
                [`RunContext`][pydantic_ai.tools.RunContext]; merged with the agent's configured metadata.
            infer_name: Whether to try to infer the agent name from the call frame if it's not set.
            toolsets: Optional additional toolsets for this run.
            builtin_tools: Optional additional builtin tools to use for this run.
            on_complete: Optional callback function called when the agent run completes successfully.
                The callback receives the completed [`AgentRunResult`][pydantic_ai.agent.AgentRunResult] and can optionally yield additional protocol-specific events.

        Returns:
            A streaming Starlette response with protocol-specific events encoded per the request's `Accept` header value.
        """
        try:
            from starlette.responses import Response
        except ImportError as e:  # pragma: no cover
            raise ImportError(
                'Please install the `starlette` package to use `dispatch_request()` method, '
                'you can use the `ui` optional group â€” `pip install "pydantic-ai-slim[ui]"`'
            ) from e

        try:
            # The DepsT and OutputDataT come from `agent`, not from `cls`; the cast is necessary to explain this to pyright
            adapter = cast(
                UIAdapter[RunInputT, MessageT, EventT, DispatchDepsT, DispatchOutputDataT],
                await cls.from_request(request, agent=cast(AbstractAgent[AgentDepsT, OutputDataT], agent)),
            )
        except ValidationError as e:  # pragma: no cover
            return Response(
                content=e.json(),
                media_type='application/json',
                status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            )

        return adapter.streaming_response(
            adapter.run_stream(
                message_history=message_history,
                deferred_tool_results=deferred_tool_results,
                deps=deps,
                output_type=output_type,
                model=model,
                instructions=instructions,
                model_settings=model_settings,
                usage_limits=usage_limits,
                usage=usage,
                metadata=metadata,
                infer_name=infer_name,
                toolsets=toolsets,
                builtin_tools=builtin_tools,
                on_complete=on_complete,
            ),
        )
```

#### agent

```python
agent: AbstractAgent[AgentDepsT, OutputDataT]
```

The Pydantic AI agent to run.

#### run_input

```python
run_input: RunInputT
```

The protocol-specific run input object.

#### accept

```python
accept: str | None = None
```

The `Accept` header value of the request, used to determine how to encode the protocol-specific events for the streaming response.

#### from_request

```python
from_request(
    request: Request,
    *,
    agent: AbstractAgent[AgentDepsT, OutputDataT]
) -> UIAdapter[
    RunInputT, MessageT, EventT, AgentDepsT, OutputDataT
]
```

Create an adapter from a request.

Source code in `pydantic_ai_slim/pydantic_ai/ui/_adapter.py`

```python
@classmethod
async def from_request(
    cls, request: Request, *, agent: AbstractAgent[AgentDepsT, OutputDataT]
) -> UIAdapter[RunInputT, MessageT, EventT, AgentDepsT, OutputDataT]:
    """Create an adapter from a request."""
    return cls(
        agent=agent,
        run_input=cls.build_run_input(await request.body()),
        accept=request.headers.get('accept'),
    )
```

#### build_run_input

```python
build_run_input(body: bytes) -> RunInputT
```

Build a protocol-specific run input object from the request body.

Source code in `pydantic_ai_slim/pydantic_ai/ui/_adapter.py`

```python
@classmethod
@abstractmethod
def build_run_input(cls, body: bytes) -> RunInputT:
    """Build a protocol-specific run input object from the request body."""
    raise NotImplementedError
```

#### load_messages

```python
load_messages(
    messages: Sequence[MessageT],
) -> list[ModelMessage]
```

Transform protocol-specific messages into Pydantic AI messages.

Source code in `pydantic_ai_slim/pydantic_ai/ui/_adapter.py`

```python
@classmethod
@abstractmethod
def load_messages(cls, messages: Sequence[MessageT]) -> list[ModelMessage]:
    """Transform protocol-specific messages into Pydantic AI messages."""
    raise NotImplementedError
```

#### dump_messages

```python
dump_messages(
    messages: Sequence[ModelMessage],
) -> list[MessageT]
```

Transform Pydantic AI messages into protocol-specific messages.

Source code in `pydantic_ai_slim/pydantic_ai/ui/_adapter.py`

```python
@classmethod
def dump_messages(cls, messages: Sequence[ModelMessage]) -> list[MessageT]:
    """Transform Pydantic AI messages into protocol-specific messages."""
    raise NotImplementedError
```

#### build_event_stream

```python
build_event_stream() -> (
    UIEventStream[
        RunInputT, EventT, AgentDepsT, OutputDataT
    ]
)
```

Build a protocol-specific event stream transformer.

Source code in `pydantic_ai_slim/pydantic_ai/ui/_adapter.py`

```python
@abstractmethod
def build_event_stream(self) -> UIEventStream[RunInputT, EventT, AgentDepsT, OutputDataT]:
    """Build a protocol-specific event stream transformer."""
    raise NotImplementedError
```

#### messages

```python
messages: list[ModelMessage]
```

Pydantic AI messages from the protocol-specific run input.

#### toolset

```python
toolset: AbstractToolset[AgentDepsT] | None
```

Toolset representing frontend tools from the protocol-specific run input.

#### state

```python
state: dict[str, Any] | None
```

Frontend state from the protocol-specific run input.

#### transform_stream

```python
transform_stream(
    stream: AsyncIterator[NativeEvent],
    on_complete: OnCompleteFunc[EventT] | None = None,
) -> AsyncIterator[EventT]
```

Transform a stream of Pydantic AI events into protocol-specific events.

Parameters:

| Name          | Type                         | Description                                    | Default                                                                                                                                                                                       |
| ------------- | ---------------------------- | ---------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `stream`      | `AsyncIterator[NativeEvent]` | The stream of Pydantic AI events to transform. | *required*                                                                                                                                                                                    |
| `on_complete` | \`OnCompleteFunc[EventT]     | None\`                                         | Optional callback function called when the agent run completes successfully. The callback receives the completed AgentRunResult and can optionally yield additional protocol-specific events. |

Source code in `pydantic_ai_slim/pydantic_ai/ui/_adapter.py`

```python
def transform_stream(
    self,
    stream: AsyncIterator[NativeEvent],
    on_complete: OnCompleteFunc[EventT] | None = None,
) -> AsyncIterator[EventT]:
    """Transform a stream of Pydantic AI events into protocol-specific events.

    Args:
        stream: The stream of Pydantic AI events to transform.
        on_complete: Optional callback function called when the agent run completes successfully.
            The callback receives the completed [`AgentRunResult`][pydantic_ai.agent.AgentRunResult] and can optionally yield additional protocol-specific events.
    """
    return self.build_event_stream().transform_stream(stream, on_complete=on_complete)
```

#### encode_stream

```python
encode_stream(
    stream: AsyncIterator[EventT],
) -> AsyncIterator[str]
```

Encode a stream of protocol-specific events as strings according to the `Accept` header value.

Parameters:

| Name     | Type                    | Description                                       | Default    |
| -------- | ----------------------- | ------------------------------------------------- | ---------- |
| `stream` | `AsyncIterator[EventT]` | The stream of protocol-specific events to encode. | *required* |

Source code in `pydantic_ai_slim/pydantic_ai/ui/_adapter.py`

```python
def encode_stream(self, stream: AsyncIterator[EventT]) -> AsyncIterator[str]:
    """Encode a stream of protocol-specific events as strings according to the `Accept` header value.

    Args:
        stream: The stream of protocol-specific events to encode.
    """
    return self.build_event_stream().encode_stream(stream)
```

#### streaming_response

```python
streaming_response(
    stream: AsyncIterator[EventT],
) -> StreamingResponse
```

Generate a streaming response from a stream of protocol-specific events.

Parameters:

| Name     | Type                    | Description                                       | Default    |
| -------- | ----------------------- | ------------------------------------------------- | ---------- |
| `stream` | `AsyncIterator[EventT]` | The stream of protocol-specific events to encode. | *required* |

Source code in `pydantic_ai_slim/pydantic_ai/ui/_adapter.py`

```python
def streaming_response(self, stream: AsyncIterator[EventT]) -> StreamingResponse:
    """Generate a streaming response from a stream of protocol-specific events.

    Args:
        stream: The stream of protocol-specific events to encode.
    """
    return self.build_event_stream().streaming_response(stream)
```

#### run_stream_native

```python
run_stream_native(
    *,
    output_type: OutputSpec[Any] | None = None,
    message_history: Sequence[ModelMessage] | None = None,
    deferred_tool_results: (
        DeferredToolResults | None
    ) = None,
    model: Model | KnownModelName | str | None = None,
    instructions: Instructions[AgentDepsT] = None,
    deps: AgentDepsT = None,
    model_settings: ModelSettings | None = None,
    usage_limits: UsageLimits | None = None,
    usage: RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    infer_name: bool = True,
    toolsets: (
        Sequence[AbstractToolset[AgentDepsT]] | None
    ) = None,
    builtin_tools: (
        Sequence[AbstractBuiltinTool] | None
    ) = None
) -> AsyncIterator[NativeEvent]
```

Run the agent with the protocol-specific run input and stream Pydantic AI events.

Parameters:

| Name                    | Type                                      | Description                                                                 | Default                                                                                                                                                                                           |
| ----------------------- | ----------------------------------------- | --------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `output_type`           | \`OutputSpec[Any]                         | None\`                                                                      | Custom output type to use for this run, output_type may only be used if the agent has no output validators since output validators would expect an argument that matches the agent's output type. |
| `message_history`       | \`Sequence[ModelMessage]                  | None\`                                                                      | History of the conversation so far.                                                                                                                                                               |
| `deferred_tool_results` | \`DeferredToolResults                     | None\`                                                                      | Optional results for deferred tool calls in the message history.                                                                                                                                  |
| `model`                 | \`Model                                   | KnownModelName                                                              | str                                                                                                                                                                                               |
| `instructions`          | `Instructions[AgentDepsT]`                | Optional additional instructions to use for this run.                       | `None`                                                                                                                                                                                            |
| `deps`                  | `AgentDepsT`                              | Optional dependencies to use for this run.                                  | `None`                                                                                                                                                                                            |
| `model_settings`        | \`ModelSettings                           | None\`                                                                      | Optional settings to use for this model's request.                                                                                                                                                |
| `usage_limits`          | \`UsageLimits                             | None\`                                                                      | Optional limits on model request count or token usage.                                                                                                                                            |
| `usage`                 | \`RunUsage                                | None\`                                                                      | Optional usage to start with, useful for resuming a conversation or agents used in tools.                                                                                                         |
| `metadata`              | \`AgentMetadata[AgentDepsT]               | None\`                                                                      | Optional metadata to attach to this run. Accepts a dictionary or a callable taking RunContext; merged with the agent's configured metadata.                                                       |
| `infer_name`            | `bool`                                    | Whether to try to infer the agent name from the call frame if it's not set. | `True`                                                                                                                                                                                            |
| `toolsets`              | \`Sequence\[AbstractToolset[AgentDepsT]\] | None\`                                                                      | Optional additional toolsets for this run.                                                                                                                                                        |
| `builtin_tools`         | \`Sequence[AbstractBuiltinTool]           | None\`                                                                      | Optional additional builtin tools to use for this run.                                                                                                                                            |

Source code in `pydantic_ai_slim/pydantic_ai/ui/_adapter.py`

```python
def run_stream_native(
    self,
    *,
    output_type: OutputSpec[Any] | None = None,
    message_history: Sequence[ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    model: Model | KnownModelName | str | None = None,
    instructions: Instructions[AgentDepsT] = None,
    deps: AgentDepsT = None,
    model_settings: ModelSettings | None = None,
    usage_limits: UsageLimits | None = None,
    usage: RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    builtin_tools: Sequence[AbstractBuiltinTool] | None = None,
) -> AsyncIterator[NativeEvent]:
    """Run the agent with the protocol-specific run input and stream Pydantic AI events.

    Args:
        output_type: Custom output type to use for this run, `output_type` may only be used if the agent has no
            output validators since output validators would expect an argument that matches the agent's output type.
        message_history: History of the conversation so far.
        deferred_tool_results: Optional results for deferred tool calls in the message history.
        model: Optional model to use for this run, required if `model` was not set when creating the agent.
        instructions: Optional additional instructions to use for this run.
        deps: Optional dependencies to use for this run.
        model_settings: Optional settings to use for this model's request.
        usage_limits: Optional limits on model request count or token usage.
        usage: Optional usage to start with, useful for resuming a conversation or agents used in tools.
        metadata: Optional metadata to attach to this run. Accepts a dictionary or a callable taking
            [`RunContext`][pydantic_ai.tools.RunContext]; merged with the agent's configured metadata.
        infer_name: Whether to try to infer the agent name from the call frame if it's not set.
        toolsets: Optional additional toolsets for this run.
        builtin_tools: Optional additional builtin tools to use for this run.
    """
    message_history = [*(message_history or []), *self.messages]

    toolset = self.toolset
    if toolset:
        output_type = [output_type or self.agent.output_type, DeferredToolRequests]
        toolsets = [*(toolsets or []), toolset]

    if isinstance(deps, StateHandler):
        raw_state = self.state or {}
        if isinstance(deps.state, BaseModel):
            state = type(deps.state).model_validate(raw_state)
        else:
            state = raw_state

        deps.state = state
    elif self.state:
        warnings.warn(
            f'State was provided but `deps` of type `{type(deps).__name__}` does not implement the `StateHandler` protocol, so the state was ignored. Use `StateDeps[...]` or implement `StateHandler` to receive AG-UI state.',
            UserWarning,
            stacklevel=2,
        )

    return self.agent.run_stream_events(
        output_type=output_type,
        message_history=message_history,
        deferred_tool_results=deferred_tool_results,
        model=model,
        deps=deps,
        model_settings=model_settings,
        instructions=instructions,
        usage_limits=usage_limits,
        usage=usage,
        metadata=metadata,
        infer_name=infer_name,
        toolsets=toolsets,
        builtin_tools=builtin_tools,
    )
```

#### run_stream

```python
run_stream(
    *,
    output_type: OutputSpec[Any] | None = None,
    message_history: Sequence[ModelMessage] | None = None,
    deferred_tool_results: (
        DeferredToolResults | None
    ) = None,
    model: Model | KnownModelName | str | None = None,
    instructions: Instructions[AgentDepsT] = None,
    deps: AgentDepsT = None,
    model_settings: ModelSettings | None = None,
    usage_limits: UsageLimits | None = None,
    usage: RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    infer_name: bool = True,
    toolsets: (
        Sequence[AbstractToolset[AgentDepsT]] | None
    ) = None,
    builtin_tools: (
        Sequence[AbstractBuiltinTool] | None
    ) = None,
    on_complete: OnCompleteFunc[EventT] | None = None
) -> AsyncIterator[EventT]
```

Run the agent with the protocol-specific run input and stream protocol-specific events.

Parameters:

| Name                    | Type                                      | Description                                                                 | Default                                                                                                                                                                                           |
| ----------------------- | ----------------------------------------- | --------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `output_type`           | \`OutputSpec[Any]                         | None\`                                                                      | Custom output type to use for this run, output_type may only be used if the agent has no output validators since output validators would expect an argument that matches the agent's output type. |
| `message_history`       | \`Sequence[ModelMessage]                  | None\`                                                                      | History of the conversation so far.                                                                                                                                                               |
| `deferred_tool_results` | \`DeferredToolResults                     | None\`                                                                      | Optional results for deferred tool calls in the message history.                                                                                                                                  |
| `model`                 | \`Model                                   | KnownModelName                                                              | str                                                                                                                                                                                               |
| `instructions`          | `Instructions[AgentDepsT]`                | Optional additional instructions to use for this run.                       | `None`                                                                                                                                                                                            |
| `deps`                  | `AgentDepsT`                              | Optional dependencies to use for this run.                                  | `None`                                                                                                                                                                                            |
| `model_settings`        | \`ModelSettings                           | None\`                                                                      | Optional settings to use for this model's request.                                                                                                                                                |
| `usage_limits`          | \`UsageLimits                             | None\`                                                                      | Optional limits on model request count or token usage.                                                                                                                                            |
| `usage`                 | \`RunUsage                                | None\`                                                                      | Optional usage to start with, useful for resuming a conversation or agents used in tools.                                                                                                         |
| `metadata`              | \`AgentMetadata[AgentDepsT]               | None\`                                                                      | Optional metadata to attach to this run. Accepts a dictionary or a callable taking RunContext; merged with the agent's configured metadata.                                                       |
| `infer_name`            | `bool`                                    | Whether to try to infer the agent name from the call frame if it's not set. | `True`                                                                                                                                                                                            |
| `toolsets`              | \`Sequence\[AbstractToolset[AgentDepsT]\] | None\`                                                                      | Optional additional toolsets for this run.                                                                                                                                                        |
| `builtin_tools`         | \`Sequence[AbstractBuiltinTool]           | None\`                                                                      | Optional additional builtin tools to use for this run.                                                                                                                                            |
| `on_complete`           | \`OnCompleteFunc[EventT]                  | None\`                                                                      | Optional callback function called when the agent run completes successfully. The callback receives the completed AgentRunResult and can optionally yield additional protocol-specific events.     |

Source code in `pydantic_ai_slim/pydantic_ai/ui/_adapter.py`

```python
def run_stream(
    self,
    *,
    output_type: OutputSpec[Any] | None = None,
    message_history: Sequence[ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    model: Model | KnownModelName | str | None = None,
    instructions: Instructions[AgentDepsT] = None,
    deps: AgentDepsT = None,
    model_settings: ModelSettings | None = None,
    usage_limits: UsageLimits | None = None,
    usage: RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    builtin_tools: Sequence[AbstractBuiltinTool] | None = None,
    on_complete: OnCompleteFunc[EventT] | None = None,
) -> AsyncIterator[EventT]:
    """Run the agent with the protocol-specific run input and stream protocol-specific events.

    Args:
        output_type: Custom output type to use for this run, `output_type` may only be used if the agent has no
            output validators since output validators would expect an argument that matches the agent's output type.
        message_history: History of the conversation so far.
        deferred_tool_results: Optional results for deferred tool calls in the message history.
        model: Optional model to use for this run, required if `model` was not set when creating the agent.
        instructions: Optional additional instructions to use for this run.
        deps: Optional dependencies to use for this run.
        model_settings: Optional settings to use for this model's request.
        usage_limits: Optional limits on model request count or token usage.
        usage: Optional usage to start with, useful for resuming a conversation or agents used in tools.
        metadata: Optional metadata to attach to this run. Accepts a dictionary or a callable taking
            [`RunContext`][pydantic_ai.tools.RunContext]; merged with the agent's configured metadata.
        infer_name: Whether to try to infer the agent name from the call frame if it's not set.
        toolsets: Optional additional toolsets for this run.
        builtin_tools: Optional additional builtin tools to use for this run.
        on_complete: Optional callback function called when the agent run completes successfully.
            The callback receives the completed [`AgentRunResult`][pydantic_ai.agent.AgentRunResult] and can optionally yield additional protocol-specific events.
    """
    return self.transform_stream(
        self.run_stream_native(
            output_type=output_type,
            message_history=message_history,
            deferred_tool_results=deferred_tool_results,
            model=model,
            instructions=instructions,
            deps=deps,
            model_settings=model_settings,
            usage_limits=usage_limits,
            usage=usage,
            metadata=metadata,
            infer_name=infer_name,
            toolsets=toolsets,
            builtin_tools=builtin_tools,
        ),
        on_complete=on_complete,
    )
```

#### dispatch_request

```python
dispatch_request(
    request: Request,
    *,
    agent: AbstractAgent[
        DispatchDepsT, DispatchOutputDataT
    ],
    message_history: Sequence[ModelMessage] | None = None,
    deferred_tool_results: (
        DeferredToolResults | None
    ) = None,
    model: Model | KnownModelName | str | None = None,
    instructions: Instructions[DispatchDepsT] = None,
    deps: DispatchDepsT = None,
    output_type: OutputSpec[Any] | None = None,
    model_settings: ModelSettings | None = None,
    usage_limits: UsageLimits | None = None,
    usage: RunUsage | None = None,
    metadata: AgentMetadata[DispatchDepsT] | None = None,
    infer_name: bool = True,
    toolsets: (
        Sequence[AbstractToolset[DispatchDepsT]] | None
    ) = None,
    builtin_tools: (
        Sequence[AbstractBuiltinTool] | None
    ) = None,
    on_complete: OnCompleteFunc[EventT] | None = None
) -> Response
```

Handle a protocol-specific HTTP request by running the agent and returning a streaming response of protocol-specific events.

Parameters:

| Name                    | Type                                                | Description                                                                 | Default                                                                                                                                                                                           |
| ----------------------- | --------------------------------------------------- | --------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `request`               | `Request`                                           | The incoming Starlette/FastAPI request.                                     | *required*                                                                                                                                                                                        |
| `agent`                 | `AbstractAgent[DispatchDepsT, DispatchOutputDataT]` | The agent to run.                                                           | *required*                                                                                                                                                                                        |
| `output_type`           | \`OutputSpec[Any]                                   | None\`                                                                      | Custom output type to use for this run, output_type may only be used if the agent has no output validators since output validators would expect an argument that matches the agent's output type. |
| `message_history`       | \`Sequence[ModelMessage]                            | None\`                                                                      | History of the conversation so far.                                                                                                                                                               |
| `deferred_tool_results` | \`DeferredToolResults                               | None\`                                                                      | Optional results for deferred tool calls in the message history.                                                                                                                                  |
| `model`                 | \`Model                                             | KnownModelName                                                              | str                                                                                                                                                                                               |
| `instructions`          | `Instructions[DispatchDepsT]`                       | Optional additional instructions to use for this run.                       | `None`                                                                                                                                                                                            |
| `deps`                  | `DispatchDepsT`                                     | Optional dependencies to use for this run.                                  | `None`                                                                                                                                                                                            |
| `model_settings`        | \`ModelSettings                                     | None\`                                                                      | Optional settings to use for this model's request.                                                                                                                                                |
| `usage_limits`          | \`UsageLimits                                       | None\`                                                                      | Optional limits on model request count or token usage.                                                                                                                                            |
| `usage`                 | \`RunUsage                                          | None\`                                                                      | Optional usage to start with, useful for resuming a conversation or agents used in tools.                                                                                                         |
| `metadata`              | \`AgentMetadata[DispatchDepsT]                      | None\`                                                                      | Optional metadata to attach to this run. Accepts a dictionary or a callable taking RunContext; merged with the agent's configured metadata.                                                       |
| `infer_name`            | `bool`                                              | Whether to try to infer the agent name from the call frame if it's not set. | `True`                                                                                                                                                                                            |
| `toolsets`              | \`Sequence\[AbstractToolset[DispatchDepsT]\]        | None\`                                                                      | Optional additional toolsets for this run.                                                                                                                                                        |
| `builtin_tools`         | \`Sequence[AbstractBuiltinTool]                     | None\`                                                                      | Optional additional builtin tools to use for this run.                                                                                                                                            |
| `on_complete`           | \`OnCompleteFunc[EventT]                            | None\`                                                                      | Optional callback function called when the agent run completes successfully. The callback receives the completed AgentRunResult and can optionally yield additional protocol-specific events.     |

Returns:

| Type       | Description                                                                                                 |
| ---------- | ----------------------------------------------------------------------------------------------------------- |
| `Response` | A streaming Starlette response with protocol-specific events encoded per the request's Accept header value. |

Source code in `pydantic_ai_slim/pydantic_ai/ui/_adapter.py`

```python
@classmethod
async def dispatch_request(
    cls,
    request: Request,
    *,
    agent: AbstractAgent[DispatchDepsT, DispatchOutputDataT],
    message_history: Sequence[ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    model: Model | KnownModelName | str | None = None,
    instructions: Instructions[DispatchDepsT] = None,
    deps: DispatchDepsT = None,
    output_type: OutputSpec[Any] | None = None,
    model_settings: ModelSettings | None = None,
    usage_limits: UsageLimits | None = None,
    usage: RunUsage | None = None,
    metadata: AgentMetadata[DispatchDepsT] | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[DispatchDepsT]] | None = None,
    builtin_tools: Sequence[AbstractBuiltinTool] | None = None,
    on_complete: OnCompleteFunc[EventT] | None = None,
) -> Response:
    """Handle a protocol-specific HTTP request by running the agent and returning a streaming response of protocol-specific events.

    Args:
        request: The incoming Starlette/FastAPI request.
        agent: The agent to run.
        output_type: Custom output type to use for this run, `output_type` may only be used if the agent has no
            output validators since output validators would expect an argument that matches the agent's output type.
        message_history: History of the conversation so far.
        deferred_tool_results: Optional results for deferred tool calls in the message history.
        model: Optional model to use for this run, required if `model` was not set when creating the agent.
        instructions: Optional additional instructions to use for this run.
        deps: Optional dependencies to use for this run.
        model_settings: Optional settings to use for this model's request.
        usage_limits: Optional limits on model request count or token usage.
        usage: Optional usage to start with, useful for resuming a conversation or agents used in tools.
        metadata: Optional metadata to attach to this run. Accepts a dictionary or a callable taking
            [`RunContext`][pydantic_ai.tools.RunContext]; merged with the agent's configured metadata.
        infer_name: Whether to try to infer the agent name from the call frame if it's not set.
        toolsets: Optional additional toolsets for this run.
        builtin_tools: Optional additional builtin tools to use for this run.
        on_complete: Optional callback function called when the agent run completes successfully.
            The callback receives the completed [`AgentRunResult`][pydantic_ai.agent.AgentRunResult] and can optionally yield additional protocol-specific events.

    Returns:
        A streaming Starlette response with protocol-specific events encoded per the request's `Accept` header value.
    """
    try:
        from starlette.responses import Response
    except ImportError as e:  # pragma: no cover
        raise ImportError(
            'Please install the `starlette` package to use `dispatch_request()` method, '
            'you can use the `ui` optional group â€” `pip install "pydantic-ai-slim[ui]"`'
        ) from e

    try:
        # The DepsT and OutputDataT come from `agent`, not from `cls`; the cast is necessary to explain this to pyright
        adapter = cast(
            UIAdapter[RunInputT, MessageT, EventT, DispatchDepsT, DispatchOutputDataT],
            await cls.from_request(request, agent=cast(AbstractAgent[AgentDepsT, OutputDataT], agent)),
        )
    except ValidationError as e:  # pragma: no cover
        return Response(
            content=e.json(),
            media_type='application/json',
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        )

    return adapter.streaming_response(
        adapter.run_stream(
            message_history=message_history,
            deferred_tool_results=deferred_tool_results,
            deps=deps,
            output_type=output_type,
            model=model,
            instructions=instructions,
            model_settings=model_settings,
            usage_limits=usage_limits,
            usage=usage,
            metadata=metadata,
            infer_name=infer_name,
            toolsets=toolsets,
            builtin_tools=builtin_tools,
            on_complete=on_complete,
        ),
    )
```

### SSE_CONTENT_TYPE

```python
SSE_CONTENT_TYPE = 'text/event-stream'
```

Content type header value for Server-Sent Events (SSE).

### NativeEvent

```python
NativeEvent: TypeAlias = (
    AgentStreamEvent | AgentRunResultEvent[Any]
)
```

Type alias for the native event type, which is either an `AgentStreamEvent` or an `AgentRunResultEvent`.

### OnCompleteFunc

```python
OnCompleteFunc: TypeAlias = (
    Callable[[AgentRunResult[Any]], None]
    | Callable[[AgentRunResult[Any]], Awaitable[None]]
    | Callable[[AgentRunResult[Any]], AsyncIterator[EventT]]
)
```

Callback function type that receives the `AgentRunResult` of the completed run. Can be sync, async, or an async generator of protocol-specific events.

### UIEventStream

Bases: `ABC`, `Generic[RunInputT, EventT, AgentDepsT, OutputDataT]`

Base class for UI event stream transformers.

This class is responsible for transforming Pydantic AI events into protocol-specific events.

Source code in `pydantic_ai_slim/pydantic_ai/ui/_event_stream.py`

```python
@dataclass
class UIEventStream(ABC, Generic[RunInputT, EventT, AgentDepsT, OutputDataT]):
    """Base class for UI event stream transformers.

    This class is responsible for transforming Pydantic AI events into protocol-specific events.
    """

    run_input: RunInputT

    accept: str | None = None
    """The `Accept` header value of the request, used to determine how to encode the protocol-specific events for the streaming response."""

    message_id: str = field(default_factory=lambda: str(uuid4()))
    """The message ID to use for the next event."""

    _turn: Literal['request', 'response'] | None = None

    _result: AgentRunResult[OutputDataT] | None = None
    _final_result_event: FinalResultEvent | None = None

    def new_message_id(self) -> str:
        """Generate and store a new message ID."""
        self.message_id = str(uuid4())
        return self.message_id

    @property
    def response_headers(self) -> Mapping[str, str] | None:
        """Response headers to return to the frontend."""
        return None

    @property
    def content_type(self) -> str:
        """Get the content type for the event stream, compatible with the `Accept` header value.

        By default, this returns the Server-Sent Events content type (`text/event-stream`).
        If a subclass supports other types as well, it should consider `self.accept` in [`encode_event()`][pydantic_ai.ui.UIEventStream.encode_event] and return the resulting content type.
        """
        return SSE_CONTENT_TYPE

    @abstractmethod
    def encode_event(self, event: EventT) -> str:
        """Encode a protocol-specific event as a string."""
        raise NotImplementedError

    async def encode_stream(self, stream: AsyncIterator[EventT]) -> AsyncIterator[str]:
        """Encode a stream of protocol-specific events as strings according to the `Accept` header value."""
        async for event in stream:
            yield self.encode_event(event)

    def streaming_response(self, stream: AsyncIterator[EventT]) -> StreamingResponse:
        """Generate a streaming response from a stream of protocol-specific events."""
        try:
            from starlette.responses import StreamingResponse
        except ImportError as e:  # pragma: no cover
            raise ImportError(
                'Please install the `starlette` package to use the `streaming_response()` method, '
                'you can use the `ui` optional group â€” `pip install "pydantic-ai-slim[ui]"`'
            ) from e

        return StreamingResponse(
            self.encode_stream(stream),
            headers=self.response_headers,
            media_type=self.content_type,
        )

    async def transform_stream(  # noqa: C901
        self, stream: AsyncIterator[NativeEvent], on_complete: OnCompleteFunc[EventT] | None = None
    ) -> AsyncIterator[EventT]:
        """Transform a stream of Pydantic AI events into protocol-specific events.

        This method dispatches to specific hooks and `handle_*` methods that subclasses can override:
        - [`before_stream()`][pydantic_ai.ui.UIEventStream.before_stream]
        - [`after_stream()`][pydantic_ai.ui.UIEventStream.after_stream]
        - [`on_error()`][pydantic_ai.ui.UIEventStream.on_error]
        - [`before_request()`][pydantic_ai.ui.UIEventStream.before_request]
        - [`after_request()`][pydantic_ai.ui.UIEventStream.after_request]
        - [`before_response()`][pydantic_ai.ui.UIEventStream.before_response]
        - [`after_response()`][pydantic_ai.ui.UIEventStream.after_response]
        - [`handle_event()`][pydantic_ai.ui.UIEventStream.handle_event]

        Args:
            stream: The stream of Pydantic AI events to transform.
            on_complete: Optional callback function called when the agent run completes successfully.
                The callback receives the completed [`AgentRunResult`][pydantic_ai.agent.AgentRunResult] and can optionally yield additional protocol-specific events.
        """
        async for e in self.before_stream():
            yield e

        try:
            async for event in stream:
                if isinstance(event, PartStartEvent):
                    async for e in self._turn_to('response'):
                        yield e
                elif isinstance(event, FunctionToolCallEvent):
                    async for e in self._turn_to('request'):
                        yield e
                elif isinstance(event, AgentRunResultEvent):
                    if (
                        self._final_result_event
                        and (tool_call_id := self._final_result_event.tool_call_id)
                        and (tool_name := self._final_result_event.tool_name)
                    ):
                        async for e in self._turn_to('request'):
                            yield e

                        self._final_result_event = None
                        # Ensure the stream does not end on a dangling tool call without a result.
                        output_tool_result_event = FunctionToolResultEvent(
                            result=ToolReturnPart(
                                tool_call_id=tool_call_id,
                                tool_name=tool_name,
                                content='Final result processed.',
                            )
                        )
                        async for e in self.handle_function_tool_result(output_tool_result_event):
                            yield e

                    result = cast(AgentRunResult[OutputDataT], event.result)
                    self._result = result

                    async for e in self._turn_to(None):
                        yield e

                    if on_complete is not None:
                        if inspect.isasyncgenfunction(on_complete):
                            async for e in on_complete(result):
                                yield e
                        elif _utils.is_async_callable(on_complete):
                            await on_complete(result)
                        else:
                            await _utils.run_in_executor(on_complete, result)
                elif isinstance(event, FinalResultEvent):
                    self._final_result_event = event

                if isinstance(event, BuiltinToolCallEvent | BuiltinToolResultEvent):  # pyright: ignore[reportDeprecated]
                    # These events were deprecated before this feature was introduced
                    continue

                async for e in self.handle_event(event):
                    yield e
        except Exception as e:
            async for e in self.on_error(e):
                yield e
        finally:
            async for e in self._turn_to(None):
                yield e

            async for e in self.after_stream():
                yield e

    async def _turn_to(self, to_turn: Literal['request', 'response'] | None) -> AsyncIterator[EventT]:
        """Fire hooks when turning from request to response or vice versa."""
        if to_turn == self._turn:
            return

        if self._turn == 'request':
            async for e in self.after_request():
                yield e
        elif self._turn == 'response':
            async for e in self.after_response():
                yield e

        self._turn = to_turn

        if to_turn == 'request':
            async for e in self.before_request():
                yield e
        elif to_turn == 'response':
            async for e in self.before_response():
                yield e

    async def handle_event(self, event: NativeEvent) -> AsyncIterator[EventT]:
        """Transform a Pydantic AI event into one or more protocol-specific events.

        This method dispatches to specific `handle_*` methods based on event type:

        - [`PartStartEvent`][pydantic_ai.messages.PartStartEvent] -> [`handle_part_start()`][pydantic_ai.ui.UIEventStream.handle_part_start]
        - [`PartDeltaEvent`][pydantic_ai.messages.PartDeltaEvent] -> `handle_part_delta`
        - [`PartEndEvent`][pydantic_ai.messages.PartEndEvent] -> `handle_part_end`
        - [`FinalResultEvent`][pydantic_ai.messages.FinalResultEvent] -> `handle_final_result`
        - [`FunctionToolCallEvent`][pydantic_ai.messages.FunctionToolCallEvent] -> `handle_function_tool_call`
        - [`FunctionToolResultEvent`][pydantic_ai.messages.FunctionToolResultEvent] -> `handle_function_tool_result`
        - [`AgentRunResultEvent`][pydantic_ai.run.AgentRunResultEvent] -> `handle_run_result`

        Subclasses are encouraged to override the individual `handle_*` methods rather than this one.
        If you need specific behavior for all events, make sure you call the super method.
        """
        match event:
            case PartStartEvent():
                async for e in self.handle_part_start(event):
                    yield e
            case PartDeltaEvent():
                async for e in self.handle_part_delta(event):
                    yield e
            case PartEndEvent():
                async for e in self.handle_part_end(event):
                    yield e
            case FinalResultEvent():
                async for e in self.handle_final_result(event):
                    yield e
            case FunctionToolCallEvent():
                async for e in self.handle_function_tool_call(event):
                    yield e
            case FunctionToolResultEvent():
                async for e in self.handle_function_tool_result(event):
                    yield e
            case AgentRunResultEvent():
                async for e in self.handle_run_result(event):
                    yield e
            case _:
                pass

    async def handle_part_start(self, event: PartStartEvent) -> AsyncIterator[EventT]:
        """Handle a `PartStartEvent`.

        This method dispatches to specific `handle_*` methods based on part type:

        - [`TextPart`][pydantic_ai.messages.TextPart] -> [`handle_text_start()`][pydantic_ai.ui.UIEventStream.handle_text_start]
        - [`ThinkingPart`][pydantic_ai.messages.ThinkingPart] -> [`handle_thinking_start()`][pydantic_ai.ui.UIEventStream.handle_thinking_start]
        - [`ToolCallPart`][pydantic_ai.messages.ToolCallPart] -> [`handle_tool_call_start()`][pydantic_ai.ui.UIEventStream.handle_tool_call_start]
        - [`BuiltinToolCallPart`][pydantic_ai.messages.BuiltinToolCallPart] -> [`handle_builtin_tool_call_start()`][pydantic_ai.ui.UIEventStream.handle_builtin_tool_call_start]
        - [`BuiltinToolReturnPart`][pydantic_ai.messages.BuiltinToolReturnPart] -> [`handle_builtin_tool_return()`][pydantic_ai.ui.UIEventStream.handle_builtin_tool_return]
        - [`FilePart`][pydantic_ai.messages.FilePart] -> [`handle_file()`][pydantic_ai.ui.UIEventStream.handle_file]

        Subclasses are encouraged to override the individual `handle_*` methods rather than this one.
        If you need specific behavior for all part start events, make sure you call the super method.

        Args:
            event: The part start event.
        """
        part = event.part
        previous_part_kind = event.previous_part_kind
        match part:
            case TextPart():
                async for e in self.handle_text_start(part, follows_text=previous_part_kind == 'text'):
                    yield e
            case ThinkingPart():
                async for e in self.handle_thinking_start(part, follows_thinking=previous_part_kind == 'thinking'):
                    yield e
            case ToolCallPart():
                async for e in self.handle_tool_call_start(part):
                    yield e
            case BuiltinToolCallPart():
                async for e in self.handle_builtin_tool_call_start(part):
                    yield e
            case BuiltinToolReturnPart():
                async for e in self.handle_builtin_tool_return(part):
                    yield e
            case FilePart():  # pragma: no branch
                async for e in self.handle_file(part):
                    yield e

    async def handle_part_delta(self, event: PartDeltaEvent) -> AsyncIterator[EventT]:
        """Handle a PartDeltaEvent.

        This method dispatches to specific `handle_*_delta` methods based on part delta type:

        - [`TextPartDelta`][pydantic_ai.messages.TextPartDelta] -> [`handle_text_delta()`][pydantic_ai.ui.UIEventStream.handle_text_delta]
        - [`ThinkingPartDelta`][pydantic_ai.messages.ThinkingPartDelta] -> [`handle_thinking_delta()`][pydantic_ai.ui.UIEventStream.handle_thinking_delta]
        - [`ToolCallPartDelta`][pydantic_ai.messages.ToolCallPartDelta] -> [`handle_tool_call_delta()`][pydantic_ai.ui.UIEventStream.handle_tool_call_delta]

        Subclasses are encouraged to override the individual `handle_*_delta` methods rather than this one.
        If you need specific behavior for all part delta events, make sure you call the super method.

        Args:
            event: The PartDeltaEvent.
        """
        delta = event.delta
        match delta:
            case TextPartDelta():
                async for e in self.handle_text_delta(delta):
                    yield e
            case ThinkingPartDelta():
                async for e in self.handle_thinking_delta(delta):
                    yield e
            case ToolCallPartDelta():  # pragma: no branch
                async for e in self.handle_tool_call_delta(delta):
                    yield e

    async def handle_part_end(self, event: PartEndEvent) -> AsyncIterator[EventT]:
        """Handle a `PartEndEvent`.

        This method dispatches to specific `handle_*_end` methods based on part type:

        - [`TextPart`][pydantic_ai.messages.TextPart] -> [`handle_text_end()`][pydantic_ai.ui.UIEventStream.handle_text_end]
        - [`ThinkingPart`][pydantic_ai.messages.ThinkingPart] -> [`handle_thinking_end()`][pydantic_ai.ui.UIEventStream.handle_thinking_end]
        - [`ToolCallPart`][pydantic_ai.messages.ToolCallPart] -> [`handle_tool_call_end()`][pydantic_ai.ui.UIEventStream.handle_tool_call_end]
        - [`BuiltinToolCallPart`][pydantic_ai.messages.BuiltinToolCallPart] -> [`handle_builtin_tool_call_end()`][pydantic_ai.ui.UIEventStream.handle_builtin_tool_call_end]

        Subclasses are encouraged to override the individual `handle_*_end` methods rather than this one.
        If you need specific behavior for all part end events, make sure you call the super method.

        Args:
            event: The part end event.
        """
        part = event.part
        next_part_kind = event.next_part_kind
        match part:
            case TextPart():
                async for e in self.handle_text_end(part, followed_by_text=next_part_kind == 'text'):
                    yield e
            case ThinkingPart():
                async for e in self.handle_thinking_end(part, followed_by_thinking=next_part_kind == 'thinking'):
                    yield e
            case ToolCallPart():
                async for e in self.handle_tool_call_end(part):
                    yield e
            case BuiltinToolCallPart():
                async for e in self.handle_builtin_tool_call_end(part):
                    yield e
            case BuiltinToolReturnPart() | FilePart():  # pragma: no cover
                # These don't have deltas, so they don't need to be ended.
                pass

    async def before_stream(self) -> AsyncIterator[EventT]:
        """Yield events before agent streaming starts.

        This hook is called before any agent events are processed.
        Override this to inject custom events at the start of the stream.
        """
        return  # pragma: no cover
        yield  # Make this an async generator

    async def after_stream(self) -> AsyncIterator[EventT]:
        """Yield events after agent streaming completes.

        This hook is called after all agent events have been processed.
        Override this to inject custom events at the end of the stream.
        """
        return  # pragma: no cover
        yield  # Make this an async generator

    async def on_error(self, error: Exception) -> AsyncIterator[EventT]:
        """Handle errors that occur during streaming.

        Args:
            error: The error that occurred during streaming.
        """
        return  # pragma: no cover
        yield  # Make this an async generator

    async def before_request(self) -> AsyncIterator[EventT]:
        """Yield events before a model request is processed.

        Override this to inject custom events at the start of the request.
        """
        return  # pragma: lax no cover
        yield  # Make this an async generator

    async def after_request(self) -> AsyncIterator[EventT]:
        """Yield events after a model request is processed.

        Override this to inject custom events at the end of the request.
        """
        return  # pragma: lax no cover
        yield  # Make this an async generator

    async def before_response(self) -> AsyncIterator[EventT]:
        """Yield events before a model response is processed.

        Override this to inject custom events at the start of the response.
        """
        return  # pragma: no cover
        yield  # Make this an async generator

    async def after_response(self) -> AsyncIterator[EventT]:
        """Yield events after a model response is processed.

        Override this to inject custom events at the end of the response.
        """
        return  # pragma: lax no cover
        yield  # Make this an async generator

    async def handle_text_start(self, part: TextPart, follows_text: bool = False) -> AsyncIterator[EventT]:
        """Handle the start of a `TextPart`.

        Args:
            part: The text part.
            follows_text: Whether the part is directly preceded by another text part. In this case, you may want to yield a "text-delta" event instead of a "text-start" event.
        """
        return  # pragma: no cover
        yield  # Make this an async generator

    async def handle_text_delta(self, delta: TextPartDelta) -> AsyncIterator[EventT]:
        """Handle a `TextPartDelta`.

        Args:
            delta: The text part delta.
        """
        return  # pragma: no cover
        yield  # Make this an async generator

    async def handle_text_end(self, part: TextPart, followed_by_text: bool = False) -> AsyncIterator[EventT]:
        """Handle the end of a `TextPart`.

        Args:
            part: The text part.
            followed_by_text: Whether the part is directly followed by another text part. In this case, you may not want to yield a "text-end" event yet.
        """
        return  # pragma: no cover
        yield  # Make this an async generator

    async def handle_thinking_start(self, part: ThinkingPart, follows_thinking: bool = False) -> AsyncIterator[EventT]:
        """Handle the start of a `ThinkingPart`.

        Args:
            part: The thinking part.
            follows_thinking: Whether the part is directly preceded by another thinking part. In this case, you may want to yield a "thinking-delta" event instead of a "thinking-start" event.
        """
        return  # pragma: no cover
        yield  # Make this an async generator

    async def handle_thinking_delta(self, delta: ThinkingPartDelta) -> AsyncIterator[EventT]:
        """Handle a `ThinkingPartDelta`.

        Args:
            delta: The thinking part delta.
        """
        return  # pragma: no cover
        yield  # Make this an async generator

    async def handle_thinking_end(
        self, part: ThinkingPart, followed_by_thinking: bool = False
    ) -> AsyncIterator[EventT]:
        """Handle the end of a `ThinkingPart`.

        Args:
            part: The thinking part.
            followed_by_thinking: Whether the part is directly followed by another thinking part. In this case, you may not want to yield a "thinking-end" event yet.
        """
        return  # pragma: no cover
        yield  # Make this an async generator

    async def handle_tool_call_start(self, part: ToolCallPart) -> AsyncIterator[EventT]:
        """Handle the start of a `ToolCallPart`.

        Args:
            part: The tool call part.
        """
        return  # pragma: no cover
        yield  # Make this an async generator

    async def handle_tool_call_delta(self, delta: ToolCallPartDelta) -> AsyncIterator[EventT]:
        """Handle a `ToolCallPartDelta`.

        Args:
            delta: The tool call part delta.
        """
        return  # pragma: no cover
        yield  # Make this an async generator

    async def handle_tool_call_end(self, part: ToolCallPart) -> AsyncIterator[EventT]:
        """Handle the end of a `ToolCallPart`.

        Args:
            part: The tool call part.
        """
        return  # pragma: no cover
        yield  # Make this an async generator

    async def handle_builtin_tool_call_start(self, part: BuiltinToolCallPart) -> AsyncIterator[EventT]:
        """Handle a `BuiltinToolCallPart` at start.

        Args:
            part: The builtin tool call part.
        """
        return  # pragma: no cover
        yield  # Make this an async generator

    async def handle_builtin_tool_call_end(self, part: BuiltinToolCallPart) -> AsyncIterator[EventT]:
        """Handle the end of a `BuiltinToolCallPart`.

        Args:
            part: The builtin tool call part.
        """
        return  # pragma: no cover
        yield  # Make this an async generator

    async def handle_builtin_tool_return(self, part: BuiltinToolReturnPart) -> AsyncIterator[EventT]:
        """Handle a `BuiltinToolReturnPart`.

        Args:
            part: The builtin tool return part.
        """
        return  # pragma: no cover
        yield  # Make this an async generator

    async def handle_file(self, part: FilePart) -> AsyncIterator[EventT]:
        """Handle a `FilePart`.

        Args:
            part: The file part.
        """
        return  # pragma: no cover
        yield  # Make this an async generator

    async def handle_final_result(self, event: FinalResultEvent) -> AsyncIterator[EventT]:
        """Handle a `FinalResultEvent`.

        Args:
            event: The final result event.
        """
        return
        yield  # Make this an async generator

    async def handle_function_tool_call(self, event: FunctionToolCallEvent) -> AsyncIterator[EventT]:
        """Handle a `FunctionToolCallEvent`.

        Args:
            event: The function tool call event.
        """
        return
        yield  # Make this an async generator

    async def handle_function_tool_result(self, event: FunctionToolResultEvent) -> AsyncIterator[EventT]:
        """Handle a `FunctionToolResultEvent`.

        Args:
            event: The function tool result event.
        """
        return  # pragma: no cover
        yield  # Make this an async generator

    async def handle_run_result(self, event: AgentRunResultEvent) -> AsyncIterator[EventT]:
        """Handle an `AgentRunResultEvent`.

        Args:
            event: The agent run result event.
        """
        return
        yield  # Make this an async generator
```

#### accept

```python
accept: str | None = None
```

The `Accept` header value of the request, used to determine how to encode the protocol-specific events for the streaming response.

#### message_id

```python
message_id: str = field(
    default_factory=lambda: str(uuid4())
)
```

The message ID to use for the next event.

#### new_message_id

```python
new_message_id() -> str
```

Generate and store a new message ID.

Source code in `pydantic_ai_slim/pydantic_ai/ui/_event_stream.py`

```python
def new_message_id(self) -> str:
    """Generate and store a new message ID."""
    self.message_id = str(uuid4())
    return self.message_id
```

#### response_headers

```python
response_headers: Mapping[str, str] | None
```

Response headers to return to the frontend.

#### content_type

```python
content_type: str
```

Get the content type for the event stream, compatible with the `Accept` header value.

By default, this returns the Server-Sent Events content type (`text/event-stream`). If a subclass supports other types as well, it should consider `self.accept` in encode_event() and return the resulting content type.

#### encode_event

```python
encode_event(event: EventT) -> str
```

Encode a protocol-specific event as a string.

Source code in `pydantic_ai_slim/pydantic_ai/ui/_event_stream.py`

```python
@abstractmethod
def encode_event(self, event: EventT) -> str:
    """Encode a protocol-specific event as a string."""
    raise NotImplementedError
```

#### encode_stream

```python
encode_stream(
    stream: AsyncIterator[EventT],
) -> AsyncIterator[str]
```

Encode a stream of protocol-specific events as strings according to the `Accept` header value.

Source code in `pydantic_ai_slim/pydantic_ai/ui/_event_stream.py`

```python
async def encode_stream(self, stream: AsyncIterator[EventT]) -> AsyncIterator[str]:
    """Encode a stream of protocol-specific events as strings according to the `Accept` header value."""
    async for event in stream:
        yield self.encode_event(event)
```

#### streaming_response

```python
streaming_response(
    stream: AsyncIterator[EventT],
) -> StreamingResponse
```

Generate a streaming response from a stream of protocol-specific events.

Source code in `pydantic_ai_slim/pydantic_ai/ui/_event_stream.py`

```python
def streaming_response(self, stream: AsyncIterator[EventT]) -> StreamingResponse:
    """Generate a streaming response from a stream of protocol-specific events."""
    try:
        from starlette.responses import StreamingResponse
    except ImportError as e:  # pragma: no cover
        raise ImportError(
            'Please install the `starlette` package to use the `streaming_response()` method, '
            'you can use the `ui` optional group â€” `pip install "pydantic-ai-slim[ui]"`'
        ) from e

    return StreamingResponse(
        self.encode_stream(stream),
        headers=self.response_headers,
        media_type=self.content_type,
    )
```

#### transform_stream

```python
transform_stream(
    stream: AsyncIterator[NativeEvent],
    on_complete: OnCompleteFunc[EventT] | None = None,
) -> AsyncIterator[EventT]
```

Transform a stream of Pydantic AI events into protocol-specific events.

This method dispatches to specific hooks and `handle_*` methods that subclasses can override:

- before_stream()
- after_stream()
- on_error()
- before_request()
- after_request()
- before_response()
- after_response()
- handle_event()

Parameters:

| Name          | Type                         | Description                                    | Default                                                                                                                                                                                       |
| ------------- | ---------------------------- | ---------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `stream`      | `AsyncIterator[NativeEvent]` | The stream of Pydantic AI events to transform. | *required*                                                                                                                                                                                    |
| `on_complete` | \`OnCompleteFunc[EventT]     | None\`                                         | Optional callback function called when the agent run completes successfully. The callback receives the completed AgentRunResult and can optionally yield additional protocol-specific events. |

Source code in `pydantic_ai_slim/pydantic_ai/ui/_event_stream.py`

```python
async def transform_stream(  # noqa: C901
    self, stream: AsyncIterator[NativeEvent], on_complete: OnCompleteFunc[EventT] | None = None
) -> AsyncIterator[EventT]:
    """Transform a stream of Pydantic AI events into protocol-specific events.

    This method dispatches to specific hooks and `handle_*` methods that subclasses can override:
    - [`before_stream()`][pydantic_ai.ui.UIEventStream.before_stream]
    - [`after_stream()`][pydantic_ai.ui.UIEventStream.after_stream]
    - [`on_error()`][pydantic_ai.ui.UIEventStream.on_error]
    - [`before_request()`][pydantic_ai.ui.UIEventStream.before_request]
    - [`after_request()`][pydantic_ai.ui.UIEventStream.after_request]
    - [`before_response()`][pydantic_ai.ui.UIEventStream.before_response]
    - [`after_response()`][pydantic_ai.ui.UIEventStream.after_response]
    - [`handle_event()`][pydantic_ai.ui.UIEventStream.handle_event]

    Args:
        stream: The stream of Pydantic AI events to transform.
        on_complete: Optional callback function called when the agent run completes successfully.
            The callback receives the completed [`AgentRunResult`][pydantic_ai.agent.AgentRunResult] and can optionally yield additional protocol-specific events.
    """
    async for e in self.before_stream():
        yield e

    try:
        async for event in stream:
            if isinstance(event, PartStartEvent):
                async for e in self._turn_to('response'):
                    yield e
            elif isinstance(event, FunctionToolCallEvent):
                async for e in self._turn_to('request'):
                    yield e
            elif isinstance(event, AgentRunResultEvent):
                if (
                    self._final_result_event
                    and (tool_call_id := self._final_result_event.tool_call_id)
                    and (tool_name := self._final_result_event.tool_name)
                ):
                    async for e in self._turn_to('request'):
                        yield e

                    self._final_result_event = None
                    # Ensure the stream does not end on a dangling tool call without a result.
                    output_tool_result_event = FunctionToolResultEvent(
                        result=ToolReturnPart(
                            tool_call_id=tool_call_id,
                            tool_name=tool_name,
                            content='Final result processed.',
                        )
                    )
                    async for e in self.handle_function_tool_result(output_tool_result_event):
                        yield e

                result = cast(AgentRunResult[OutputDataT], event.result)
                self._result = result

                async for e in self._turn_to(None):
                    yield e

                if on_complete is not None:
                    if inspect.isasyncgenfunction(on_complete):
                        async for e in on_complete(result):
                            yield e
                    elif _utils.is_async_callable(on_complete):
                        await on_complete(result)
                    else:
                        await _utils.run_in_executor(on_complete, result)
            elif isinstance(event, FinalResultEvent):
                self._final_result_event = event

            if isinstance(event, BuiltinToolCallEvent | BuiltinToolResultEvent):  # pyright: ignore[reportDeprecated]
                # These events were deprecated before this feature was introduced
                continue

            async for e in self.handle_event(event):
                yield e
    except Exception as e:
        async for e in self.on_error(e):
            yield e
    finally:
        async for e in self._turn_to(None):
            yield e

        async for e in self.after_stream():
            yield e
```

#### handle_event

```python
handle_event(event: NativeEvent) -> AsyncIterator[EventT]
```

Transform a Pydantic AI event into one or more protocol-specific events.

This method dispatches to specific `handle_*` methods based on event type:

- PartStartEvent -> handle_part_start()
- PartDeltaEvent -> `handle_part_delta`
- PartEndEvent -> `handle_part_end`
- FinalResultEvent -> `handle_final_result`
- FunctionToolCallEvent -> `handle_function_tool_call`
- FunctionToolResultEvent -> `handle_function_tool_result`
- AgentRunResultEvent -> `handle_run_result`

Subclasses are encouraged to override the individual `handle_*` methods rather than this one. If you need specific behavior for all events, make sure you call the super method.

Source code in `pydantic_ai_slim/pydantic_ai/ui/_event_stream.py`

```python
async def handle_event(self, event: NativeEvent) -> AsyncIterator[EventT]:
    """Transform a Pydantic AI event into one or more protocol-specific events.

    This method dispatches to specific `handle_*` methods based on event type:

    - [`PartStartEvent`][pydantic_ai.messages.PartStartEvent] -> [`handle_part_start()`][pydantic_ai.ui.UIEventStream.handle_part_start]
    - [`PartDeltaEvent`][pydantic_ai.messages.PartDeltaEvent] -> `handle_part_delta`
    - [`PartEndEvent`][pydantic_ai.messages.PartEndEvent] -> `handle_part_end`
    - [`FinalResultEvent`][pydantic_ai.messages.FinalResultEvent] -> `handle_final_result`
    - [`FunctionToolCallEvent`][pydantic_ai.messages.FunctionToolCallEvent] -> `handle_function_tool_call`
    - [`FunctionToolResultEvent`][pydantic_ai.messages.FunctionToolResultEvent] -> `handle_function_tool_result`
    - [`AgentRunResultEvent`][pydantic_ai.run.AgentRunResultEvent] -> `handle_run_result`

    Subclasses are encouraged to override the individual `handle_*` methods rather than this one.
    If you need specific behavior for all events, make sure you call the super method.
    """
    match event:
        case PartStartEvent():
            async for e in self.handle_part_start(event):
                yield e
        case PartDeltaEvent():
            async for e in self.handle_part_delta(event):
                yield e
        case PartEndEvent():
            async for e in self.handle_part_end(event):
                yield e
        case FinalResultEvent():
            async for e in self.handle_final_result(event):
                yield e
        case FunctionToolCallEvent():
            async for e in self.handle_function_tool_call(event):
                yield e
        case FunctionToolResultEvent():
            async for e in self.handle_function_tool_result(event):
                yield e
        case AgentRunResultEvent():
            async for e in self.handle_run_result(event):
                yield e
        case _:
            pass
```

#### handle_part_start

```python
handle_part_start(
    event: PartStartEvent,
) -> AsyncIterator[EventT]
```

Handle a `PartStartEvent`.

This method dispatches to specific `handle_*` methods based on part type:

- TextPart -> handle_text_start()
- ThinkingPart -> handle_thinking_start()
- ToolCallPart -> handle_tool_call_start()
- BuiltinToolCallPart -> handle_builtin_tool_call_start()
- BuiltinToolReturnPart -> handle_builtin_tool_return()
- FilePart -> handle_file()

Subclasses are encouraged to override the individual `handle_*` methods rather than this one. If you need specific behavior for all part start events, make sure you call the super method.

Parameters:

| Name    | Type             | Description           | Default    |
| ------- | ---------------- | --------------------- | ---------- |
| `event` | `PartStartEvent` | The part start event. | *required* |

Source code in `pydantic_ai_slim/pydantic_ai/ui/_event_stream.py`

```python
async def handle_part_start(self, event: PartStartEvent) -> AsyncIterator[EventT]:
    """Handle a `PartStartEvent`.

    This method dispatches to specific `handle_*` methods based on part type:

    - [`TextPart`][pydantic_ai.messages.TextPart] -> [`handle_text_start()`][pydantic_ai.ui.UIEventStream.handle_text_start]
    - [`ThinkingPart`][pydantic_ai.messages.ThinkingPart] -> [`handle_thinking_start()`][pydantic_ai.ui.UIEventStream.handle_thinking_start]
    - [`ToolCallPart`][pydantic_ai.messages.ToolCallPart] -> [`handle_tool_call_start()`][pydantic_ai.ui.UIEventStream.handle_tool_call_start]
    - [`BuiltinToolCallPart`][pydantic_ai.messages.BuiltinToolCallPart] -> [`handle_builtin_tool_call_start()`][pydantic_ai.ui.UIEventStream.handle_builtin_tool_call_start]
    - [`BuiltinToolReturnPart`][pydantic_ai.messages.BuiltinToolReturnPart] -> [`handle_builtin_tool_return()`][pydantic_ai.ui.UIEventStream.handle_builtin_tool_return]
    - [`FilePart`][pydantic_ai.messages.FilePart] -> [`handle_file()`][pydantic_ai.ui.UIEventStream.handle_file]

    Subclasses are encouraged to override the individual `handle_*` methods rather than this one.
    If you need specific behavior for all part start events, make sure you call the super method.

    Args:
        event: The part start event.
    """
    part = event.part
    previous_part_kind = event.previous_part_kind
    match part:
        case TextPart():
            async for e in self.handle_text_start(part, follows_text=previous_part_kind == 'text'):
                yield e
        case ThinkingPart():
            async for e in self.handle_thinking_start(part, follows_thinking=previous_part_kind == 'thinking'):
                yield e
        case ToolCallPart():
            async for e in self.handle_tool_call_start(part):
                yield e
        case BuiltinToolCallPart():
            async for e in self.handle_builtin_tool_call_start(part):
                yield e
        case BuiltinToolReturnPart():
            async for e in self.handle_builtin_tool_return(part):
                yield e
        case FilePart():  # pragma: no branch
            async for e in self.handle_file(part):
                yield e
```

#### handle_part_delta

```python
handle_part_delta(
    event: PartDeltaEvent,
) -> AsyncIterator[EventT]
```

Handle a PartDeltaEvent.

This method dispatches to specific `handle_*_delta` methods based on part delta type:

- TextPartDelta -> handle_text_delta()
- ThinkingPartDelta -> handle_thinking_delta()
- ToolCallPartDelta -> handle_tool_call_delta()

Subclasses are encouraged to override the individual `handle_*_delta` methods rather than this one. If you need specific behavior for all part delta events, make sure you call the super method.

Parameters:

| Name    | Type             | Description         | Default    |
| ------- | ---------------- | ------------------- | ---------- |
| `event` | `PartDeltaEvent` | The PartDeltaEvent. | *required* |

Source code in `pydantic_ai_slim/pydantic_ai/ui/_event_stream.py`

```python
async def handle_part_delta(self, event: PartDeltaEvent) -> AsyncIterator[EventT]:
    """Handle a PartDeltaEvent.

    This method dispatches to specific `handle_*_delta` methods based on part delta type:

    - [`TextPartDelta`][pydantic_ai.messages.TextPartDelta] -> [`handle_text_delta()`][pydantic_ai.ui.UIEventStream.handle_text_delta]
    - [`ThinkingPartDelta`][pydantic_ai.messages.ThinkingPartDelta] -> [`handle_thinking_delta()`][pydantic_ai.ui.UIEventStream.handle_thinking_delta]
    - [`ToolCallPartDelta`][pydantic_ai.messages.ToolCallPartDelta] -> [`handle_tool_call_delta()`][pydantic_ai.ui.UIEventStream.handle_tool_call_delta]

    Subclasses are encouraged to override the individual `handle_*_delta` methods rather than this one.
    If you need specific behavior for all part delta events, make sure you call the super method.

    Args:
        event: The PartDeltaEvent.
    """
    delta = event.delta
    match delta:
        case TextPartDelta():
            async for e in self.handle_text_delta(delta):
                yield e
        case ThinkingPartDelta():
            async for e in self.handle_thinking_delta(delta):
                yield e
        case ToolCallPartDelta():  # pragma: no branch
            async for e in self.handle_tool_call_delta(delta):
                yield e
```

#### handle_part_end

```python
handle_part_end(
    event: PartEndEvent,
) -> AsyncIterator[EventT]
```

Handle a `PartEndEvent`.

This method dispatches to specific `handle_*_end` methods based on part type:

- TextPart -> handle_text_end()
- ThinkingPart -> handle_thinking_end()
- ToolCallPart -> handle_tool_call_end()
- BuiltinToolCallPart -> handle_builtin_tool_call_end()

Subclasses are encouraged to override the individual `handle_*_end` methods rather than this one. If you need specific behavior for all part end events, make sure you call the super method.

Parameters:

| Name    | Type           | Description         | Default    |
| ------- | -------------- | ------------------- | ---------- |
| `event` | `PartEndEvent` | The part end event. | *required* |

Source code in `pydantic_ai_slim/pydantic_ai/ui/_event_stream.py`

```python
async def handle_part_end(self, event: PartEndEvent) -> AsyncIterator[EventT]:
    """Handle a `PartEndEvent`.

    This method dispatches to specific `handle_*_end` methods based on part type:

    - [`TextPart`][pydantic_ai.messages.TextPart] -> [`handle_text_end()`][pydantic_ai.ui.UIEventStream.handle_text_end]
    - [`ThinkingPart`][pydantic_ai.messages.ThinkingPart] -> [`handle_thinking_end()`][pydantic_ai.ui.UIEventStream.handle_thinking_end]
    - [`ToolCallPart`][pydantic_ai.messages.ToolCallPart] -> [`handle_tool_call_end()`][pydantic_ai.ui.UIEventStream.handle_tool_call_end]
    - [`BuiltinToolCallPart`][pydantic_ai.messages.BuiltinToolCallPart] -> [`handle_builtin_tool_call_end()`][pydantic_ai.ui.UIEventStream.handle_builtin_tool_call_end]

    Subclasses are encouraged to override the individual `handle_*_end` methods rather than this one.
    If you need specific behavior for all part end events, make sure you call the super method.

    Args:
        event: The part end event.
    """
    part = event.part
    next_part_kind = event.next_part_kind
    match part:
        case TextPart():
            async for e in self.handle_text_end(part, followed_by_text=next_part_kind == 'text'):
                yield e
        case ThinkingPart():
            async for e in self.handle_thinking_end(part, followed_by_thinking=next_part_kind == 'thinking'):
                yield e
        case ToolCallPart():
            async for e in self.handle_tool_call_end(part):
                yield e
        case BuiltinToolCallPart():
            async for e in self.handle_builtin_tool_call_end(part):
                yield e
        case BuiltinToolReturnPart() | FilePart():  # pragma: no cover
            # These don't have deltas, so they don't need to be ended.
            pass
```

#### before_stream

```python
before_stream() -> AsyncIterator[EventT]
```

Yield events before agent streaming starts.

This hook is called before any agent events are processed. Override this to inject custom events at the start of the stream.

Source code in `pydantic_ai_slim/pydantic_ai/ui/_event_stream.py`

```python
async def before_stream(self) -> AsyncIterator[EventT]:
    """Yield events before agent streaming starts.

    This hook is called before any agent events are processed.
    Override this to inject custom events at the start of the stream.
    """
    return  # pragma: no cover
    yield  # Make this an async generator
```

#### after_stream

```python
after_stream() -> AsyncIterator[EventT]
```

Yield events after agent streaming completes.

This hook is called after all agent events have been processed. Override this to inject custom events at the end of the stream.

Source code in `pydantic_ai_slim/pydantic_ai/ui/_event_stream.py`

```python
async def after_stream(self) -> AsyncIterator[EventT]:
    """Yield events after agent streaming completes.

    This hook is called after all agent events have been processed.
    Override this to inject custom events at the end of the stream.
    """
    return  # pragma: no cover
    yield  # Make this an async generator
```

#### on_error

```python
on_error(error: Exception) -> AsyncIterator[EventT]
```

Handle errors that occur during streaming.

Parameters:

| Name    | Type        | Description                               | Default    |
| ------- | ----------- | ----------------------------------------- | ---------- |
| `error` | `Exception` | The error that occurred during streaming. | *required* |

Source code in `pydantic_ai_slim/pydantic_ai/ui/_event_stream.py`

```python
async def on_error(self, error: Exception) -> AsyncIterator[EventT]:
    """Handle errors that occur during streaming.

    Args:
        error: The error that occurred during streaming.
    """
    return  # pragma: no cover
    yield  # Make this an async generator
```

#### before_request

```python
before_request() -> AsyncIterator[EventT]
```

Yield events before a model request is processed.

Override this to inject custom events at the start of the request.

Source code in `pydantic_ai_slim/pydantic_ai/ui/_event_stream.py`

```python
async def before_request(self) -> AsyncIterator[EventT]:
    """Yield events before a model request is processed.

    Override this to inject custom events at the start of the request.
    """
    return  # pragma: lax no cover
    yield  # Make this an async generator
```

#### after_request

```python
after_request() -> AsyncIterator[EventT]
```

Yield events after a model request is processed.

Override this to inject custom events at the end of the request.

Source code in `pydantic_ai_slim/pydantic_ai/ui/_event_stream.py`

```python
async def after_request(self) -> AsyncIterator[EventT]:
    """Yield events after a model request is processed.

    Override this to inject custom events at the end of the request.
    """
    return  # pragma: lax no cover
    yield  # Make this an async generator
```

#### before_response

```python
before_response() -> AsyncIterator[EventT]
```

Yield events before a model response is processed.

Override this to inject custom events at the start of the response.

Source code in `pydantic_ai_slim/pydantic_ai/ui/_event_stream.py`

```python
async def before_response(self) -> AsyncIterator[EventT]:
    """Yield events before a model response is processed.

    Override this to inject custom events at the start of the response.
    """
    return  # pragma: no cover
    yield  # Make this an async generator
```

#### after_response

```python
after_response() -> AsyncIterator[EventT]
```

Yield events after a model response is processed.

Override this to inject custom events at the end of the response.

Source code in `pydantic_ai_slim/pydantic_ai/ui/_event_stream.py`

```python
async def after_response(self) -> AsyncIterator[EventT]:
    """Yield events after a model response is processed.

    Override this to inject custom events at the end of the response.
    """
    return  # pragma: lax no cover
    yield  # Make this an async generator
```

#### handle_text_start

```python
handle_text_start(
    part: TextPart, follows_text: bool = False
) -> AsyncIterator[EventT]
```

Handle the start of a `TextPart`.

Parameters:

| Name           | Type       | Description                                                                                                                                           | Default    |
| -------------- | ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| `part`         | `TextPart` | The text part.                                                                                                                                        | *required* |
| `follows_text` | `bool`     | Whether the part is directly preceded by another text part. In this case, you may want to yield a "text-delta" event instead of a "text-start" event. | `False`    |

Source code in `pydantic_ai_slim/pydantic_ai/ui/_event_stream.py`

```python
async def handle_text_start(self, part: TextPart, follows_text: bool = False) -> AsyncIterator[EventT]:
    """Handle the start of a `TextPart`.

    Args:
        part: The text part.
        follows_text: Whether the part is directly preceded by another text part. In this case, you may want to yield a "text-delta" event instead of a "text-start" event.
    """
    return  # pragma: no cover
    yield  # Make this an async generator
```

#### handle_text_delta

```python
handle_text_delta(
    delta: TextPartDelta,
) -> AsyncIterator[EventT]
```

Handle a `TextPartDelta`.

Parameters:

| Name    | Type            | Description          | Default    |
| ------- | --------------- | -------------------- | ---------- |
| `delta` | `TextPartDelta` | The text part delta. | *required* |

Source code in `pydantic_ai_slim/pydantic_ai/ui/_event_stream.py`

```python
async def handle_text_delta(self, delta: TextPartDelta) -> AsyncIterator[EventT]:
    """Handle a `TextPartDelta`.

    Args:
        delta: The text part delta.
    """
    return  # pragma: no cover
    yield  # Make this an async generator
```

#### handle_text_end

```python
handle_text_end(
    part: TextPart, followed_by_text: bool = False
) -> AsyncIterator[EventT]
```

Handle the end of a `TextPart`.

Parameters:

| Name               | Type       | Description                                                                                                                 | Default    |
| ------------------ | ---------- | --------------------------------------------------------------------------------------------------------------------------- | ---------- |
| `part`             | `TextPart` | The text part.                                                                                                              | *required* |
| `followed_by_text` | `bool`     | Whether the part is directly followed by another text part. In this case, you may not want to yield a "text-end" event yet. | `False`    |

Source code in `pydantic_ai_slim/pydantic_ai/ui/_event_stream.py`

```python
async def handle_text_end(self, part: TextPart, followed_by_text: bool = False) -> AsyncIterator[EventT]:
    """Handle the end of a `TextPart`.

    Args:
        part: The text part.
        followed_by_text: Whether the part is directly followed by another text part. In this case, you may not want to yield a "text-end" event yet.
    """
    return  # pragma: no cover
    yield  # Make this an async generator
```

#### handle_thinking_start

```python
handle_thinking_start(
    part: ThinkingPart, follows_thinking: bool = False
) -> AsyncIterator[EventT]
```

Handle the start of a `ThinkingPart`.

Parameters:

| Name               | Type           | Description                                                                                                                                                       | Default    |
| ------------------ | -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| `part`             | `ThinkingPart` | The thinking part.                                                                                                                                                | *required* |
| `follows_thinking` | `bool`         | Whether the part is directly preceded by another thinking part. In this case, you may want to yield a "thinking-delta" event instead of a "thinking-start" event. | `False`    |

Source code in `pydantic_ai_slim/pydantic_ai/ui/_event_stream.py`

```python
async def handle_thinking_start(self, part: ThinkingPart, follows_thinking: bool = False) -> AsyncIterator[EventT]:
    """Handle the start of a `ThinkingPart`.

    Args:
        part: The thinking part.
        follows_thinking: Whether the part is directly preceded by another thinking part. In this case, you may want to yield a "thinking-delta" event instead of a "thinking-start" event.
    """
    return  # pragma: no cover
    yield  # Make this an async generator
```

#### handle_thinking_delta

```python
handle_thinking_delta(
    delta: ThinkingPartDelta,
) -> AsyncIterator[EventT]
```

Handle a `ThinkingPartDelta`.

Parameters:

| Name    | Type                | Description              | Default    |
| ------- | ------------------- | ------------------------ | ---------- |
| `delta` | `ThinkingPartDelta` | The thinking part delta. | *required* |

Source code in `pydantic_ai_slim/pydantic_ai/ui/_event_stream.py`

```python
async def handle_thinking_delta(self, delta: ThinkingPartDelta) -> AsyncIterator[EventT]:
    """Handle a `ThinkingPartDelta`.

    Args:
        delta: The thinking part delta.
    """
    return  # pragma: no cover
    yield  # Make this an async generator
```

#### handle_thinking_end

```python
handle_thinking_end(
    part: ThinkingPart, followed_by_thinking: bool = False
) -> AsyncIterator[EventT]
```

Handle the end of a `ThinkingPart`.

Parameters:

| Name                   | Type           | Description                                                                                                                         | Default    |
| ---------------------- | -------------- | ----------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| `part`                 | `ThinkingPart` | The thinking part.                                                                                                                  | *required* |
| `followed_by_thinking` | `bool`         | Whether the part is directly followed by another thinking part. In this case, you may not want to yield a "thinking-end" event yet. | `False`    |

Source code in `pydantic_ai_slim/pydantic_ai/ui/_event_stream.py`

```python
async def handle_thinking_end(
    self, part: ThinkingPart, followed_by_thinking: bool = False
) -> AsyncIterator[EventT]:
    """Handle the end of a `ThinkingPart`.

    Args:
        part: The thinking part.
        followed_by_thinking: Whether the part is directly followed by another thinking part. In this case, you may not want to yield a "thinking-end" event yet.
    """
    return  # pragma: no cover
    yield  # Make this an async generator
```

#### handle_tool_call_start

```python
handle_tool_call_start(
    part: ToolCallPart,
) -> AsyncIterator[EventT]
```

Handle the start of a `ToolCallPart`.

Parameters:

| Name   | Type           | Description         | Default    |
| ------ | -------------- | ------------------- | ---------- |
| `part` | `ToolCallPart` | The tool call part. | *required* |

Source code in `pydantic_ai_slim/pydantic_ai/ui/_event_stream.py`

```python
async def handle_tool_call_start(self, part: ToolCallPart) -> AsyncIterator[EventT]:
    """Handle the start of a `ToolCallPart`.

    Args:
        part: The tool call part.
    """
    return  # pragma: no cover
    yield  # Make this an async generator
```

#### handle_tool_call_delta

```python
handle_tool_call_delta(
    delta: ToolCallPartDelta,
) -> AsyncIterator[EventT]
```

Handle a `ToolCallPartDelta`.

Parameters:

| Name    | Type                | Description               | Default    |
| ------- | ------------------- | ------------------------- | ---------- |
| `delta` | `ToolCallPartDelta` | The tool call part delta. | *required* |

Source code in `pydantic_ai_slim/pydantic_ai/ui/_event_stream.py`

```python
async def handle_tool_call_delta(self, delta: ToolCallPartDelta) -> AsyncIterator[EventT]:
    """Handle a `ToolCallPartDelta`.

    Args:
        delta: The tool call part delta.
    """
    return  # pragma: no cover
    yield  # Make this an async generator
```

#### handle_tool_call_end

```python
handle_tool_call_end(
    part: ToolCallPart,
) -> AsyncIterator[EventT]
```

Handle the end of a `ToolCallPart`.

Parameters:

| Name   | Type           | Description         | Default    |
| ------ | -------------- | ------------------- | ---------- |
| `part` | `ToolCallPart` | The tool call part. | *required* |

Source code in `pydantic_ai_slim/pydantic_ai/ui/_event_stream.py`

```python
async def handle_tool_call_end(self, part: ToolCallPart) -> AsyncIterator[EventT]:
    """Handle the end of a `ToolCallPart`.

    Args:
        part: The tool call part.
    """
    return  # pragma: no cover
    yield  # Make this an async generator
```

#### handle_builtin_tool_call_start

```python
handle_builtin_tool_call_start(
    part: BuiltinToolCallPart,
) -> AsyncIterator[EventT]
```

Handle a `BuiltinToolCallPart` at start.

Parameters:

| Name   | Type                  | Description                 | Default    |
| ------ | --------------------- | --------------------------- | ---------- |
| `part` | `BuiltinToolCallPart` | The builtin tool call part. | *required* |

Source code in `pydantic_ai_slim/pydantic_ai/ui/_event_stream.py`

```python
async def handle_builtin_tool_call_start(self, part: BuiltinToolCallPart) -> AsyncIterator[EventT]:
    """Handle a `BuiltinToolCallPart` at start.

    Args:
        part: The builtin tool call part.
    """
    return  # pragma: no cover
    yield  # Make this an async generator
```

#### handle_builtin_tool_call_end

```python
handle_builtin_tool_call_end(
    part: BuiltinToolCallPart,
) -> AsyncIterator[EventT]
```

Handle the end of a `BuiltinToolCallPart`.

Parameters:

| Name   | Type                  | Description                 | Default    |
| ------ | --------------------- | --------------------------- | ---------- |
| `part` | `BuiltinToolCallPart` | The builtin tool call part. | *required* |

Source code in `pydantic_ai_slim/pydantic_ai/ui/_event_stream.py`

```python
async def handle_builtin_tool_call_end(self, part: BuiltinToolCallPart) -> AsyncIterator[EventT]:
    """Handle the end of a `BuiltinToolCallPart`.

    Args:
        part: The builtin tool call part.
    """
    return  # pragma: no cover
    yield  # Make this an async generator
```

#### handle_builtin_tool_return

```python
handle_builtin_tool_return(
    part: BuiltinToolReturnPart,
) -> AsyncIterator[EventT]
```

Handle a `BuiltinToolReturnPart`.

Parameters:

| Name   | Type                    | Description                   | Default    |
| ------ | ----------------------- | ----------------------------- | ---------- |
| `part` | `BuiltinToolReturnPart` | The builtin tool return part. | *required* |

Source code in `pydantic_ai_slim/pydantic_ai/ui/_event_stream.py`

```python
async def handle_builtin_tool_return(self, part: BuiltinToolReturnPart) -> AsyncIterator[EventT]:
    """Handle a `BuiltinToolReturnPart`.

    Args:
        part: The builtin tool return part.
    """
    return  # pragma: no cover
    yield  # Make this an async generator
```

#### handle_file

```python
handle_file(part: FilePart) -> AsyncIterator[EventT]
```

Handle a `FilePart`.

Parameters:

| Name   | Type       | Description    | Default    |
| ------ | ---------- | -------------- | ---------- |
| `part` | `FilePart` | The file part. | *required* |

Source code in `pydantic_ai_slim/pydantic_ai/ui/_event_stream.py`

```python
async def handle_file(self, part: FilePart) -> AsyncIterator[EventT]:
    """Handle a `FilePart`.

    Args:
        part: The file part.
    """
    return  # pragma: no cover
    yield  # Make this an async generator
```

#### handle_final_result

```python
handle_final_result(
    event: FinalResultEvent,
) -> AsyncIterator[EventT]
```

Handle a `FinalResultEvent`.

Parameters:

| Name    | Type               | Description             | Default    |
| ------- | ------------------ | ----------------------- | ---------- |
| `event` | `FinalResultEvent` | The final result event. | *required* |

Source code in `pydantic_ai_slim/pydantic_ai/ui/_event_stream.py`

```python
async def handle_final_result(self, event: FinalResultEvent) -> AsyncIterator[EventT]:
    """Handle a `FinalResultEvent`.

    Args:
        event: The final result event.
    """
    return
    yield  # Make this an async generator
```

#### handle_function_tool_call

```python
handle_function_tool_call(
    event: FunctionToolCallEvent,
) -> AsyncIterator[EventT]
```

Handle a `FunctionToolCallEvent`.

Parameters:

| Name    | Type                    | Description                   | Default    |
| ------- | ----------------------- | ----------------------------- | ---------- |
| `event` | `FunctionToolCallEvent` | The function tool call event. | *required* |

Source code in `pydantic_ai_slim/pydantic_ai/ui/_event_stream.py`

```python
async def handle_function_tool_call(self, event: FunctionToolCallEvent) -> AsyncIterator[EventT]:
    """Handle a `FunctionToolCallEvent`.

    Args:
        event: The function tool call event.
    """
    return
    yield  # Make this an async generator
```

#### handle_function_tool_result

```python
handle_function_tool_result(
    event: FunctionToolResultEvent,
) -> AsyncIterator[EventT]
```

Handle a `FunctionToolResultEvent`.

Parameters:

| Name    | Type                      | Description                     | Default    |
| ------- | ------------------------- | ------------------------------- | ---------- |
| `event` | `FunctionToolResultEvent` | The function tool result event. | *required* |

Source code in `pydantic_ai_slim/pydantic_ai/ui/_event_stream.py`

```python
async def handle_function_tool_result(self, event: FunctionToolResultEvent) -> AsyncIterator[EventT]:
    """Handle a `FunctionToolResultEvent`.

    Args:
        event: The function tool result event.
    """
    return  # pragma: no cover
    yield  # Make this an async generator
```

#### handle_run_result

```python
handle_run_result(
    event: AgentRunResultEvent,
) -> AsyncIterator[EventT]
```

Handle an `AgentRunResultEvent`.

Parameters:

| Name    | Type                  | Description                 | Default    |
| ------- | --------------------- | --------------------------- | ---------- |
| `event` | `AgentRunResultEvent` | The agent run result event. | *required* |

Source code in `pydantic_ai_slim/pydantic_ai/ui/_event_stream.py`

```python
async def handle_run_result(self, event: AgentRunResultEvent) -> AsyncIterator[EventT]:
    """Handle an `AgentRunResultEvent`.

    Args:
        event: The agent run result event.
    """
    return
    yield  # Make this an async generator
```

### MessagesBuilder

Helper class to build Pydantic AI messages from request/response parts.

Source code in `pydantic_ai_slim/pydantic_ai/ui/_messages_builder.py`

```python
@dataclass
class MessagesBuilder:
    """Helper class to build Pydantic AI messages from request/response parts."""

    messages: list[ModelMessage] = field(default_factory=list[ModelMessage])

    def add(self, part: ModelRequestPart | ModelResponsePart) -> None:
        """Add a new part, creating a new request or response message if necessary."""
        last_message = self.messages[-1] if self.messages else None
        if isinstance(part, get_union_args(ModelRequestPart)):
            part = cast(ModelRequestPart, part)
            if isinstance(last_message, ModelRequest):
                last_message.parts = [*last_message.parts, part]
            else:
                self.messages.append(ModelRequest(parts=[part]))
        else:
            part = cast(ModelResponsePart, part)
            if isinstance(last_message, ModelResponse):
                last_message.parts = [*last_message.parts, part]
            else:
                self.messages.append(ModelResponse(parts=[part]))
```

#### add

```python
add(part: ModelRequestPart | ModelResponsePart) -> None
```

Add a new part, creating a new request or response message if necessary.

Source code in `pydantic_ai_slim/pydantic_ai/ui/_messages_builder.py`

```python
def add(self, part: ModelRequestPart | ModelResponsePart) -> None:
    """Add a new part, creating a new request or response message if necessary."""
    last_message = self.messages[-1] if self.messages else None
    if isinstance(part, get_union_args(ModelRequestPart)):
        part = cast(ModelRequestPart, part)
        if isinstance(last_message, ModelRequest):
            last_message.parts = [*last_message.parts, part]
        else:
            self.messages.append(ModelRequest(parts=[part]))
    else:
        part = cast(ModelResponsePart, part)
        if isinstance(last_message, ModelResponse):
            last_message.parts = [*last_message.parts, part]
        else:
            self.messages.append(ModelResponse(parts=[part]))
```
