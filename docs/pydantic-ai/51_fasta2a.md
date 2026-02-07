# `fasta2a`

### FastA2A

Bases: `Starlette`

The main class for the FastA2A library.

Source code in `.venv/lib/python3.12/site-packages/fasta2a/applications.py`

```python
class FastA2A(Starlette):
    """The main class for the FastA2A library."""

    def __init__(
        self,
        *,
        storage: Storage,
        broker: Broker,
        # Agent card
        name: str | None = None,
        url: str = 'http://localhost:8000',
        version: str = '1.0.0',
        description: str | None = None,
        provider: AgentProvider | None = None,
        skills: list[Skill] | None = None,
        # Starlette
        debug: bool = False,
        routes: Sequence[Route] | None = None,
        middleware: Sequence[Middleware] | None = None,
        exception_handlers: dict[Any, ExceptionHandler] | None = None,
        lifespan: Lifespan[FastA2A] | None = None,
    ):
        if lifespan is None:
            lifespan = _default_lifespan

        super().__init__(
            debug=debug,
            routes=routes,
            middleware=middleware,
            exception_handlers=exception_handlers,
            lifespan=lifespan,
        )

        self.name = name or 'My Agent'
        self.url = url
        self.version = version
        self.description = description
        self.provider = provider
        self.skills = skills or []
        # NOTE: For now, I don't think there's any reason to support any other input/output modes.
        self.default_input_modes = ['application/json']
        self.default_output_modes = ['application/json']

        self.task_manager = TaskManager(broker=broker, storage=storage)

        # Setup
        self._agent_card_json_schema: bytes | None = None
        self.router.add_route(
            '/.well-known/agent-card.json', self._agent_card_endpoint, methods=['HEAD', 'GET', 'OPTIONS']
        )
        self.router.add_route('/', self._agent_run_endpoint, methods=['POST'])
        self.router.add_route('/docs', self._docs_endpoint, methods=['GET'])

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope['type'] == 'http' and not self.task_manager.is_running:
            raise RuntimeError('TaskManager was not properly initialized.')
        await super().__call__(scope, receive, send)

    async def _agent_card_endpoint(self, request: Request) -> Response:
        if self._agent_card_json_schema is None:
            agent_card = AgentCard(
                name=self.name,
                description=self.description or 'An AI agent exposed as an A2A agent.',
                url=self.url,
                version=self.version,
                protocol_version='0.3.0',
                skills=self.skills,
                default_input_modes=self.default_input_modes,
                default_output_modes=self.default_output_modes,
                capabilities=AgentCapabilities(
                    streaming=False, push_notifications=False, state_transition_history=False
                ),
            )
            if self.provider is not None:
                agent_card['provider'] = self.provider
            self._agent_card_json_schema = agent_card_ta.dump_json(agent_card, by_alias=True)
        return Response(content=self._agent_card_json_schema, media_type='application/json')

    async def _docs_endpoint(self, request: Request) -> Response:
        """Serve the documentation interface."""
        docs_path = Path(__file__).parent / 'static' / 'docs.html'
        return FileResponse(docs_path, media_type='text/html')

    async def _agent_run_endpoint(self, request: Request) -> Response:
        """This is the main endpoint for the A2A server.

        Although the specification allows freedom of choice and implementation, I'm pretty sure about some decisions.

        1. The server will always either send a "submitted" or a "failed" on `message/send`.
            Never a "completed" on the first message.
        2. There are three possible ends for the task:
            2.1. The task was "completed" successfully.
            2.2. The task was "canceled".
            2.3. The task "failed".
        3. The server will send a "working" on the first chunk on `tasks/pushNotification/get`.
        """
        data = await request.body()
        a2a_request = a2a_request_ta.validate_json(data)

        if a2a_request['method'] == 'message/send':
            jsonrpc_response = await self.task_manager.send_message(a2a_request)
        elif a2a_request['method'] == 'tasks/get':
            jsonrpc_response = await self.task_manager.get_task(a2a_request)
        elif a2a_request['method'] == 'tasks/cancel':
            jsonrpc_response = await self.task_manager.cancel_task(a2a_request)
        else:
            raise NotImplementedError(f'Method {a2a_request["method"]} not implemented.')
        return Response(
            content=a2a_response_ta.dump_json(jsonrpc_response, by_alias=True), media_type='application/json'
        )
```

### Broker

Bases: `ABC`

The broker class is in charge of scheduling the tasks.

The HTTP server uses the broker to schedule tasks.

The simple implementation is the `InMemoryBroker`, which is the broker that runs the tasks in the same process as the HTTP server. That said, this class can be extended to support remote workers.

Source code in `.venv/lib/python3.12/site-packages/fasta2a/broker.py`

```python
@dataclass
class Broker(ABC):
    """The broker class is in charge of scheduling the tasks.

    The HTTP server uses the broker to schedule tasks.

    The simple implementation is the `InMemoryBroker`, which is the broker that
    runs the tasks in the same process as the HTTP server. That said, this class can be
    extended to support remote workers.
    """

    @abstractmethod
    async def run_task(self, params: TaskSendParams) -> None:
        """Send a task to be executed by the worker."""
        raise NotImplementedError('send_run_task is not implemented yet.')

    @abstractmethod
    async def cancel_task(self, params: TaskIdParams) -> None:
        """Cancel a task."""
        raise NotImplementedError('send_cancel_task is not implemented yet.')

    @abstractmethod
    async def __aenter__(self) -> Self: ...

    @abstractmethod
    async def __aexit__(self, exc_type: Any, exc_value: Any, traceback: Any): ...

    @abstractmethod
    def receive_task_operations(self) -> AsyncIterator[TaskOperation]:
        """Receive task operations from the broker.

        On a multi-worker setup, the broker will need to round-robin the task operations
        between the workers.
        """
```

#### run_task

```python
run_task(params: TaskSendParams) -> None
```

Send a task to be executed by the worker.

Source code in `.venv/lib/python3.12/site-packages/fasta2a/broker.py`

```python
@abstractmethod
async def run_task(self, params: TaskSendParams) -> None:
    """Send a task to be executed by the worker."""
    raise NotImplementedError('send_run_task is not implemented yet.')
```

#### cancel_task

```python
cancel_task(params: TaskIdParams) -> None
```

Cancel a task.

Source code in `.venv/lib/python3.12/site-packages/fasta2a/broker.py`

```python
@abstractmethod
async def cancel_task(self, params: TaskIdParams) -> None:
    """Cancel a task."""
    raise NotImplementedError('send_cancel_task is not implemented yet.')
```

#### receive_task_operations

```python
receive_task_operations() -> AsyncIterator[TaskOperation]
```

Receive task operations from the broker.

On a multi-worker setup, the broker will need to round-robin the task operations between the workers.

Source code in `.venv/lib/python3.12/site-packages/fasta2a/broker.py`

```python
@abstractmethod
def receive_task_operations(self) -> AsyncIterator[TaskOperation]:
    """Receive task operations from the broker.

    On a multi-worker setup, the broker will need to round-robin the task operations
    between the workers.
    """
```

### Skill

Bases: `TypedDict`

Skills are a unit of capability that an agent can perform.

Source code in `.venv/lib/python3.12/site-packages/fasta2a/schema.py`

```python
@pydantic.with_config({'alias_generator': to_camel})
class Skill(TypedDict):
    """Skills are a unit of capability that an agent can perform."""

    id: str
    """A unique identifier for the skill."""

    name: str
    """Human readable name of the skill."""

    description: str
    """A human-readable description of the skill.

    It will be used by the client or a human as a hint to understand the skill.
    """

    tags: list[str]
    """Set of tag-words describing classes of capabilities for this specific skill.

    Examples: "cooking", "customer support", "billing".
    """

    examples: NotRequired[list[str]]
    """The set of example scenarios that the skill can perform.

    Will be used by the client as a hint to understand how the skill can be used. (e.g. "I need a recipe for bread")
    """

    input_modes: list[str]
    """Supported mime types for input data."""

    output_modes: list[str]
    """Supported mime types for output data."""
```

#### id

```python
id: str
```

A unique identifier for the skill.

#### name

```python
name: str
```

Human readable name of the skill.

#### description

```python
description: str
```

A human-readable description of the skill.

It will be used by the client or a human as a hint to understand the skill.

#### tags

```python
tags: list[str]
```

Set of tag-words describing classes of capabilities for this specific skill.

Examples: "cooking", "customer support", "billing".

#### examples

```python
examples: NotRequired[list[str]]
```

The set of example scenarios that the skill can perform.

Will be used by the client as a hint to understand how the skill can be used. (e.g. "I need a recipe for bread")

#### input_modes

```python
input_modes: list[str]
```

Supported mime types for input data.

#### output_modes

```python
output_modes: list[str]
```

Supported mime types for output data.

### Storage

Bases: `ABC`, `Generic[ContextT]`

A storage to retrieve and save tasks, as well as retrieve and save context.

The storage serves two purposes:

1. Task storage: Stores tasks in A2A protocol format with their status, artifacts, and message history
1. Context storage: Stores conversation context in a format optimized for the specific agent implementation

Source code in `.venv/lib/python3.12/site-packages/fasta2a/storage.py`

```python
class Storage(ABC, Generic[ContextT]):
    """A storage to retrieve and save tasks, as well as retrieve and save context.

    The storage serves two purposes:
    1. Task storage: Stores tasks in A2A protocol format with their status, artifacts, and message history
    2. Context storage: Stores conversation context in a format optimized for the specific agent implementation
    """

    @abstractmethod
    async def load_task(self, task_id: str, history_length: int | None = None) -> Task | None:
        """Load a task from storage.

        If the task is not found, return None.
        """

    @abstractmethod
    async def submit_task(self, context_id: str, message: Message) -> Task:
        """Submit a task to storage."""

    @abstractmethod
    async def update_task(
        self,
        task_id: str,
        state: TaskState,
        new_artifacts: list[Artifact] | None = None,
        new_messages: list[Message] | None = None,
    ) -> Task:
        """Update the state of a task. Appends artifacts and messages, if specified."""

    @abstractmethod
    async def load_context(self, context_id: str) -> ContextT | None:
        """Retrieve the stored context given the `context_id`."""

    @abstractmethod
    async def update_context(self, context_id: str, context: ContextT) -> None:
        """Updates the context for a `context_id`.

        Implementing agent can decide what to store in context.
        """
```

#### load_task

```python
load_task(
    task_id: str, history_length: int | None = None
) -> Task | None
```

Load a task from storage.

If the task is not found, return None.

Source code in `.venv/lib/python3.12/site-packages/fasta2a/storage.py`

```python
@abstractmethod
async def load_task(self, task_id: str, history_length: int | None = None) -> Task | None:
    """Load a task from storage.

    If the task is not found, return None.
    """
```

#### submit_task

```python
submit_task(context_id: str, message: Message) -> Task
```

Submit a task to storage.

Source code in `.venv/lib/python3.12/site-packages/fasta2a/storage.py`

```python
@abstractmethod
async def submit_task(self, context_id: str, message: Message) -> Task:
    """Submit a task to storage."""
```

#### update_task

```python
update_task(
    task_id: str,
    state: TaskState,
    new_artifacts: list[Artifact] | None = None,
    new_messages: list[Message] | None = None,
) -> Task
```

Update the state of a task. Appends artifacts and messages, if specified.

Source code in `.venv/lib/python3.12/site-packages/fasta2a/storage.py`

```python
@abstractmethod
async def update_task(
    self,
    task_id: str,
    state: TaskState,
    new_artifacts: list[Artifact] | None = None,
    new_messages: list[Message] | None = None,
) -> Task:
    """Update the state of a task. Appends artifacts and messages, if specified."""
```

#### load_context

```python
load_context(context_id: str) -> ContextT | None
```

Retrieve the stored context given the `context_id`.

Source code in `.venv/lib/python3.12/site-packages/fasta2a/storage.py`

```python
@abstractmethod
async def load_context(self, context_id: str) -> ContextT | None:
    """Retrieve the stored context given the `context_id`."""
```

#### update_context

```python
update_context(context_id: str, context: ContextT) -> None
```

Updates the context for a `context_id`.

Implementing agent can decide what to store in context.

Source code in `.venv/lib/python3.12/site-packages/fasta2a/storage.py`

```python
@abstractmethod
async def update_context(self, context_id: str, context: ContextT) -> None:
    """Updates the context for a `context_id`.

    Implementing agent can decide what to store in context.
    """
```

### Worker

Bases: `ABC`, `Generic[ContextT]`

A worker is responsible for executing tasks.

Source code in `.venv/lib/python3.12/site-packages/fasta2a/worker.py`

```python
@dataclass
class Worker(ABC, Generic[ContextT]):
    """A worker is responsible for executing tasks."""

    broker: Broker
    storage: Storage[ContextT]

    @asynccontextmanager
    async def run(self) -> AsyncIterator[None]:
        """Run the worker.

        It connects to the broker, and it makes itself available to receive commands.
        """
        async with anyio.create_task_group() as tg:
            tg.start_soon(self._loop)
            yield
            tg.cancel_scope.cancel()

    async def _loop(self) -> None:
        async for task_operation in self.broker.receive_task_operations():
            await self._handle_task_operation(task_operation)

    async def _handle_task_operation(self, task_operation: TaskOperation) -> None:
        try:
            with use_span(task_operation['_current_span']):
                with tracer.start_as_current_span(
                    f'{task_operation["operation"]} task', attributes={'logfire.tags': ['fasta2a']}
                ):
                    if task_operation['operation'] == 'run':
                        await self.run_task(task_operation['params'])
                    elif task_operation['operation'] == 'cancel':
                        await self.cancel_task(task_operation['params'])
                    else:
                        assert_never(task_operation)
        except Exception:
            await self.storage.update_task(task_operation['params']['id'], state='failed')

    @abstractmethod
    async def run_task(self, params: TaskSendParams) -> None: ...

    @abstractmethod
    async def cancel_task(self, params: TaskIdParams) -> None: ...

    @abstractmethod
    def build_message_history(self, history: list[Message]) -> list[Any]: ...

    @abstractmethod
    def build_artifacts(self, result: Any) -> list[Artifact]: ...
```

#### run

```python
run() -> AsyncIterator[None]
```

Run the worker.

It connects to the broker, and it makes itself available to receive commands.

Source code in `.venv/lib/python3.12/site-packages/fasta2a/worker.py`

```python
@asynccontextmanager
async def run(self) -> AsyncIterator[None]:
    """Run the worker.

    It connects to the broker, and it makes itself available to receive commands.
    """
    async with anyio.create_task_group() as tg:
        tg.start_soon(self._loop)
        yield
        tg.cancel_scope.cancel()
```

This module contains the schema for the agent card.

### AgentCard

Bases: `TypedDict`

The card that describes an agent.

Source code in `.venv/lib/python3.12/site-packages/fasta2a/schema.py`

```python
@pydantic.with_config({'alias_generator': to_camel})
class AgentCard(TypedDict):
    """The card that describes an agent."""

    name: str
    """Human readable name of the agent e.g. "Recipe Agent"."""

    description: str
    """A human-readable description of the agent.

    Used to assist users and other agents in understanding what the agent can do.
    (e.g. "Agent that helps users with recipes and cooking.")
    """

    url: str
    """A URL to the address the agent is hosted at."""

    version: str
    """The version of the agent - format is up to the provider. (e.g. "1.0.0")"""

    protocol_version: str
    """The version of the A2A protocol this agent supports."""

    provider: NotRequired[AgentProvider]
    """The service provider of the agent."""

    documentation_url: NotRequired[str]
    """A URL to documentation for the agent."""

    icon_url: NotRequired[str]
    """A URL to an icon for the agent."""

    preferred_transport: NotRequired[str]
    """The transport of the preferred endpoint. If empty, defaults to JSONRPC."""

    additional_interfaces: NotRequired[list[AgentInterface]]
    """Announcement of additional supported transports."""

    capabilities: AgentCapabilities
    """The capabilities of the agent."""

    security: NotRequired[list[dict[str, list[str]]]]
    """Security requirements for contacting the agent."""

    security_schemes: NotRequired[dict[str, SecurityScheme]]
    """Security scheme definitions."""

    default_input_modes: list[str]
    """Supported mime types for input data."""

    default_output_modes: list[str]
    """Supported mime types for output data."""

    skills: list[Skill]
    """The set of skills, or distinct capabilities, that the agent can perform."""
```

#### name

```python
name: str
```

Human readable name of the agent e.g. "Recipe Agent".

#### description

```python
description: str
```

A human-readable description of the agent.

Used to assist users and other agents in understanding what the agent can do. (e.g. "Agent that helps users with recipes and cooking.")

#### url

```python
url: str
```

A URL to the address the agent is hosted at.

#### version

```python
version: str
```

The version of the agent - format is up to the provider. (e.g. "1.0.0")

#### protocol_version

```python
protocol_version: str
```

The version of the A2A protocol this agent supports.

#### provider

```python
provider: NotRequired[AgentProvider]
```

The service provider of the agent.

#### documentation_url

```python
documentation_url: NotRequired[str]
```

A URL to documentation for the agent.

#### icon_url

```python
icon_url: NotRequired[str]
```

A URL to an icon for the agent.

#### preferred_transport

```python
preferred_transport: NotRequired[str]
```

The transport of the preferred endpoint. If empty, defaults to JSONRPC.

#### additional_interfaces

```python
additional_interfaces: NotRequired[list[AgentInterface]]
```

Announcement of additional supported transports.

#### capabilities

```python
capabilities: AgentCapabilities
```

The capabilities of the agent.

#### security

```python
security: NotRequired[list[dict[str, list[str]]]]
```

Security requirements for contacting the agent.

#### security_schemes

```python
security_schemes: NotRequired[dict[str, SecurityScheme]]
```

Security scheme definitions.

#### default_input_modes

```python
default_input_modes: list[str]
```

Supported mime types for input data.

#### default_output_modes

```python
default_output_modes: list[str]
```

Supported mime types for output data.

#### skills

```python
skills: list[Skill]
```

The set of skills, or distinct capabilities, that the agent can perform.

### AgentProvider

Bases: `TypedDict`

The service provider of the agent.

Source code in `.venv/lib/python3.12/site-packages/fasta2a/schema.py`

```python
class AgentProvider(TypedDict):
    """The service provider of the agent."""

    organization: str
    """The name of the agent provider's organization."""

    url: str
    """A URL for the agent provider's website or relevant documentation."""
```

#### organization

```python
organization: str
```

The name of the agent provider's organization.

#### url

```python
url: str
```

A URL for the agent provider's website or relevant documentation.

### AgentCapabilities

Bases: `TypedDict`

The capabilities of the agent.

Source code in `.venv/lib/python3.12/site-packages/fasta2a/schema.py`

```python
@pydantic.with_config({'alias_generator': to_camel})
class AgentCapabilities(TypedDict):
    """The capabilities of the agent."""

    streaming: NotRequired[bool]
    """Whether the agent supports streaming."""

    push_notifications: NotRequired[bool]
    """Whether the agent can notify updates to client."""

    state_transition_history: NotRequired[bool]
    """Whether the agent exposes status change history for tasks."""
```

#### streaming

```python
streaming: NotRequired[bool]
```

Whether the agent supports streaming.

#### push_notifications

```python
push_notifications: NotRequired[bool]
```

Whether the agent can notify updates to client.

#### state_transition_history

```python
state_transition_history: NotRequired[bool]
```

Whether the agent exposes status change history for tasks.

### HttpSecurityScheme

Bases: `TypedDict`

HTTP security scheme.

Source code in `.venv/lib/python3.12/site-packages/fasta2a/schema.py`

```python
@pydantic.with_config({'alias_generator': to_camel})
class HttpSecurityScheme(TypedDict):
    """HTTP security scheme."""

    type: Literal['http']
    """The type of the security scheme. Must be 'http'."""

    scheme: str
    """The name of the HTTP Authorization scheme."""

    bearer_format: NotRequired[str]
    """A hint to the client to identify how the bearer token is formatted."""

    description: NotRequired[str]
    """Description of this security scheme."""
```

#### type

```python
type: Literal['http']
```

The type of the security scheme. Must be 'http'.

#### scheme

```python
scheme: str
```

The name of the HTTP Authorization scheme.

#### bearer_format

```python
bearer_format: NotRequired[str]
```

A hint to the client to identify how the bearer token is formatted.

#### description

```python
description: NotRequired[str]
```

Description of this security scheme.

### ApiKeySecurityScheme

Bases: `TypedDict`

API Key security scheme.

Source code in `.venv/lib/python3.12/site-packages/fasta2a/schema.py`

```python
@pydantic.with_config({'alias_generator': to_camel})
class ApiKeySecurityScheme(TypedDict):
    """API Key security scheme."""

    type: Literal['apiKey']
    """The type of the security scheme. Must be 'apiKey'."""

    name: str
    """The name of the header, query or cookie parameter to be used."""

    in_: Literal['query', 'header', 'cookie']
    """The location of the API key."""

    description: NotRequired[str]
    """Description of this security scheme."""
```

#### type

```python
type: Literal['apiKey']
```

The type of the security scheme. Must be 'apiKey'.

#### name

```python
name: str
```

The name of the header, query or cookie parameter to be used.

#### in\_

```python
in_: Literal['query', 'header', 'cookie']
```

The location of the API key.

#### description

```python
description: NotRequired[str]
```

Description of this security scheme.

### OAuth2SecurityScheme

Bases: `TypedDict`

OAuth2 security scheme.

Source code in `.venv/lib/python3.12/site-packages/fasta2a/schema.py`

```python
@pydantic.with_config({'alias_generator': to_camel})
class OAuth2SecurityScheme(TypedDict):
    """OAuth2 security scheme."""

    type: Literal['oauth2']
    """The type of the security scheme. Must be 'oauth2'."""

    flows: dict[str, Any]
    """An object containing configuration information for the flow types supported."""

    description: NotRequired[str]
    """Description of this security scheme."""
```

#### type

```python
type: Literal['oauth2']
```

The type of the security scheme. Must be 'oauth2'.

#### flows

```python
flows: dict[str, Any]
```

An object containing configuration information for the flow types supported.

#### description

```python
description: NotRequired[str]
```

Description of this security scheme.

### OpenIdConnectSecurityScheme

Bases: `TypedDict`

OpenID Connect security scheme.

Source code in `.venv/lib/python3.12/site-packages/fasta2a/schema.py`

```python
@pydantic.with_config({'alias_generator': to_camel})
class OpenIdConnectSecurityScheme(TypedDict):
    """OpenID Connect security scheme."""

    type: Literal['openIdConnect']
    """The type of the security scheme. Must be 'openIdConnect'."""

    open_id_connect_url: str
    """OpenId Connect URL to discover OAuth2 configuration values."""

    description: NotRequired[str]
    """Description of this security scheme."""
```

#### type

```python
type: Literal['openIdConnect']
```

The type of the security scheme. Must be 'openIdConnect'.

#### open_id_connect_url

```python
open_id_connect_url: str
```

OpenId Connect URL to discover OAuth2 configuration values.

#### description

```python
description: NotRequired[str]
```

Description of this security scheme.

### SecurityScheme

```python
SecurityScheme = Annotated[
    Union[
        HttpSecurityScheme,
        ApiKeySecurityScheme,
        OAuth2SecurityScheme,
        OpenIdConnectSecurityScheme,
    ],
    Field(discriminator="type"),
]
```

A security scheme for authentication.

### AgentInterface

Bases: `TypedDict`

An interface that the agent supports.

Source code in `.venv/lib/python3.12/site-packages/fasta2a/schema.py`

```python
@pydantic.with_config({'alias_generator': to_camel})
class AgentInterface(TypedDict):
    """An interface that the agent supports."""

    transport: str
    """The transport protocol (e.g., 'jsonrpc', 'websocket')."""

    url: str
    """The URL endpoint for this transport."""

    description: NotRequired[str]
    """Description of this interface."""
```

#### transport

```python
transport: str
```

The transport protocol (e.g., 'jsonrpc', 'websocket').

#### url

```python
url: str
```

The URL endpoint for this transport.

#### description

```python
description: NotRequired[str]
```

Description of this interface.

### AgentExtension

Bases: `TypedDict`

A declaration of an extension supported by an Agent.

Source code in `.venv/lib/python3.12/site-packages/fasta2a/schema.py`

```python
@pydantic.with_config({'alias_generator': to_camel})
class AgentExtension(TypedDict):
    """A declaration of an extension supported by an Agent."""

    uri: str
    """The URI of the extension."""

    description: NotRequired[str]
    """A description of how this agent uses this extension."""

    required: NotRequired[bool]
    """Whether the client must follow specific requirements of the extension."""

    params: NotRequired[dict[str, Any]]
    """Optional configuration for the extension."""
```

#### uri

```python
uri: str
```

The URI of the extension.

#### description

```python
description: NotRequired[str]
```

A description of how this agent uses this extension.

#### required

```python
required: NotRequired[bool]
```

Whether the client must follow specific requirements of the extension.

#### params

```python
params: NotRequired[dict[str, Any]]
```

Optional configuration for the extension.

### Skill

Bases: `TypedDict`

Skills are a unit of capability that an agent can perform.

Source code in `.venv/lib/python3.12/site-packages/fasta2a/schema.py`

```python
@pydantic.with_config({'alias_generator': to_camel})
class Skill(TypedDict):
    """Skills are a unit of capability that an agent can perform."""

    id: str
    """A unique identifier for the skill."""

    name: str
    """Human readable name of the skill."""

    description: str
    """A human-readable description of the skill.

    It will be used by the client or a human as a hint to understand the skill.
    """

    tags: list[str]
    """Set of tag-words describing classes of capabilities for this specific skill.

    Examples: "cooking", "customer support", "billing".
    """

    examples: NotRequired[list[str]]
    """The set of example scenarios that the skill can perform.

    Will be used by the client as a hint to understand how the skill can be used. (e.g. "I need a recipe for bread")
    """

    input_modes: list[str]
    """Supported mime types for input data."""

    output_modes: list[str]
    """Supported mime types for output data."""
```

#### id

```python
id: str
```

A unique identifier for the skill.

#### name

```python
name: str
```

Human readable name of the skill.

#### description

```python
description: str
```

A human-readable description of the skill.

It will be used by the client or a human as a hint to understand the skill.

#### tags

```python
tags: list[str]
```

Set of tag-words describing classes of capabilities for this specific skill.

Examples: "cooking", "customer support", "billing".

#### examples

```python
examples: NotRequired[list[str]]
```

The set of example scenarios that the skill can perform.

Will be used by the client as a hint to understand how the skill can be used. (e.g. "I need a recipe for bread")

#### input_modes

```python
input_modes: list[str]
```

Supported mime types for input data.

#### output_modes

```python
output_modes: list[str]
```

Supported mime types for output data.

### Artifact

Bases: `TypedDict`

Agents generate Artifacts as an end result of a Task.

Artifacts are immutable, can be named, and can have multiple parts. A streaming response can append parts to existing Artifacts.

A single Task can generate many Artifacts. For example, "create a webpage" could create separate HTML and image Artifacts.

Source code in `.venv/lib/python3.12/site-packages/fasta2a/schema.py`

```python
@pydantic.with_config({'alias_generator': to_camel})
class Artifact(TypedDict):
    """Agents generate Artifacts as an end result of a Task.

    Artifacts are immutable, can be named, and can have multiple parts. A streaming response can append parts to
    existing Artifacts.

    A single Task can generate many Artifacts. For example, "create a webpage" could create separate HTML and image
    Artifacts.
    """

    artifact_id: str
    """Unique identifier for the artifact."""

    name: NotRequired[str]
    """The name of the artifact."""

    description: NotRequired[str]
    """A description of the artifact."""

    parts: list[Part]
    """The parts that make up the artifact."""

    metadata: NotRequired[dict[str, Any]]
    """Metadata about the artifact."""

    extensions: NotRequired[list[str]]
    """Array of extensions."""

    append: NotRequired[bool]
    """Whether to append this artifact to an existing one."""

    last_chunk: NotRequired[bool]
    """Whether this is the last chunk of the artifact."""
```

#### artifact_id

```python
artifact_id: str
```

Unique identifier for the artifact.

#### name

```python
name: NotRequired[str]
```

The name of the artifact.

#### description

```python
description: NotRequired[str]
```

A description of the artifact.

#### parts

```python
parts: list[Part]
```

The parts that make up the artifact.

#### metadata

```python
metadata: NotRequired[dict[str, Any]]
```

Metadata about the artifact.

#### extensions

```python
extensions: NotRequired[list[str]]
```

Array of extensions.

#### append

```python
append: NotRequired[bool]
```

Whether to append this artifact to an existing one.

#### last_chunk

```python
last_chunk: NotRequired[bool]
```

Whether this is the last chunk of the artifact.

### PushNotificationConfig

Bases: `TypedDict`

Configuration for push notifications.

A2A supports a secure notification mechanism whereby an agent can notify a client of an update outside a connected session via a PushNotificationService. Within and across enterprises, it is critical that the agent verifies the identity of the notification service, authenticates itself with the service, and presents an identifier that ties the notification to the executing Task.

The target server of the PushNotificationService should be considered a separate service, and is not guaranteed (or even expected) to be the client directly. This PushNotificationService is responsible for authenticating and authorizing the agent and for proxying the verified notification to the appropriate endpoint (which could be anything from a pub/sub queue, to an email inbox or other service, etc.).

For contrived scenarios with isolated client-agent pairs (e.g. local service mesh in a contained VPC, etc.) or isolated environments without enterprise security concerns, the client may choose to simply open a port and act as its own PushNotificationService. Any enterprise implementation will likely have a centralized service that authenticates the remote agents with trusted notification credentials and can handle online/offline scenarios. (This should be thought of similarly to a mobile Push Notification Service).

Source code in `.venv/lib/python3.12/site-packages/fasta2a/schema.py`

```python
@pydantic.with_config({'alias_generator': to_camel})
class PushNotificationConfig(TypedDict):
    """Configuration for push notifications.

    A2A supports a secure notification mechanism whereby an agent can notify a client of an update
    outside a connected session via a PushNotificationService. Within and across enterprises,
    it is critical that the agent verifies the identity of the notification service, authenticates
    itself with the service, and presents an identifier that ties the notification to the executing
    Task.

    The target server of the PushNotificationService should be considered a separate service, and
    is not guaranteed (or even expected) to be the client directly. This PushNotificationService is
    responsible for authenticating and authorizing the agent and for proxying the verified notification
    to the appropriate endpoint (which could be anything from a pub/sub queue, to an email inbox or
    other service, etc.).

    For contrived scenarios with isolated client-agent pairs (e.g. local service mesh in a contained
    VPC, etc.) or isolated environments without enterprise security concerns, the client may choose to
    simply open a port and act as its own PushNotificationService. Any enterprise implementation will
    likely have a centralized service that authenticates the remote agents with trusted notification
    credentials and can handle online/offline scenarios. (This should be thought of similarly to a
    mobile Push Notification Service).
    """

    id: NotRequired[str]
    """Server-assigned identifier."""

    url: str
    """The URL to send push notifications to."""

    token: NotRequired[str]
    """Token unique to this task/session."""

    authentication: NotRequired[SecurityScheme]
    """Authentication details for push notifications."""
```

#### id

```python
id: NotRequired[str]
```

Server-assigned identifier.

#### url

```python
url: str
```

The URL to send push notifications to.

#### token

```python
token: NotRequired[str]
```

Token unique to this task/session.

#### authentication

```python
authentication: NotRequired[SecurityScheme]
```

Authentication details for push notifications.

### TaskPushNotificationConfig

Bases: `TypedDict`

Configuration for task push notifications.

Source code in `.venv/lib/python3.12/site-packages/fasta2a/schema.py`

```python
@pydantic.with_config({'alias_generator': to_camel})
class TaskPushNotificationConfig(TypedDict):
    """Configuration for task push notifications."""

    id: str
    """The task id."""

    push_notification_config: PushNotificationConfig
    """The push notification configuration."""
```

#### id

```python
id: str
```

The task id.

#### push_notification_config

```python
push_notification_config: PushNotificationConfig
```

The push notification configuration.

### Message

Bases: `TypedDict`

A Message contains any content that is not an Artifact.

This can include things like agent thoughts, user context, instructions, errors, status, or metadata.

All content from a client comes in the form of a Message. Agents send Messages to communicate status or to provide instructions (whereas generated results are sent as Artifacts).

A Message can have multiple parts to denote different pieces of content. For example, a user request could include a textual description from a user and then multiple files used as context from the client.

Source code in `.venv/lib/python3.12/site-packages/fasta2a/schema.py`

```python
@pydantic.with_config({'alias_generator': to_camel})
class Message(TypedDict):
    """A Message contains any content that is not an Artifact.

    This can include things like agent thoughts, user context, instructions, errors, status, or metadata.

    All content from a client comes in the form of a Message. Agents send Messages to communicate status or to provide
    instructions (whereas generated results are sent as Artifacts).

    A Message can have multiple parts to denote different pieces of content. For example, a user request could include
    a textual description from a user and then multiple files used as context from the client.
    """

    role: Literal['user', 'agent']
    """The role of the message."""

    parts: list[Part]
    """The parts of the message."""

    kind: Literal['message']
    """Event type."""

    metadata: NotRequired[dict[str, Any]]
    """Metadata about the message."""

    # Additional fields
    message_id: str
    """Identifier created by the message creator."""

    context_id: NotRequired[str]
    """The context the message is associated with."""

    task_id: NotRequired[str]
    """Identifier of task the message is related to."""

    reference_task_ids: NotRequired[list[str]]
    """Array of task IDs this message references."""

    extensions: NotRequired[list[str]]
    """Array of extensions."""
```

#### role

```python
role: Literal['user', 'agent']
```

The role of the message.

#### parts

```python
parts: list[Part]
```

The parts of the message.

#### kind

```python
kind: Literal['message']
```

Event type.

#### metadata

```python
metadata: NotRequired[dict[str, Any]]
```

Metadata about the message.

#### message_id

```python
message_id: str
```

Identifier created by the message creator.

#### context_id

```python
context_id: NotRequired[str]
```

The context the message is associated with.

#### task_id

```python
task_id: NotRequired[str]
```

Identifier of task the message is related to.

#### reference_task_ids

```python
reference_task_ids: NotRequired[list[str]]
```

Array of task IDs this message references.

#### extensions

```python
extensions: NotRequired[list[str]]
```

Array of extensions.

### TextPart

Bases: `_BasePart`

A part that contains text.

Source code in `.venv/lib/python3.12/site-packages/fasta2a/schema.py`

```python
@pydantic.with_config({'alias_generator': to_camel})
class TextPart(_BasePart):
    """A part that contains text."""

    kind: Literal['text']
    """The kind of the part."""

    text: str
    """The text of the part."""
```

#### kind

```python
kind: Literal['text']
```

The kind of the part.

#### text

```python
text: str
```

The text of the part.

### FileWithBytes

Bases: `TypedDict`

File with base64 encoded data.

Source code in `.venv/lib/python3.12/site-packages/fasta2a/schema.py`

```python
@pydantic.with_config({'alias_generator': to_camel})
class FileWithBytes(TypedDict):
    """File with base64 encoded data."""

    bytes: str
    """The base64 encoded content of the file."""

    mime_type: NotRequired[str]
    """Optional mime type for the file."""
```

#### bytes

```python
bytes: str
```

The base64 encoded content of the file.

#### mime_type

```python
mime_type: NotRequired[str]
```

Optional mime type for the file.

### FileWithUri

Bases: `TypedDict`

File with URI reference.

Source code in `.venv/lib/python3.12/site-packages/fasta2a/schema.py`

```python
@pydantic.with_config({'alias_generator': to_camel})
class FileWithUri(TypedDict):
    """File with URI reference."""

    uri: str
    """The URI of the file."""

    mime_type: NotRequired[str]
    """The mime type of the file."""
```

#### uri

```python
uri: str
```

The URI of the file.

#### mime_type

```python
mime_type: NotRequired[str]
```

The mime type of the file.

### FilePart

Bases: `_BasePart`

A part that contains a file.

Source code in `.venv/lib/python3.12/site-packages/fasta2a/schema.py`

```python
@pydantic.with_config({'alias_generator': to_camel})
class FilePart(_BasePart):
    """A part that contains a file."""

    kind: Literal['file']
    """The kind of the part."""

    file: FileWithBytes | FileWithUri
    """The file content - either bytes or URI."""
```

#### kind

```python
kind: Literal['file']
```

The kind of the part.

#### file

```python
file: FileWithBytes | FileWithUri
```

The file content - either bytes or URI.

### DataPart

Bases: `_BasePart`

A part that contains structured data.

Source code in `.venv/lib/python3.12/site-packages/fasta2a/schema.py`

```python
@pydantic.with_config({'alias_generator': to_camel})
class DataPart(_BasePart):
    """A part that contains structured data."""

    kind: Literal['data']
    """The kind of the part."""

    data: dict[str, Any]
    """The data of the part."""
```

#### kind

```python
kind: Literal['data']
```

The kind of the part.

#### data

```python
data: dict[str, Any]
```

The data of the part.

### Part

```python
Part = Annotated[
    Union[TextPart, FilePart, DataPart],
    Field(discriminator="kind"),
]
```

A fully formed piece of content exchanged between a client and a remote agent as part of a Message or an Artifact.

Each Part has its own content type and metadata.

### TaskState

```python
TaskState: TypeAlias = Literal[
    "submitted",
    "working",
    "input-required",
    "completed",
    "canceled",
    "failed",
    "rejected",
    "auth-required",
    "unknown",
]
```

The possible states of a task.

### TaskStatus

Bases: `TypedDict`

Status and accompanying message for a task.

Source code in `.venv/lib/python3.12/site-packages/fasta2a/schema.py`

```python
@pydantic.with_config({'alias_generator': to_camel})
class TaskStatus(TypedDict):
    """Status and accompanying message for a task."""

    state: TaskState
    """The current state of the task."""

    message: NotRequired[Message]
    """Additional status updates for client."""

    timestamp: NotRequired[str]
    """ISO datetime value of when the status was updated."""
```

#### state

```python
state: TaskState
```

The current state of the task.

#### message

```python
message: NotRequired[Message]
```

Additional status updates for client.

#### timestamp

```python
timestamp: NotRequired[str]
```

ISO datetime value of when the status was updated.

### Task

Bases: `TypedDict`

A Task is a stateful entity that allows Clients and Remote Agents to achieve a specific outcome.

Clients and Remote Agents exchange Messages within a Task. Remote Agents generate results as Artifacts. A Task is always created by a Client and the status is always determined by the Remote Agent.

Source code in `.venv/lib/python3.12/site-packages/fasta2a/schema.py`

```python
@pydantic.with_config({'alias_generator': to_camel})
class Task(TypedDict):
    """A Task is a stateful entity that allows Clients and Remote Agents to achieve a specific outcome.

    Clients and Remote Agents exchange Messages within a Task. Remote Agents generate results as Artifacts.
    A Task is always created by a Client and the status is always determined by the Remote Agent.
    """

    id: str
    """Unique identifier for the task."""

    context_id: str
    """The context the task is associated with."""

    kind: Literal['task']
    """Event type."""

    status: TaskStatus
    """Current status of the task."""

    history: NotRequired[list[Message]]
    """Optional history of messages."""

    artifacts: NotRequired[list[Artifact]]
    """Collection of artifacts created by the agent."""

    metadata: NotRequired[dict[str, Any]]
    """Extension metadata."""
```

#### id

```python
id: str
```

Unique identifier for the task.

#### context_id

```python
context_id: str
```

The context the task is associated with.

#### kind

```python
kind: Literal['task']
```

Event type.

#### status

```python
status: TaskStatus
```

Current status of the task.

#### history

```python
history: NotRequired[list[Message]]
```

Optional history of messages.

#### artifacts

```python
artifacts: NotRequired[list[Artifact]]
```

Collection of artifacts created by the agent.

#### metadata

```python
metadata: NotRequired[dict[str, Any]]
```

Extension metadata.

### TaskStatusUpdateEvent

Bases: `TypedDict`

Sent by server during message/stream requests.

Source code in `.venv/lib/python3.12/site-packages/fasta2a/schema.py`

```python
@pydantic.with_config({'alias_generator': to_camel})
class TaskStatusUpdateEvent(TypedDict):
    """Sent by server during message/stream requests."""

    task_id: str
    """The id of the task."""

    context_id: str
    """The context the task is associated with."""

    kind: Literal['status-update']
    """Event type."""

    status: TaskStatus
    """The status of the task."""

    final: bool
    """Indicates the end of the event stream."""

    metadata: NotRequired[dict[str, Any]]
    """Extension metadata."""
```

#### task_id

```python
task_id: str
```

The id of the task.

#### context_id

```python
context_id: str
```

The context the task is associated with.

#### kind

```python
kind: Literal['status-update']
```

Event type.

#### status

```python
status: TaskStatus
```

The status of the task.

#### final

```python
final: bool
```

Indicates the end of the event stream.

#### metadata

```python
metadata: NotRequired[dict[str, Any]]
```

Extension metadata.

### TaskArtifactUpdateEvent

Bases: `TypedDict`

Sent by server during message/stream requests.

Source code in `.venv/lib/python3.12/site-packages/fasta2a/schema.py`

```python
@pydantic.with_config({'alias_generator': to_camel})
class TaskArtifactUpdateEvent(TypedDict):
    """Sent by server during message/stream requests."""

    task_id: str
    """The id of the task."""

    context_id: str
    """The context the task is associated with."""

    kind: Literal['artifact-update']
    """Event type identification."""

    artifact: Artifact
    """The artifact that was updated."""

    append: NotRequired[bool]
    """Whether to append to existing artifact (true) or replace (false)."""

    last_chunk: NotRequired[bool]
    """Indicates this is the final chunk of the artifact."""

    metadata: NotRequired[dict[str, Any]]
    """Extension metadata."""
```

#### task_id

```python
task_id: str
```

The id of the task.

#### context_id

```python
context_id: str
```

The context the task is associated with.

#### kind

```python
kind: Literal['artifact-update']
```

Event type identification.

#### artifact

```python
artifact: Artifact
```

The artifact that was updated.

#### append

```python
append: NotRequired[bool]
```

Whether to append to existing artifact (true) or replace (false).

#### last_chunk

```python
last_chunk: NotRequired[bool]
```

Indicates this is the final chunk of the artifact.

#### metadata

```python
metadata: NotRequired[dict[str, Any]]
```

Extension metadata.

### TaskIdParams

Bases: `TypedDict`

Parameters for a task id.

Source code in `.venv/lib/python3.12/site-packages/fasta2a/schema.py`

```python
@pydantic.with_config({'alias_generator': to_camel})
class TaskIdParams(TypedDict):
    """Parameters for a task id."""

    id: str
    """The unique identifier for the task."""

    metadata: NotRequired[dict[str, Any]]
    """Optional metadata associated with the request."""
```

#### id

```python
id: str
```

The unique identifier for the task.

#### metadata

```python
metadata: NotRequired[dict[str, Any]]
```

Optional metadata associated with the request.

### TaskQueryParams

Bases: `TaskIdParams`

Query parameters for a task.

Source code in `.venv/lib/python3.12/site-packages/fasta2a/schema.py`

```python
@pydantic.with_config({'alias_generator': to_camel})
class TaskQueryParams(TaskIdParams):
    """Query parameters for a task."""

    history_length: NotRequired[int]
    """Number of recent messages to be retrieved."""
```

#### history_length

```python
history_length: NotRequired[int]
```

Number of recent messages to be retrieved.

### MessageSendConfiguration

Bases: `TypedDict`

Configuration for the send message request.

Source code in `.venv/lib/python3.12/site-packages/fasta2a/schema.py`

```python
@pydantic.with_config({'alias_generator': to_camel})
class MessageSendConfiguration(TypedDict):
    """Configuration for the send message request."""

    accepted_output_modes: list[str]
    """Accepted output modalities by the client."""

    blocking: NotRequired[bool]
    """If the server should treat the client as a blocking request."""

    history_length: NotRequired[int]
    """Number of recent messages to be retrieved."""

    push_notification_config: NotRequired[PushNotificationConfig]
    """Where the server should send notifications when disconnected."""
```

#### accepted_output_modes

```python
accepted_output_modes: list[str]
```

Accepted output modalities by the client.

#### blocking

```python
blocking: NotRequired[bool]
```

If the server should treat the client as a blocking request.

#### history_length

```python
history_length: NotRequired[int]
```

Number of recent messages to be retrieved.

#### push_notification_config

```python
push_notification_config: NotRequired[
    PushNotificationConfig
]
```

Where the server should send notifications when disconnected.

### MessageSendParams

Bases: `TypedDict`

Parameters for message/send method.

Source code in `.venv/lib/python3.12/site-packages/fasta2a/schema.py`

```python
@pydantic.with_config({'alias_generator': to_camel})
class MessageSendParams(TypedDict):
    """Parameters for message/send method."""

    configuration: NotRequired[MessageSendConfiguration]
    """Send message configuration."""

    message: Message
    """The message being sent to the server."""

    metadata: NotRequired[dict[str, Any]]
    """Extension metadata."""
```

#### configuration

```python
configuration: NotRequired[MessageSendConfiguration]
```

Send message configuration.

#### message

```python
message: Message
```

The message being sent to the server.

#### metadata

```python
metadata: NotRequired[dict[str, Any]]
```

Extension metadata.

### TaskSendParams

Bases: `TypedDict`

Internal parameters for task execution within the framework.

Note: This is not part of the A2A protocol - it's used internally for broker/worker communication.

Source code in `.venv/lib/python3.12/site-packages/fasta2a/schema.py`

```python
@pydantic.with_config({'alias_generator': to_camel})
class TaskSendParams(TypedDict):
    """Internal parameters for task execution within the framework.

    Note: This is not part of the A2A protocol - it's used internally
    for broker/worker communication.
    """

    id: str
    """The id of the task."""

    context_id: str
    """The context id for the task."""

    message: Message
    """The message to process."""

    history_length: NotRequired[int]
    """Number of recent messages to be retrieved."""

    metadata: NotRequired[dict[str, Any]]
    """Extension metadata."""
```

#### id

```python
id: str
```

The id of the task.

#### context_id

```python
context_id: str
```

The context id for the task.

#### message

```python
message: Message
```

The message to process.

#### history_length

```python
history_length: NotRequired[int]
```

Number of recent messages to be retrieved.

#### metadata

```python
metadata: NotRequired[dict[str, Any]]
```

Extension metadata.

### ListTaskPushNotificationConfigParams

Bases: `TypedDict`

Parameters for getting list of pushNotificationConfigurations associated with a Task.

Source code in `.venv/lib/python3.12/site-packages/fasta2a/schema.py`

```python
@pydantic.with_config({'alias_generator': to_camel})
class ListTaskPushNotificationConfigParams(TypedDict):
    """Parameters for getting list of pushNotificationConfigurations associated with a Task."""

    id: str
    """Task id."""

    metadata: NotRequired[dict[str, Any]]
    """Extension metadata."""
```

#### id

```python
id: str
```

Task id.

#### metadata

```python
metadata: NotRequired[dict[str, Any]]
```

Extension metadata.

### DeleteTaskPushNotificationConfigParams

Bases: `TypedDict`

Parameters for removing pushNotificationConfiguration associated with a Task.

Source code in `.venv/lib/python3.12/site-packages/fasta2a/schema.py`

```python
@pydantic.with_config({'alias_generator': to_camel})
class DeleteTaskPushNotificationConfigParams(TypedDict):
    """Parameters for removing pushNotificationConfiguration associated with a Task."""

    id: str
    """Task id."""

    push_notification_config_id: str
    """The push notification config id to delete."""

    metadata: NotRequired[dict[str, Any]]
    """Extension metadata."""
```

#### id

```python
id: str
```

Task id.

#### push_notification_config_id

```python
push_notification_config_id: str
```

The push notification config id to delete.

#### metadata

```python
metadata: NotRequired[dict[str, Any]]
```

Extension metadata.

### JSONRPCMessage

Bases: `TypedDict`

A JSON RPC message.

Source code in `.venv/lib/python3.12/site-packages/fasta2a/schema.py`

```python
class JSONRPCMessage(TypedDict):
    """A JSON RPC message."""

    jsonrpc: Literal['2.0']
    """The JSON RPC version."""

    id: int | str | None
    """The request id."""
```

#### jsonrpc

```python
jsonrpc: Literal['2.0']
```

The JSON RPC version.

#### id

```python
id: int | str | None
```

The request id.

### JSONRPCRequest

Bases: `JSONRPCMessage`, `Generic[Method, Params]`

A JSON RPC request.

Source code in `.venv/lib/python3.12/site-packages/fasta2a/schema.py`

```python
class JSONRPCRequest(JSONRPCMessage, Generic[Method, Params]):
    """A JSON RPC request."""

    method: Method
    """The method to call."""

    params: Params
    """The parameters to pass to the method."""
```

#### method

```python
method: Method
```

The method to call.

#### params

```python
params: Params
```

The parameters to pass to the method.

### JSONRPCError

Bases: `TypedDict`, `Generic[CodeT, MessageT]`

A JSON RPC error.

Source code in `.venv/lib/python3.12/site-packages/fasta2a/schema.py`

```python
class JSONRPCError(TypedDict, Generic[CodeT, MessageT]):
    """A JSON RPC error."""

    code: CodeT
    """A number that indicates the error type that occurred."""

    message: MessageT
    """A string providing a short description of the error."""

    data: NotRequired[Any]
    """A primitive or structured value containing additional information about the error."""
```

#### code

```python
code: CodeT
```

A number that indicates the error type that occurred.

#### message

```python
message: MessageT
```

A string providing a short description of the error.

#### data

```python
data: NotRequired[Any]
```

A primitive or structured value containing additional information about the error.

### JSONRPCResponse

Bases: `JSONRPCMessage`, `Generic[ResultT, ErrorT]`

A JSON RPC response.

Source code in `.venv/lib/python3.12/site-packages/fasta2a/schema.py`

```python
class JSONRPCResponse(JSONRPCMessage, Generic[ResultT, ErrorT]):
    """A JSON RPC response."""

    result: NotRequired[ResultT]
    error: NotRequired[ErrorT]
```

### JSONParseError

```python
JSONParseError = JSONRPCError[
    Literal[-32700], Literal["Invalid JSON payload"]
]
```

A JSON RPC error for a parse error.

### InvalidRequestError

```python
InvalidRequestError = JSONRPCError[
    Literal[-32600],
    Literal["Request payload validation error"],
]
```

A JSON RPC error for an invalid request.

### MethodNotFoundError

```python
MethodNotFoundError = JSONRPCError[
    Literal[-32601], Literal["Method not found"]
]
```

A JSON RPC error for a method not found.

### InvalidParamsError

```python
InvalidParamsError = JSONRPCError[
    Literal[-32602], Literal["Invalid parameters"]
]
```

A JSON RPC error for invalid parameters.

### InternalError

```python
InternalError = JSONRPCError[
    Literal[-32603], Literal["Internal error"]
]
```

A JSON RPC error for an internal error.

### TaskNotFoundError

```python
TaskNotFoundError = JSONRPCError[
    Literal[-32001], Literal["Task not found"]
]
```

A JSON RPC error for a task not found.

### TaskNotCancelableError

```python
TaskNotCancelableError = JSONRPCError[
    Literal[-32002], Literal["Task not cancelable"]
]
```

A JSON RPC error for a task not cancelable.

### PushNotificationNotSupportedError

```python
PushNotificationNotSupportedError = JSONRPCError[
    Literal[-32003],
    Literal["Push notification not supported"],
]
```

A JSON RPC error for a push notification not supported.

### UnsupportedOperationError

```python
UnsupportedOperationError = JSONRPCError[
    Literal[-32004],
    Literal["This operation is not supported"],
]
```

A JSON RPC error for an unsupported operation.

### ContentTypeNotSupportedError

```python
ContentTypeNotSupportedError = JSONRPCError[
    Literal[-32005], Literal["Incompatible content types"]
]
```

A JSON RPC error for incompatible content types.

### InvalidAgentResponseError

```python
InvalidAgentResponseError = JSONRPCError[
    Literal[-32006], Literal["Invalid agent response"]
]
```

A JSON RPC error for invalid agent response.

### SendMessageRequest

```python
SendMessageRequest = JSONRPCRequest[
    Literal["message/send"], MessageSendParams
]
```

A JSON RPC request to send a message.

### SendMessageResponse

```python
SendMessageResponse = JSONRPCResponse[
    Union[Task, Message], JSONRPCError[Any, Any]
]
```

A JSON RPC response to send a message.

### StreamMessageRequest

```python
StreamMessageRequest = JSONRPCRequest[
    Literal["message/stream"], MessageSendParams
]
```

A JSON RPC request to stream a message.

### StreamMessageResponse

```python
StreamMessageResponse = JSONRPCResponse[
    Union[
        Task,
        Message,
        TaskStatusUpdateEvent,
        TaskArtifactUpdateEvent,
    ],
    JSONRPCError[Any, Any],
]
```

A JSON RPC response to a StreamMessageRequest.

### GetTaskRequest

```python
GetTaskRequest = JSONRPCRequest[
    Literal["tasks/get"], TaskQueryParams
]
```

A JSON RPC request to get a task.

### GetTaskResponse

```python
GetTaskResponse = JSONRPCResponse[Task, TaskNotFoundError]
```

A JSON RPC response to get a task.

### CancelTaskRequest

```python
CancelTaskRequest = JSONRPCRequest[
    Literal["tasks/cancel"], TaskIdParams
]
```

A JSON RPC request to cancel a task.

### CancelTaskResponse

```python
CancelTaskResponse = JSONRPCResponse[
    Task, Union[TaskNotCancelableError, TaskNotFoundError]
]
```

A JSON RPC response to cancel a task.

### SetTaskPushNotificationRequest

```python
SetTaskPushNotificationRequest = JSONRPCRequest[
    Literal["tasks/pushNotification/set"],
    TaskPushNotificationConfig,
]
```

A JSON RPC request to set a task push notification.

### SetTaskPushNotificationResponse

```python
SetTaskPushNotificationResponse = JSONRPCResponse[
    TaskPushNotificationConfig,
    PushNotificationNotSupportedError,
]
```

A JSON RPC response to set a task push notification.

### GetTaskPushNotificationRequest

```python
GetTaskPushNotificationRequest = JSONRPCRequest[
    Literal["tasks/pushNotification/get"], TaskIdParams
]
```

A JSON RPC request to get a task push notification.

### GetTaskPushNotificationResponse

```python
GetTaskPushNotificationResponse = JSONRPCResponse[
    TaskPushNotificationConfig,
    PushNotificationNotSupportedError,
]
```

A JSON RPC response to get a task push notification.

### ResubscribeTaskRequest

```python
ResubscribeTaskRequest = JSONRPCRequest[
    Literal["tasks/resubscribe"], TaskIdParams
]
```

A JSON RPC request to resubscribe to a task.

### ListTaskPushNotificationConfigRequest

```python
ListTaskPushNotificationConfigRequest = JSONRPCRequest[
    Literal["tasks/pushNotificationConfig/list"],
    ListTaskPushNotificationConfigParams,
]
```

A JSON RPC request to list task push notification configs.

### DeleteTaskPushNotificationConfigRequest

```python
DeleteTaskPushNotificationConfigRequest = JSONRPCRequest[
    Literal["tasks/pushNotificationConfig/delete"],
    DeleteTaskPushNotificationConfigParams,
]
```

A JSON RPC request to delete a task push notification config.

### A2ARequest

```python
A2ARequest = Annotated[
    Union[
        SendMessageRequest,
        StreamMessageRequest,
        GetTaskRequest,
        CancelTaskRequest,
        SetTaskPushNotificationRequest,
        GetTaskPushNotificationRequest,
        ResubscribeTaskRequest,
        ListTaskPushNotificationConfigRequest,
        DeleteTaskPushNotificationConfigRequest,
    ],
    Discriminator("method"),
]
```

A JSON RPC request to the A2A server.

### A2AResponse

```python
A2AResponse: TypeAlias = Union[
    SendMessageResponse,
    StreamMessageResponse,
    GetTaskResponse,
    CancelTaskResponse,
    SetTaskPushNotificationResponse,
    GetTaskPushNotificationResponse,
]
```

A JSON RPC response from the A2A server.

### A2AClient

A client for the A2A protocol.

Source code in `.venv/lib/python3.12/site-packages/fasta2a/client.py`

```python
class A2AClient:
    """A client for the A2A protocol."""

    def __init__(self, base_url: str = 'http://localhost:8000', http_client: httpx.AsyncClient | None = None) -> None:
        if http_client is None:
            self.http_client = httpx.AsyncClient(base_url=base_url)
        else:
            self.http_client = http_client
            self.http_client.base_url = base_url

    async def send_message(
        self,
        message: Message,
        *,
        metadata: dict[str, Any] | None = None,
        configuration: MessageSendConfiguration | None = None,
    ) -> SendMessageResponse:
        """Send a message using the A2A protocol.

        Returns a JSON-RPC response containing either a result (Task) or an error.
        """
        params = MessageSendParams(message=message)
        if metadata is not None:
            params['metadata'] = metadata
        if configuration is not None:
            params['configuration'] = configuration

        request_id = str(uuid.uuid4())
        payload = SendMessageRequest(jsonrpc='2.0', id=request_id, method='message/send', params=params)
        content = send_message_request_ta.dump_json(payload, by_alias=True)
        response = await self.http_client.post('/', content=content, headers={'Content-Type': 'application/json'})
        self._raise_for_status(response)

        return send_message_response_ta.validate_json(response.content)

    async def get_task(self, task_id: str) -> GetTaskResponse:
        payload = GetTaskRequest(jsonrpc='2.0', id=None, method='tasks/get', params={'id': task_id})
        content = a2a_request_ta.dump_json(payload, by_alias=True)
        response = await self.http_client.post('/', content=content, headers={'Content-Type': 'application/json'})
        self._raise_for_status(response)
        return get_task_response_ta.validate_json(response.content)

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code >= 400:
            raise UnexpectedResponseError(response.status_code, response.text)
```

#### send_message

```python
send_message(
    message: Message,
    *,
    metadata: dict[str, Any] | None = None,
    configuration: MessageSendConfiguration | None = None
) -> SendMessageResponse
```

Send a message using the A2A protocol.

Returns a JSON-RPC response containing either a result (Task) or an error.

Source code in `.venv/lib/python3.12/site-packages/fasta2a/client.py`

```python
async def send_message(
    self,
    message: Message,
    *,
    metadata: dict[str, Any] | None = None,
    configuration: MessageSendConfiguration | None = None,
) -> SendMessageResponse:
    """Send a message using the A2A protocol.

    Returns a JSON-RPC response containing either a result (Task) or an error.
    """
    params = MessageSendParams(message=message)
    if metadata is not None:
        params['metadata'] = metadata
    if configuration is not None:
        params['configuration'] = configuration

    request_id = str(uuid.uuid4())
    payload = SendMessageRequest(jsonrpc='2.0', id=request_id, method='message/send', params=params)
    content = send_message_request_ta.dump_json(payload, by_alias=True)
    response = await self.http_client.post('/', content=content, headers={'Content-Type': 'application/json'})
    self._raise_for_status(response)

    return send_message_response_ta.validate_json(response.content)
```

### UnexpectedResponseError

Bases: `Exception`

An error raised when an unexpected response is received from the server.

Source code in `.venv/lib/python3.12/site-packages/fasta2a/client.py`

```python
class UnexpectedResponseError(Exception):
    """An error raised when an unexpected response is received from the server."""

    def __init__(self, status_code: int, content: str) -> None:
        self.status_code = status_code
        self.content = content
```
