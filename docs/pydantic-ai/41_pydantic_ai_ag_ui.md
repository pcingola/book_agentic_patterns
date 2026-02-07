# `pydantic_ai.ag_ui`

Provides an AG-UI protocol adapter for the Pydantic AI agent.

This package provides seamless integration between pydantic-ai agents and ag-ui for building interactive AI applications with streaming event-based communication.

### SSE_CONTENT_TYPE

```python
SSE_CONTENT_TYPE = 'text/event-stream'
```

Content type header value for Server-Sent Events (SSE).

### OnCompleteFunc

```python
OnCompleteFunc: TypeAlias = (
    Callable[[AgentRunResult[Any]], None]
    | Callable[[AgentRunResult[Any]], Awaitable[None]]
    | Callable[[AgentRunResult[Any]], AsyncIterator[EventT]]
)
```

Callback function type that receives the `AgentRunResult` of the completed run. Can be sync, async, or an async generator of protocol-specific events.

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

### handle_ag_ui_request

```python
handle_ag_ui_request(
    agent: AbstractAgent[AgentDepsT, Any],
    request: Request,
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
    metadata: AgentMetadata[AgentDepsT] | None = None,
    infer_name: bool = True,
    toolsets: (
        Sequence[AbstractToolset[AgentDepsT]] | None
    ) = None,
    on_complete: OnCompleteFunc[BaseEvent] | None = None
) -> Response
```

Handle an AG-UI request by running the agent and returning a streaming response.

Parameters:

| Name                    | Type                                      | Description                                                                 | Default                                                                                                                                                                                           |
| ----------------------- | ----------------------------------------- | --------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `agent`                 | `AbstractAgent[AgentDepsT, Any]`          | The agent to run.                                                           | *required*                                                                                                                                                                                        |
| `request`               | `Request`                                 | The Starlette request (e.g. from FastAPI) containing the AG-UI run input.   | *required*                                                                                                                                                                                        |
| `output_type`           | \`OutputSpec[Any]                         | None\`                                                                      | Custom output type to use for this run, output_type may only be used if the agent has no output validators since output validators would expect an argument that matches the agent's output type. |
| `message_history`       | \`Sequence[ModelMessage]                  | None\`                                                                      | History of the conversation so far.                                                                                                                                                               |
| `deferred_tool_results` | \`DeferredToolResults                     | None\`                                                                      | Optional results for deferred tool calls in the message history.                                                                                                                                  |
| `model`                 | \`Model                                   | KnownModelName                                                              | str                                                                                                                                                                                               |
| `deps`                  | `AgentDepsT`                              | Optional dependencies to use for this run.                                  | `None`                                                                                                                                                                                            |
| `model_settings`        | \`ModelSettings                           | None\`                                                                      | Optional settings to use for this model's request.                                                                                                                                                |
| `usage_limits`          | \`UsageLimits                             | None\`                                                                      | Optional limits on model request count or token usage.                                                                                                                                            |
| `usage`                 | \`RunUsage                                | None\`                                                                      | Optional usage to start with, useful for resuming a conversation or agents used in tools.                                                                                                         |
| `metadata`              | \`AgentMetadata[AgentDepsT]               | None\`                                                                      | Optional metadata to attach to this run. Accepts a dictionary or a callable taking RunContext; merged with the agent's configured metadata.                                                       |
| `infer_name`            | `bool`                                    | Whether to try to infer the agent name from the call frame if it's not set. | `True`                                                                                                                                                                                            |
| `toolsets`              | \`Sequence\[AbstractToolset[AgentDepsT]\] | None\`                                                                      | Optional additional toolsets for this run.                                                                                                                                                        |
| `on_complete`           | \`OnCompleteFunc[BaseEvent]               | None\`                                                                      | Optional callback function called when the agent run completes successfully. The callback receives the completed AgentRunResult and can access all_messages() and other result data.              |

Returns:

| Type       | Description                                                |
| ---------- | ---------------------------------------------------------- |
| `Response` | A streaming Starlette response with AG-UI protocol events. |

Source code in `pydantic_ai_slim/pydantic_ai/ag_ui.py`

```python
async def handle_ag_ui_request(
    agent: AbstractAgent[AgentDepsT, Any],
    request: Request,
    *,
    output_type: OutputSpec[Any] | None = None,
    message_history: Sequence[ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    model: Model | KnownModelName | str | None = None,
    deps: AgentDepsT = None,
    model_settings: ModelSettings | None = None,
    usage_limits: UsageLimits | None = None,
    usage: RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    on_complete: OnCompleteFunc[BaseEvent] | None = None,
) -> Response:
    """Handle an AG-UI request by running the agent and returning a streaming response.

    Args:
        agent: The agent to run.
        request: The Starlette request (e.g. from FastAPI) containing the AG-UI run input.

        output_type: Custom output type to use for this run, `output_type` may only be used if the agent has no
            output validators since output validators would expect an argument that matches the agent's output type.
        message_history: History of the conversation so far.
        deferred_tool_results: Optional results for deferred tool calls in the message history.
        model: Optional model to use for this run, required if `model` was not set when creating the agent.
        deps: Optional dependencies to use for this run.
        model_settings: Optional settings to use for this model's request.
        usage_limits: Optional limits on model request count or token usage.
        usage: Optional usage to start with, useful for resuming a conversation or agents used in tools.
        metadata: Optional metadata to attach to this run. Accepts a dictionary or a callable taking
            [`RunContext`][pydantic_ai.tools.RunContext]; merged with the agent's configured metadata.
        infer_name: Whether to try to infer the agent name from the call frame if it's not set.
        toolsets: Optional additional toolsets for this run.
        on_complete: Optional callback function called when the agent run completes successfully.
            The callback receives the completed [`AgentRunResult`][pydantic_ai.agent.AgentRunResult] and can access `all_messages()` and other result data.

    Returns:
        A streaming Starlette response with AG-UI protocol events.
    """
    return await AGUIAdapter[AgentDepsT].dispatch_request(
        request,
        agent=agent,
        deps=deps,
        output_type=output_type,
        message_history=message_history,
        deferred_tool_results=deferred_tool_results,
        model=model,
        model_settings=model_settings,
        usage_limits=usage_limits,
        usage=usage,
        metadata=metadata,
        infer_name=infer_name,
        toolsets=toolsets,
        on_complete=on_complete,
    )
```

### run_ag_ui

```python
run_ag_ui(
    agent: AbstractAgent[AgentDepsT, Any],
    run_input: RunAgentInput,
    accept: str = SSE_CONTENT_TYPE,
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
    metadata: AgentMetadata[AgentDepsT] | None = None,
    infer_name: bool = True,
    toolsets: (
        Sequence[AbstractToolset[AgentDepsT]] | None
    ) = None,
    on_complete: OnCompleteFunc[BaseEvent] | None = None
) -> AsyncIterator[str]
```

Run the agent with the AG-UI run input and stream AG-UI protocol events.

Parameters:

| Name                    | Type                                      | Description                                                                 | Default                                                                                                                                                                                           |
| ----------------------- | ----------------------------------------- | --------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `agent`                 | `AbstractAgent[AgentDepsT, Any]`          | The agent to run.                                                           | *required*                                                                                                                                                                                        |
| `run_input`             | `RunAgentInput`                           | The AG-UI run input containing thread_id, run_id, messages, etc.            | *required*                                                                                                                                                                                        |
| `accept`                | `str`                                     | The accept header value for the run.                                        | `SSE_CONTENT_TYPE`                                                                                                                                                                                |
| `output_type`           | \`OutputSpec[Any]                         | None\`                                                                      | Custom output type to use for this run, output_type may only be used if the agent has no output validators since output validators would expect an argument that matches the agent's output type. |
| `message_history`       | \`Sequence[ModelMessage]                  | None\`                                                                      | History of the conversation so far.                                                                                                                                                               |
| `deferred_tool_results` | \`DeferredToolResults                     | None\`                                                                      | Optional results for deferred tool calls in the message history.                                                                                                                                  |
| `model`                 | \`Model                                   | KnownModelName                                                              | str                                                                                                                                                                                               |
| `deps`                  | `AgentDepsT`                              | Optional dependencies to use for this run.                                  | `None`                                                                                                                                                                                            |
| `model_settings`        | \`ModelSettings                           | None\`                                                                      | Optional settings to use for this model's request.                                                                                                                                                |
| `usage_limits`          | \`UsageLimits                             | None\`                                                                      | Optional limits on model request count or token usage.                                                                                                                                            |
| `usage`                 | \`RunUsage                                | None\`                                                                      | Optional usage to start with, useful for resuming a conversation or agents used in tools.                                                                                                         |
| `metadata`              | \`AgentMetadata[AgentDepsT]               | None\`                                                                      | Optional metadata to attach to this run. Accepts a dictionary or a callable taking RunContext; merged with the agent's configured metadata.                                                       |
| `infer_name`            | `bool`                                    | Whether to try to infer the agent name from the call frame if it's not set. | `True`                                                                                                                                                                                            |
| `toolsets`              | \`Sequence\[AbstractToolset[AgentDepsT]\] | None\`                                                                      | Optional additional toolsets for this run.                                                                                                                                                        |
| `on_complete`           | \`OnCompleteFunc[BaseEvent]               | None\`                                                                      | Optional callback function called when the agent run completes successfully. The callback receives the completed AgentRunResult and can access all_messages() and other result data.              |

Yields:

| Type                 | Description                                                                     |
| -------------------- | ------------------------------------------------------------------------------- |
| `AsyncIterator[str]` | Streaming event chunks encoded as strings according to the accept header value. |

Source code in `pydantic_ai_slim/pydantic_ai/ag_ui.py`

```python
def run_ag_ui(
    agent: AbstractAgent[AgentDepsT, Any],
    run_input: RunAgentInput,
    accept: str = SSE_CONTENT_TYPE,
    *,
    output_type: OutputSpec[Any] | None = None,
    message_history: Sequence[ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    model: Model | KnownModelName | str | None = None,
    deps: AgentDepsT = None,
    model_settings: ModelSettings | None = None,
    usage_limits: UsageLimits | None = None,
    usage: RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    on_complete: OnCompleteFunc[BaseEvent] | None = None,
) -> AsyncIterator[str]:
    """Run the agent with the AG-UI run input and stream AG-UI protocol events.

    Args:
        agent: The agent to run.
        run_input: The AG-UI run input containing thread_id, run_id, messages, etc.
        accept: The accept header value for the run.

        output_type: Custom output type to use for this run, `output_type` may only be used if the agent has no
            output validators since output validators would expect an argument that matches the agent's output type.
        message_history: History of the conversation so far.
        deferred_tool_results: Optional results for deferred tool calls in the message history.
        model: Optional model to use for this run, required if `model` was not set when creating the agent.
        deps: Optional dependencies to use for this run.
        model_settings: Optional settings to use for this model's request.
        usage_limits: Optional limits on model request count or token usage.
        usage: Optional usage to start with, useful for resuming a conversation or agents used in tools.
        metadata: Optional metadata to attach to this run. Accepts a dictionary or a callable taking
            [`RunContext`][pydantic_ai.tools.RunContext]; merged with the agent's configured metadata.
        infer_name: Whether to try to infer the agent name from the call frame if it's not set.
        toolsets: Optional additional toolsets for this run.
        on_complete: Optional callback function called when the agent run completes successfully.
            The callback receives the completed [`AgentRunResult`][pydantic_ai.agent.AgentRunResult] and can access `all_messages()` and other result data.

    Yields:
        Streaming event chunks encoded as strings according to the accept header value.
    """
    adapter = AGUIAdapter(agent=agent, run_input=run_input, accept=accept)
    return adapter.encode_stream(
        adapter.run_stream(
            output_type=output_type,
            message_history=message_history,
            deferred_tool_results=deferred_tool_results,
            model=model,
            deps=deps,
            model_settings=model_settings,
            usage_limits=usage_limits,
            usage=usage,
            metadata=metadata,
            infer_name=infer_name,
            toolsets=toolsets,
            on_complete=on_complete,
        ),
    )
```
