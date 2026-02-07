# `pydantic_ai.ui.ag_ui`

AG-UI protocol integration for Pydantic AI agents.

### AGUIAdapter

Bases: `UIAdapter[RunAgentInput, Message, BaseEvent, AgentDepsT, OutputDataT]`

UI adapter for the Agent-User Interaction (AG-UI) protocol.

Source code in `pydantic_ai_slim/pydantic_ai/ui/ag_ui/_adapter.py`

```python
class AGUIAdapter(UIAdapter[RunAgentInput, Message, BaseEvent, AgentDepsT, OutputDataT]):
    """UI adapter for the Agent-User Interaction (AG-UI) protocol."""

    @classmethod
    def build_run_input(cls, body: bytes) -> RunAgentInput:
        """Build an AG-UI run input object from the request body."""
        return RunAgentInput.model_validate_json(body)

    def build_event_stream(self) -> UIEventStream[RunAgentInput, BaseEvent, AgentDepsT, OutputDataT]:
        """Build an AG-UI event stream transformer."""
        return AGUIEventStream(self.run_input, accept=self.accept)

    @cached_property
    def messages(self) -> list[ModelMessage]:
        """Pydantic AI messages from the AG-UI run input."""
        return self.load_messages(self.run_input.messages)

    @cached_property
    def toolset(self) -> AbstractToolset[AgentDepsT] | None:
        """Toolset representing frontend tools from the AG-UI run input."""
        if self.run_input.tools:
            return _AGUIFrontendToolset[AgentDepsT](self.run_input.tools)
        return None

    @cached_property
    def state(self) -> dict[str, Any] | None:
        """Frontend state from the AG-UI run input."""
        state = self.run_input.state
        if state is None:
            return None

        if isinstance(state, Mapping) and not state:
            return None

        return cast('dict[str, Any]', state)

    @classmethod
    def load_messages(cls, messages: Sequence[Message]) -> list[ModelMessage]:  # noqa: C901
        """Transform AG-UI messages into Pydantic AI messages."""
        builder = MessagesBuilder()
        tool_calls: dict[str, str] = {}  # Tool call ID to tool name mapping.
        for msg in messages:
            match msg:
                case UserMessage(content=content):
                    if isinstance(content, str):
                        builder.add(UserPromptPart(content=content))
                    else:
                        user_prompt_content: list[Any] = []
                        for part in content:
                            match part:
                                case TextInputContent(text=text):
                                    user_prompt_content.append(text)
                                case BinaryInputContent():
                                    if part.url:
                                        try:
                                            binary_part = BinaryContent.from_data_uri(part.url)
                                        except ValueError:
                                            media_type_constructors = {
                                                'image': ImageUrl,
                                                'video': VideoUrl,
                                                'audio': AudioUrl,
                                            }
                                            media_type_prefix = part.mime_type.split('/', 1)[0]
                                            constructor = media_type_constructors.get(media_type_prefix, DocumentUrl)
                                            binary_part = constructor(url=part.url, media_type=part.mime_type)
                                    elif part.data:
                                        binary_part = BinaryContent(
                                            data=b64decode(part.data), media_type=part.mime_type
                                        )
                                    else:  # pragma: no cover
                                        raise ValueError('BinaryInputContent must have either a `url` or `data` field.')
                                    user_prompt_content.append(binary_part)
                                case _:  # pragma: no cover
                                    raise ValueError(f'Unsupported user message part type: {type(part)}')

                        if user_prompt_content:  # pragma: no branch
                            content_to_add = (
                                user_prompt_content[0]
                                if len(user_prompt_content) == 1 and isinstance(user_prompt_content[0], str)
                                else user_prompt_content
                            )
                            builder.add(UserPromptPart(content=content_to_add))

                case SystemMessage(content=content) | DeveloperMessage(content=content):
                    builder.add(SystemPromptPart(content=content))

                case AssistantMessage(content=content, tool_calls=tool_calls_list):
                    if content:
                        builder.add(TextPart(content=content))
                    if tool_calls_list:
                        for tool_call in tool_calls_list:
                            tool_call_id = tool_call.id
                            tool_name = tool_call.function.name
                            tool_calls[tool_call_id] = tool_name

                            if tool_call_id.startswith(BUILTIN_TOOL_CALL_ID_PREFIX):
                                _, provider_name, original_id = tool_call_id.split('|', 2)
                                builder.add(
                                    BuiltinToolCallPart(
                                        tool_name=tool_name,
                                        args=tool_call.function.arguments,
                                        tool_call_id=original_id,
                                        provider_name=provider_name,
                                    )
                                )
                            else:
                                builder.add(
                                    ToolCallPart(
                                        tool_name=tool_name,
                                        tool_call_id=tool_call_id,
                                        args=tool_call.function.arguments,
                                    )
                                )
                case ToolMessage() as tool_msg:
                    tool_call_id = tool_msg.tool_call_id
                    tool_name = tool_calls.get(tool_call_id)
                    if tool_name is None:  # pragma: no cover
                        raise ValueError(f'Tool call with ID {tool_call_id} not found in the history.')

                    if tool_call_id.startswith(BUILTIN_TOOL_CALL_ID_PREFIX):
                        _, provider_name, original_id = tool_call_id.split('|', 2)
                        builder.add(
                            BuiltinToolReturnPart(
                                tool_name=tool_name,
                                content=tool_msg.content,
                                tool_call_id=original_id,
                                provider_name=provider_name,
                            )
                        )
                    else:
                        builder.add(
                            ToolReturnPart(
                                tool_name=tool_name,
                                content=tool_msg.content,
                                tool_call_id=tool_call_id,
                            )
                        )

                case ActivityMessage():
                    pass

        return builder.messages
```

#### build_run_input

```python
build_run_input(body: bytes) -> RunAgentInput
```

Build an AG-UI run input object from the request body.

Source code in `pydantic_ai_slim/pydantic_ai/ui/ag_ui/_adapter.py`

```python
@classmethod
def build_run_input(cls, body: bytes) -> RunAgentInput:
    """Build an AG-UI run input object from the request body."""
    return RunAgentInput.model_validate_json(body)
```

#### build_event_stream

```python
build_event_stream() -> (
    UIEventStream[
        RunAgentInput, BaseEvent, AgentDepsT, OutputDataT
    ]
)
```

Build an AG-UI event stream transformer.

Source code in `pydantic_ai_slim/pydantic_ai/ui/ag_ui/_adapter.py`

```python
def build_event_stream(self) -> UIEventStream[RunAgentInput, BaseEvent, AgentDepsT, OutputDataT]:
    """Build an AG-UI event stream transformer."""
    return AGUIEventStream(self.run_input, accept=self.accept)
```

#### messages

```python
messages: list[ModelMessage]
```

Pydantic AI messages from the AG-UI run input.

#### toolset

```python
toolset: AbstractToolset[AgentDepsT] | None
```

Toolset representing frontend tools from the AG-UI run input.

#### state

```python
state: dict[str, Any] | None
```

Frontend state from the AG-UI run input.

#### load_messages

```python
load_messages(
    messages: Sequence[Message],
) -> list[ModelMessage]
```

Transform AG-UI messages into Pydantic AI messages.

Source code in `pydantic_ai_slim/pydantic_ai/ui/ag_ui/_adapter.py`

```python
@classmethod
def load_messages(cls, messages: Sequence[Message]) -> list[ModelMessage]:  # noqa: C901
    """Transform AG-UI messages into Pydantic AI messages."""
    builder = MessagesBuilder()
    tool_calls: dict[str, str] = {}  # Tool call ID to tool name mapping.
    for msg in messages:
        match msg:
            case UserMessage(content=content):
                if isinstance(content, str):
                    builder.add(UserPromptPart(content=content))
                else:
                    user_prompt_content: list[Any] = []
                    for part in content:
                        match part:
                            case TextInputContent(text=text):
                                user_prompt_content.append(text)
                            case BinaryInputContent():
                                if part.url:
                                    try:
                                        binary_part = BinaryContent.from_data_uri(part.url)
                                    except ValueError:
                                        media_type_constructors = {
                                            'image': ImageUrl,
                                            'video': VideoUrl,
                                            'audio': AudioUrl,
                                        }
                                        media_type_prefix = part.mime_type.split('/', 1)[0]
                                        constructor = media_type_constructors.get(media_type_prefix, DocumentUrl)
                                        binary_part = constructor(url=part.url, media_type=part.mime_type)
                                elif part.data:
                                    binary_part = BinaryContent(
                                        data=b64decode(part.data), media_type=part.mime_type
                                    )
                                else:  # pragma: no cover
                                    raise ValueError('BinaryInputContent must have either a `url` or `data` field.')
                                user_prompt_content.append(binary_part)
                            case _:  # pragma: no cover
                                raise ValueError(f'Unsupported user message part type: {type(part)}')

                    if user_prompt_content:  # pragma: no branch
                        content_to_add = (
                            user_prompt_content[0]
                            if len(user_prompt_content) == 1 and isinstance(user_prompt_content[0], str)
                            else user_prompt_content
                        )
                        builder.add(UserPromptPart(content=content_to_add))

            case SystemMessage(content=content) | DeveloperMessage(content=content):
                builder.add(SystemPromptPart(content=content))

            case AssistantMessage(content=content, tool_calls=tool_calls_list):
                if content:
                    builder.add(TextPart(content=content))
                if tool_calls_list:
                    for tool_call in tool_calls_list:
                        tool_call_id = tool_call.id
                        tool_name = tool_call.function.name
                        tool_calls[tool_call_id] = tool_name

                        if tool_call_id.startswith(BUILTIN_TOOL_CALL_ID_PREFIX):
                            _, provider_name, original_id = tool_call_id.split('|', 2)
                            builder.add(
                                BuiltinToolCallPart(
                                    tool_name=tool_name,
                                    args=tool_call.function.arguments,
                                    tool_call_id=original_id,
                                    provider_name=provider_name,
                                )
                            )
                        else:
                            builder.add(
                                ToolCallPart(
                                    tool_name=tool_name,
                                    tool_call_id=tool_call_id,
                                    args=tool_call.function.arguments,
                                )
                            )
            case ToolMessage() as tool_msg:
                tool_call_id = tool_msg.tool_call_id
                tool_name = tool_calls.get(tool_call_id)
                if tool_name is None:  # pragma: no cover
                    raise ValueError(f'Tool call with ID {tool_call_id} not found in the history.')

                if tool_call_id.startswith(BUILTIN_TOOL_CALL_ID_PREFIX):
                    _, provider_name, original_id = tool_call_id.split('|', 2)
                    builder.add(
                        BuiltinToolReturnPart(
                            tool_name=tool_name,
                            content=tool_msg.content,
                            tool_call_id=original_id,
                            provider_name=provider_name,
                        )
                    )
                else:
                    builder.add(
                        ToolReturnPart(
                            tool_name=tool_name,
                            content=tool_msg.content,
                            tool_call_id=tool_call_id,
                        )
                    )

            case ActivityMessage():
                pass

    return builder.messages
```

### AGUIEventStream

Bases: `UIEventStream[RunAgentInput, BaseEvent, AgentDepsT, OutputDataT]`

UI event stream transformer for the Agent-User Interaction (AG-UI) protocol.

Source code in `pydantic_ai_slim/pydantic_ai/ui/ag_ui/_event_stream.py`

```python
@dataclass
class AGUIEventStream(UIEventStream[RunAgentInput, BaseEvent, AgentDepsT, OutputDataT]):
    """UI event stream transformer for the Agent-User Interaction (AG-UI) protocol."""

    _thinking_text: bool = False
    _builtin_tool_call_ids: dict[str, str] = field(default_factory=dict[str, str])
    _error: bool = False

    @property
    def _event_encoder(self) -> EventEncoder:
        return EventEncoder(accept=self.accept or SSE_CONTENT_TYPE)

    @property
    def content_type(self) -> str:
        return self._event_encoder.get_content_type()

    def encode_event(self, event: BaseEvent) -> str:
        return self._event_encoder.encode(event)

    @staticmethod
    def _get_timestamp() -> int:
        return int(now_utc().timestamp() * 1_000)

    async def handle_event(self, event: NativeEvent) -> AsyncIterator[BaseEvent]:
        """Override to set timestamps on all AG-UI events."""
        async for agui_event in super().handle_event(event):
            if agui_event.timestamp is None:
                agui_event.timestamp = self._get_timestamp()
            yield agui_event

    async def before_stream(self) -> AsyncIterator[BaseEvent]:
        yield RunStartedEvent(
            thread_id=self.run_input.thread_id,
            run_id=self.run_input.run_id,
            timestamp=self._get_timestamp(),
        )

    async def before_response(self) -> AsyncIterator[BaseEvent]:
        # Prevent parts from a subsequent response being tied to parts from an earlier response.
        # See https://github.com/pydantic/pydantic-ai/issues/3316
        self.new_message_id()
        return
        yield  # Make this an async generator

    async def after_stream(self) -> AsyncIterator[BaseEvent]:
        if not self._error:
            yield RunFinishedEvent(
                thread_id=self.run_input.thread_id,
                run_id=self.run_input.run_id,
                timestamp=self._get_timestamp(),
            )

    async def on_error(self, error: Exception) -> AsyncIterator[BaseEvent]:
        self._error = True
        yield RunErrorEvent(message=str(error), timestamp=self._get_timestamp())

    async def handle_text_start(self, part: TextPart, follows_text: bool = False) -> AsyncIterator[BaseEvent]:
        if follows_text:
            message_id = self.message_id
        else:
            message_id = self.new_message_id()
            yield TextMessageStartEvent(message_id=message_id)

        if part.content:  # pragma: no branch
            yield TextMessageContentEvent(message_id=message_id, delta=part.content)

    async def handle_text_delta(self, delta: TextPartDelta) -> AsyncIterator[BaseEvent]:
        if delta.content_delta:  # pragma: no branch
            yield TextMessageContentEvent(message_id=self.message_id, delta=delta.content_delta)

    async def handle_text_end(self, part: TextPart, followed_by_text: bool = False) -> AsyncIterator[BaseEvent]:
        if not followed_by_text:
            yield TextMessageEndEvent(message_id=self.message_id)

    async def handle_thinking_start(
        self, part: ThinkingPart, follows_thinking: bool = False
    ) -> AsyncIterator[BaseEvent]:
        if not follows_thinking:
            yield ThinkingStartEvent(type=EventType.THINKING_START)

        if part.content:
            yield ThinkingTextMessageStartEvent(type=EventType.THINKING_TEXT_MESSAGE_START)
            yield ThinkingTextMessageContentEvent(type=EventType.THINKING_TEXT_MESSAGE_CONTENT, delta=part.content)
            self._thinking_text = True

    async def handle_thinking_delta(self, delta: ThinkingPartDelta) -> AsyncIterator[BaseEvent]:
        if not delta.content_delta:
            return  # pragma: no cover

        if not self._thinking_text:
            yield ThinkingTextMessageStartEvent(type=EventType.THINKING_TEXT_MESSAGE_START)
            self._thinking_text = True

        yield ThinkingTextMessageContentEvent(type=EventType.THINKING_TEXT_MESSAGE_CONTENT, delta=delta.content_delta)

    async def handle_thinking_end(
        self, part: ThinkingPart, followed_by_thinking: bool = False
    ) -> AsyncIterator[BaseEvent]:
        if self._thinking_text:
            yield ThinkingTextMessageEndEvent(type=EventType.THINKING_TEXT_MESSAGE_END)
            self._thinking_text = False

        if not followed_by_thinking:
            yield ThinkingEndEvent(type=EventType.THINKING_END)

    def handle_tool_call_start(self, part: ToolCallPart | BuiltinToolCallPart) -> AsyncIterator[BaseEvent]:
        return self._handle_tool_call_start(part)

    def handle_builtin_tool_call_start(self, part: BuiltinToolCallPart) -> AsyncIterator[BaseEvent]:
        tool_call_id = part.tool_call_id
        builtin_tool_call_id = '|'.join([BUILTIN_TOOL_CALL_ID_PREFIX, part.provider_name or '', tool_call_id])
        self._builtin_tool_call_ids[tool_call_id] = builtin_tool_call_id
        tool_call_id = builtin_tool_call_id

        return self._handle_tool_call_start(part, tool_call_id)

    async def _handle_tool_call_start(
        self, part: ToolCallPart | BuiltinToolCallPart, tool_call_id: str | None = None
    ) -> AsyncIterator[BaseEvent]:
        tool_call_id = tool_call_id or part.tool_call_id
        parent_message_id = self.message_id

        yield ToolCallStartEvent(
            tool_call_id=tool_call_id, tool_call_name=part.tool_name, parent_message_id=parent_message_id
        )
        if part.args:
            yield ToolCallArgsEvent(tool_call_id=tool_call_id, delta=part.args_as_json_str())

    async def handle_tool_call_delta(self, delta: ToolCallPartDelta) -> AsyncIterator[BaseEvent]:
        tool_call_id = delta.tool_call_id
        assert tool_call_id, '`ToolCallPartDelta.tool_call_id` must be set'
        if tool_call_id in self._builtin_tool_call_ids:
            tool_call_id = self._builtin_tool_call_ids[tool_call_id]
        yield ToolCallArgsEvent(
            tool_call_id=tool_call_id,
            delta=delta.args_delta if isinstance(delta.args_delta, str) else json.dumps(delta.args_delta),
        )

    async def handle_tool_call_end(self, part: ToolCallPart) -> AsyncIterator[BaseEvent]:
        yield ToolCallEndEvent(tool_call_id=part.tool_call_id)

    async def handle_builtin_tool_call_end(self, part: BuiltinToolCallPart) -> AsyncIterator[BaseEvent]:
        yield ToolCallEndEvent(tool_call_id=self._builtin_tool_call_ids[part.tool_call_id])

    async def handle_builtin_tool_return(self, part: BuiltinToolReturnPart) -> AsyncIterator[BaseEvent]:
        tool_call_id = self._builtin_tool_call_ids[part.tool_call_id]
        yield ToolCallResultEvent(
            message_id=self.new_message_id(),
            type=EventType.TOOL_CALL_RESULT,
            role='tool',
            tool_call_id=tool_call_id,
            content=part.model_response_str(),
        )

    async def handle_function_tool_result(self, event: FunctionToolResultEvent) -> AsyncIterator[BaseEvent]:
        result = event.result
        output = result.model_response() if isinstance(result, RetryPromptPart) else result.model_response_str()

        yield ToolCallResultEvent(
            message_id=self.new_message_id(),
            type=EventType.TOOL_CALL_RESULT,
            role='tool',
            tool_call_id=result.tool_call_id,
            content=output,
        )

        # ToolCallResultEvent.content may hold user parts (e.g. text, images) that AG-UI does not currently have events for

        if isinstance(result, ToolReturnPart):
            # Check for AG-UI events returned by tool calls.
            possible_event = result.metadata or result.content
            if isinstance(possible_event, BaseEvent):
                yield possible_event
            elif isinstance(possible_event, str | bytes):  # pragma: no branch
                # Avoid iterable check for strings and bytes.
                pass
            elif isinstance(possible_event, Iterable):  # pragma: no branch
                for item in possible_event:  # type: ignore[reportUnknownMemberType]
                    if isinstance(item, BaseEvent):  # pragma: no branch
                        yield item
```

#### handle_event

```python
handle_event(
    event: NativeEvent,
) -> AsyncIterator[BaseEvent]
```

Override to set timestamps on all AG-UI events.

Source code in `pydantic_ai_slim/pydantic_ai/ui/ag_ui/_event_stream.py`

```python
async def handle_event(self, event: NativeEvent) -> AsyncIterator[BaseEvent]:
    """Override to set timestamps on all AG-UI events."""
    async for agui_event in super().handle_event(event):
        if agui_event.timestamp is None:
            agui_event.timestamp = self._get_timestamp()
        yield agui_event
```

AG-UI protocol integration for Pydantic AI agents.

### AGUIApp

Bases: `Generic[AgentDepsT, OutputDataT]`, `Starlette`

ASGI application for running Pydantic AI agents with AG-UI protocol support.

Source code in `pydantic_ai_slim/pydantic_ai/ui/ag_ui/app.py`

```python
class AGUIApp(Generic[AgentDepsT, OutputDataT], Starlette):
    """ASGI application for running Pydantic AI agents with AG-UI protocol support."""

    def __init__(
        self,
        agent: AbstractAgent[AgentDepsT, OutputDataT],
        *,
        # AGUIAdapter.dispatch_request parameters
        output_type: OutputSpec[Any] | None = None,
        message_history: Sequence[ModelMessage] | None = None,
        deferred_tool_results: DeferredToolResults | None = None,
        model: Model | KnownModelName | str | None = None,
        deps: AgentDepsT = None,
        model_settings: ModelSettings | None = None,
        usage_limits: UsageLimits | None = None,
        usage: RunUsage | None = None,
        infer_name: bool = True,
        toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
        builtin_tools: Sequence[AbstractBuiltinTool] | None = None,
        on_complete: OnCompleteFunc[Any] | None = None,
        # Starlette parameters
        debug: bool = False,
        routes: Sequence[BaseRoute] | None = None,
        middleware: Sequence[Middleware] | None = None,
        exception_handlers: Mapping[Any, ExceptionHandler] | None = None,
        on_startup: Sequence[Callable[[], Any]] | None = None,
        on_shutdown: Sequence[Callable[[], Any]] | None = None,
        lifespan: Lifespan[Self] | None = None,
    ) -> None:
        """An ASGI application that handles every request by running the agent and streaming the response.

        Note that the `deps` will be the same for each request, with the exception of the frontend state that's
        injected into the `state` field of a `deps` object that implements the [`StateHandler`][pydantic_ai.ui.StateHandler] protocol.
        To provide different `deps` for each request (e.g. based on the authenticated user),
        use [`AGUIAdapter.run_stream()`][pydantic_ai.ui.ag_ui.AGUIAdapter.run_stream] or
        [`AGUIAdapter.dispatch_request()`][pydantic_ai.ui.ag_ui.AGUIAdapter.dispatch_request] instead.

        Args:
            agent: The agent to run.

            output_type: Custom output type to use for this run, `output_type` may only be used if the agent has
                no output validators since output validators would expect an argument that matches the agent's
                output type.
            message_history: History of the conversation so far.
            deferred_tool_results: Optional results for deferred tool calls in the message history.
            model: Optional model to use for this run, required if `model` was not set when creating the agent.
            deps: Optional dependencies to use for this run.
            model_settings: Optional settings to use for this model's request.
            usage_limits: Optional limits on model request count or token usage.
            usage: Optional usage to start with, useful for resuming a conversation or agents used in tools.
            infer_name: Whether to try to infer the agent name from the call frame if it's not set.
            toolsets: Optional additional toolsets for this run.
            builtin_tools: Optional additional builtin tools for this run.
            on_complete: Optional callback function called when the agent run completes successfully.
                The callback receives the completed [`AgentRunResult`][pydantic_ai.agent.AgentRunResult] and can access `all_messages()` and other result data.

            debug: Boolean indicating if debug tracebacks should be returned on errors.
            routes: A list of routes to serve incoming HTTP and WebSocket requests.
            middleware: A list of middleware to run for every request. A starlette application will always
                automatically include two middleware classes. `ServerErrorMiddleware` is added as the very
                outermost middleware, to handle any uncaught errors occurring anywhere in the entire stack.
                `ExceptionMiddleware` is added as the very innermost middleware, to deal with handled
                exception cases occurring in the routing or endpoints.
            exception_handlers: A mapping of either integer status codes, or exception class types onto
                callables which handle the exceptions. Exception handler callables should be of the form
                `handler(request, exc) -> response` and may be either standard functions, or async functions.
            on_startup: A list of callables to run on application startup. Startup handler callables do not
                take any arguments, and may be either standard functions, or async functions.
            on_shutdown: A list of callables to run on application shutdown. Shutdown handler callables do
                not take any arguments, and may be either standard functions, or async functions.
            lifespan: A lifespan context function, which can be used to perform startup and shutdown tasks.
                This is a newer style that replaces the `on_startup` and `on_shutdown` handlers. Use one or
                the other, not both.
        """
        super().__init__(
            debug=debug,
            routes=routes,
            middleware=middleware,
            exception_handlers=exception_handlers,
            on_startup=on_startup,
            on_shutdown=on_shutdown,
            lifespan=lifespan,
        )

        async def run_agent(request: Request) -> Response:
            """Endpoint to run the agent with the provided input data."""
            # `dispatch_request` will store the frontend state from the request on `deps.state` (if it implements the `StateHandler` protocol),
            # so we need to copy the deps to avoid different requests mutating the same deps object.
            nonlocal deps
            if isinstance(deps, StateHandler):  # pragma: no branch
                deps = replace(deps)

            return await AGUIAdapter[AgentDepsT, OutputDataT].dispatch_request(
                request,
                agent=agent,
                output_type=output_type,
                message_history=message_history,
                deferred_tool_results=deferred_tool_results,
                model=model,
                deps=deps,
                model_settings=model_settings,
                usage_limits=usage_limits,
                usage=usage,
                infer_name=infer_name,
                toolsets=toolsets,
                builtin_tools=builtin_tools,
                on_complete=on_complete,
            )

        self.router.add_route('/', run_agent, methods=['POST'])
```

#### __init__

```python
__init__(
    agent: AbstractAgent[AgentDepsT, OutputDataT],
    *,
    output_type: OutputSpec[Any] | None = None,
    message_history: Sequence[ModelMessage] | None = None,
    deferred_tool_results: (
        DeferredToolResults | None
    ) = None,
    model: Model | KnownModelName | str | None = None,
    deps: AgentDepsT = None,
    model_settings: ModelSettings | None = None,
    usage_limits: UsageLimits | None = None,
    usage: RunUsage | None = None,
    infer_name: bool = True,
    toolsets: (
        Sequence[AbstractToolset[AgentDepsT]] | None
    ) = None,
    builtin_tools: (
        Sequence[AbstractBuiltinTool] | None
    ) = None,
    on_complete: OnCompleteFunc[Any] | None = None,
    debug: bool = False,
    routes: Sequence[BaseRoute] | None = None,
    middleware: Sequence[Middleware] | None = None,
    exception_handlers: (
        Mapping[Any, ExceptionHandler] | None
    ) = None,
    on_startup: Sequence[Callable[[], Any]] | None = None,
    on_shutdown: Sequence[Callable[[], Any]] | None = None,
    lifespan: Lifespan[Self] | None = None
) -> None
```

An ASGI application that handles every request by running the agent and streaming the response.

Note that the `deps` will be the same for each request, with the exception of the frontend state that's injected into the `state` field of a `deps` object that implements the StateHandler protocol. To provide different `deps` for each request (e.g. based on the authenticated user), use AGUIAdapter.run_stream() or AGUIAdapter.dispatch_request() instead.

Parameters:

| Name                    | Type                                      | Description                                                                 | Default                                                                                                                                                                                                                                                                                                                                                                                                            |
| ----------------------- | ----------------------------------------- | --------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `agent`                 | `AbstractAgent[AgentDepsT, OutputDataT]`  | The agent to run.                                                           | *required*                                                                                                                                                                                                                                                                                                                                                                                                         |
| `output_type`           | \`OutputSpec[Any]                         | None\`                                                                      | Custom output type to use for this run, output_type may only be used if the agent has no output validators since output validators would expect an argument that matches the agent's output type.                                                                                                                                                                                                                  |
| `message_history`       | \`Sequence[ModelMessage]                  | None\`                                                                      | History of the conversation so far.                                                                                                                                                                                                                                                                                                                                                                                |
| `deferred_tool_results` | \`DeferredToolResults                     | None\`                                                                      | Optional results for deferred tool calls in the message history.                                                                                                                                                                                                                                                                                                                                                   |
| `model`                 | \`Model                                   | KnownModelName                                                              | str                                                                                                                                                                                                                                                                                                                                                                                                                |
| `deps`                  | `AgentDepsT`                              | Optional dependencies to use for this run.                                  | `None`                                                                                                                                                                                                                                                                                                                                                                                                             |
| `model_settings`        | \`ModelSettings                           | None\`                                                                      | Optional settings to use for this model's request.                                                                                                                                                                                                                                                                                                                                                                 |
| `usage_limits`          | \`UsageLimits                             | None\`                                                                      | Optional limits on model request count or token usage.                                                                                                                                                                                                                                                                                                                                                             |
| `usage`                 | \`RunUsage                                | None\`                                                                      | Optional usage to start with, useful for resuming a conversation or agents used in tools.                                                                                                                                                                                                                                                                                                                          |
| `infer_name`            | `bool`                                    | Whether to try to infer the agent name from the call frame if it's not set. | `True`                                                                                                                                                                                                                                                                                                                                                                                                             |
| `toolsets`              | \`Sequence\[AbstractToolset[AgentDepsT]\] | None\`                                                                      | Optional additional toolsets for this run.                                                                                                                                                                                                                                                                                                                                                                         |
| `builtin_tools`         | \`Sequence[AbstractBuiltinTool]           | None\`                                                                      | Optional additional builtin tools for this run.                                                                                                                                                                                                                                                                                                                                                                    |
| `on_complete`           | \`OnCompleteFunc[Any]                     | None\`                                                                      | Optional callback function called when the agent run completes successfully. The callback receives the completed AgentRunResult and can access all_messages() and other result data.                                                                                                                                                                                                                               |
| `debug`                 | `bool`                                    | Boolean indicating if debug tracebacks should be returned on errors.        | `False`                                                                                                                                                                                                                                                                                                                                                                                                            |
| `routes`                | \`Sequence[BaseRoute]                     | None\`                                                                      | A list of routes to serve incoming HTTP and WebSocket requests.                                                                                                                                                                                                                                                                                                                                                    |
| `middleware`            | \`Sequence[Middleware]                    | None\`                                                                      | A list of middleware to run for every request. A starlette application will always automatically include two middleware classes. ServerErrorMiddleware is added as the very outermost middleware, to handle any uncaught errors occurring anywhere in the entire stack. ExceptionMiddleware is added as the very innermost middleware, to deal with handled exception cases occurring in the routing or endpoints. |
| `exception_handlers`    | \`Mapping[Any, ExceptionHandler]          | None\`                                                                      | A mapping of either integer status codes, or exception class types onto callables which handle the exceptions. Exception handler callables should be of the form handler(request, exc) -> response and may be either standard functions, or async functions.                                                                                                                                                       |
| `on_startup`            | \`Sequence\[Callable\[[], Any\]\]         | None\`                                                                      | A list of callables to run on application startup. Startup handler callables do not take any arguments, and may be either standard functions, or async functions.                                                                                                                                                                                                                                                  |
| `on_shutdown`           | \`Sequence\[Callable\[[], Any\]\]         | None\`                                                                      | A list of callables to run on application shutdown. Shutdown handler callables do not take any arguments, and may be either standard functions, or async functions.                                                                                                                                                                                                                                                |
| `lifespan`              | \`Lifespan[Self]                          | None\`                                                                      | A lifespan context function, which can be used to perform startup and shutdown tasks. This is a newer style that replaces the on_startup and on_shutdown handlers. Use one or the other, not both.                                                                                                                                                                                                                 |

Source code in `pydantic_ai_slim/pydantic_ai/ui/ag_ui/app.py`

```python
def __init__(
    self,
    agent: AbstractAgent[AgentDepsT, OutputDataT],
    *,
    # AGUIAdapter.dispatch_request parameters
    output_type: OutputSpec[Any] | None = None,
    message_history: Sequence[ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    model: Model | KnownModelName | str | None = None,
    deps: AgentDepsT = None,
    model_settings: ModelSettings | None = None,
    usage_limits: UsageLimits | None = None,
    usage: RunUsage | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    builtin_tools: Sequence[AbstractBuiltinTool] | None = None,
    on_complete: OnCompleteFunc[Any] | None = None,
    # Starlette parameters
    debug: bool = False,
    routes: Sequence[BaseRoute] | None = None,
    middleware: Sequence[Middleware] | None = None,
    exception_handlers: Mapping[Any, ExceptionHandler] | None = None,
    on_startup: Sequence[Callable[[], Any]] | None = None,
    on_shutdown: Sequence[Callable[[], Any]] | None = None,
    lifespan: Lifespan[Self] | None = None,
) -> None:
    """An ASGI application that handles every request by running the agent and streaming the response.

    Note that the `deps` will be the same for each request, with the exception of the frontend state that's
    injected into the `state` field of a `deps` object that implements the [`StateHandler`][pydantic_ai.ui.StateHandler] protocol.
    To provide different `deps` for each request (e.g. based on the authenticated user),
    use [`AGUIAdapter.run_stream()`][pydantic_ai.ui.ag_ui.AGUIAdapter.run_stream] or
    [`AGUIAdapter.dispatch_request()`][pydantic_ai.ui.ag_ui.AGUIAdapter.dispatch_request] instead.

    Args:
        agent: The agent to run.

        output_type: Custom output type to use for this run, `output_type` may only be used if the agent has
            no output validators since output validators would expect an argument that matches the agent's
            output type.
        message_history: History of the conversation so far.
        deferred_tool_results: Optional results for deferred tool calls in the message history.
        model: Optional model to use for this run, required if `model` was not set when creating the agent.
        deps: Optional dependencies to use for this run.
        model_settings: Optional settings to use for this model's request.
        usage_limits: Optional limits on model request count or token usage.
        usage: Optional usage to start with, useful for resuming a conversation or agents used in tools.
        infer_name: Whether to try to infer the agent name from the call frame if it's not set.
        toolsets: Optional additional toolsets for this run.
        builtin_tools: Optional additional builtin tools for this run.
        on_complete: Optional callback function called when the agent run completes successfully.
            The callback receives the completed [`AgentRunResult`][pydantic_ai.agent.AgentRunResult] and can access `all_messages()` and other result data.

        debug: Boolean indicating if debug tracebacks should be returned on errors.
        routes: A list of routes to serve incoming HTTP and WebSocket requests.
        middleware: A list of middleware to run for every request. A starlette application will always
            automatically include two middleware classes. `ServerErrorMiddleware` is added as the very
            outermost middleware, to handle any uncaught errors occurring anywhere in the entire stack.
            `ExceptionMiddleware` is added as the very innermost middleware, to deal with handled
            exception cases occurring in the routing or endpoints.
        exception_handlers: A mapping of either integer status codes, or exception class types onto
            callables which handle the exceptions. Exception handler callables should be of the form
            `handler(request, exc) -> response` and may be either standard functions, or async functions.
        on_startup: A list of callables to run on application startup. Startup handler callables do not
            take any arguments, and may be either standard functions, or async functions.
        on_shutdown: A list of callables to run on application shutdown. Shutdown handler callables do
            not take any arguments, and may be either standard functions, or async functions.
        lifespan: A lifespan context function, which can be used to perform startup and shutdown tasks.
            This is a newer style that replaces the `on_startup` and `on_shutdown` handlers. Use one or
            the other, not both.
    """
    super().__init__(
        debug=debug,
        routes=routes,
        middleware=middleware,
        exception_handlers=exception_handlers,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        lifespan=lifespan,
    )

    async def run_agent(request: Request) -> Response:
        """Endpoint to run the agent with the provided input data."""
        # `dispatch_request` will store the frontend state from the request on `deps.state` (if it implements the `StateHandler` protocol),
        # so we need to copy the deps to avoid different requests mutating the same deps object.
        nonlocal deps
        if isinstance(deps, StateHandler):  # pragma: no branch
            deps = replace(deps)

        return await AGUIAdapter[AgentDepsT, OutputDataT].dispatch_request(
            request,
            agent=agent,
            output_type=output_type,
            message_history=message_history,
            deferred_tool_results=deferred_tool_results,
            model=model,
            deps=deps,
            model_settings=model_settings,
            usage_limits=usage_limits,
            usage=usage,
            infer_name=infer_name,
            toolsets=toolsets,
            builtin_tools=builtin_tools,
            on_complete=on_complete,
        )

    self.router.add_route('/', run_agent, methods=['POST'])
```
