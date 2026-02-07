# `pydantic_ai` â€” Concurrency

Bases: `WrapperModel`

A model wrapper that limits concurrent requests to the underlying model.

This wrapper applies concurrency limiting at the model level, ensuring that the number of concurrent requests to the model does not exceed the configured limit. This is useful for:

- Respecting API rate limits
- Managing resource usage
- Sharing a concurrency pool across multiple models

Example usage:

```python
from pydantic_ai import Agent
from pydantic_ai.models.concurrency import ConcurrencyLimitedModel

# Limit to 5 concurrent requests
model = ConcurrencyLimitedModel('openai:gpt-4o', limiter=5)
agent = Agent(model)

# Or share a limiter across multiple models
from pydantic_ai import ConcurrencyLimiter  # noqa E402

shared_limiter = ConcurrencyLimiter(max_running=10, name='openai-pool')
model1 = ConcurrencyLimitedModel('openai:gpt-4o', limiter=shared_limiter)
model2 = ConcurrencyLimitedModel('openai:gpt-4o-mini', limiter=shared_limiter)
```

Source code in `pydantic_ai_slim/pydantic_ai/models/concurrency.py`

````python
@dataclass(init=False)
class ConcurrencyLimitedModel(WrapperModel):
    """A model wrapper that limits concurrent requests to the underlying model.

    This wrapper applies concurrency limiting at the model level, ensuring that
    the number of concurrent requests to the model does not exceed the configured
    limit. This is useful for:

    - Respecting API rate limits
    - Managing resource usage
    - Sharing a concurrency pool across multiple models

    Example usage:
    ```python
    from pydantic_ai import Agent
    from pydantic_ai.models.concurrency import ConcurrencyLimitedModel

    # Limit to 5 concurrent requests
    model = ConcurrencyLimitedModel('openai:gpt-4o', limiter=5)
    agent = Agent(model)

    # Or share a limiter across multiple models
    from pydantic_ai import ConcurrencyLimiter  # noqa E402

    shared_limiter = ConcurrencyLimiter(max_running=10, name='openai-pool')
    model1 = ConcurrencyLimitedModel('openai:gpt-4o', limiter=shared_limiter)
    model2 = ConcurrencyLimitedModel('openai:gpt-4o-mini', limiter=shared_limiter)
    ```
    """

    _limiter: AbstractConcurrencyLimiter

    def __init__(
        self,
        wrapped: Model | KnownModelName,
        limiter: int | ConcurrencyLimit | AbstractConcurrencyLimiter,
    ):
        """Initialize the ConcurrencyLimitedModel.

        Args:
            wrapped: The model to wrap, either a Model instance or a known model name.
            limiter: The concurrency limit configuration. Can be:
                - An `int`: Simple limit on concurrent operations (unlimited queue).
                - A `ConcurrencyLimit`: Full configuration with optional backpressure.
                - An `AbstractConcurrencyLimiter`: A pre-created limiter for sharing across models.
        """
        super().__init__(wrapped)
        if isinstance(limiter, AbstractConcurrencyLimiter):
            self._limiter = limiter
        else:
            self._limiter = ConcurrencyLimiter.from_limit(limiter)

    async def request(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> ModelResponse:
        """Make a request to the model with concurrency limiting."""
        async with get_concurrency_context(self._limiter, f'model:{self.model_name}'):
            return await self.wrapped.request(messages, model_settings, model_request_parameters)

    async def count_tokens(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> RequestUsage:
        """Count tokens with concurrency limiting."""
        async with get_concurrency_context(self._limiter, f'model:{self.model_name}'):
            return await self.wrapped.count_tokens(messages, model_settings, model_request_parameters)

    @asynccontextmanager
    async def request_stream(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
        run_context: RunContext[Any] | None = None,
    ) -> AsyncIterator[StreamedResponse]:
        """Make a streaming request to the model with concurrency limiting."""
        async with get_concurrency_context(self._limiter, f'model:{self.model_name}'):
            async with self.wrapped.request_stream(
                messages, model_settings, model_request_parameters, run_context
            ) as response_stream:
                yield response_stream
````

### __init__

```python
__init__(
    wrapped: Model | KnownModelName,
    limiter: (
        int | ConcurrencyLimit | AbstractConcurrencyLimiter
    ),
)
```

Initialize the ConcurrencyLimitedModel.

Parameters:

| Name      | Type    | Description      | Default                                                           |
| --------- | ------- | ---------------- | ----------------------------------------------------------------- |
| `wrapped` | \`Model | KnownModelName\` | The model to wrap, either a Model instance or a known model name. |
| `limiter` | \`int   | ConcurrencyLimit | AbstractConcurrencyLimiter\`                                      |

Source code in `pydantic_ai_slim/pydantic_ai/models/concurrency.py`

```python
def __init__(
    self,
    wrapped: Model | KnownModelName,
    limiter: int | ConcurrencyLimit | AbstractConcurrencyLimiter,
):
    """Initialize the ConcurrencyLimitedModel.

    Args:
        wrapped: The model to wrap, either a Model instance or a known model name.
        limiter: The concurrency limit configuration. Can be:
            - An `int`: Simple limit on concurrent operations (unlimited queue).
            - A `ConcurrencyLimit`: Full configuration with optional backpressure.
            - An `AbstractConcurrencyLimiter`: A pre-created limiter for sharing across models.
    """
    super().__init__(wrapped)
    if isinstance(limiter, AbstractConcurrencyLimiter):
        self._limiter = limiter
    else:
        self._limiter = ConcurrencyLimiter.from_limit(limiter)
```

### request

```python
request(
    messages: list[ModelMessage],
    model_settings: ModelSettings | None,
    model_request_parameters: ModelRequestParameters,
) -> ModelResponse
```

Make a request to the model with concurrency limiting.

Source code in `pydantic_ai_slim/pydantic_ai/models/concurrency.py`

```python
async def request(
    self,
    messages: list[ModelMessage],
    model_settings: ModelSettings | None,
    model_request_parameters: ModelRequestParameters,
) -> ModelResponse:
    """Make a request to the model with concurrency limiting."""
    async with get_concurrency_context(self._limiter, f'model:{self.model_name}'):
        return await self.wrapped.request(messages, model_settings, model_request_parameters)
```

### count_tokens

```python
count_tokens(
    messages: list[ModelMessage],
    model_settings: ModelSettings | None,
    model_request_parameters: ModelRequestParameters,
) -> RequestUsage
```

Count tokens with concurrency limiting.

Source code in `pydantic_ai_slim/pydantic_ai/models/concurrency.py`

```python
async def count_tokens(
    self,
    messages: list[ModelMessage],
    model_settings: ModelSettings | None,
    model_request_parameters: ModelRequestParameters,
) -> RequestUsage:
    """Count tokens with concurrency limiting."""
    async with get_concurrency_context(self._limiter, f'model:{self.model_name}'):
        return await self.wrapped.count_tokens(messages, model_settings, model_request_parameters)
```

### request_stream

```python
request_stream(
    messages: list[ModelMessage],
    model_settings: ModelSettings | None,
    model_request_parameters: ModelRequestParameters,
    run_context: RunContext[Any] | None = None,
) -> AsyncIterator[StreamedResponse]
```

Make a streaming request to the model with concurrency limiting.

Source code in `pydantic_ai_slim/pydantic_ai/models/concurrency.py`

```python
@asynccontextmanager
async def request_stream(
    self,
    messages: list[ModelMessage],
    model_settings: ModelSettings | None,
    model_request_parameters: ModelRequestParameters,
    run_context: RunContext[Any] | None = None,
) -> AsyncIterator[StreamedResponse]:
    """Make a streaming request to the model with concurrency limiting."""
    async with get_concurrency_context(self._limiter, f'model:{self.model_name}'):
        async with self.wrapped.request_stream(
            messages, model_settings, model_request_parameters, run_context
        ) as response_stream:
            yield response_stream
```

Wrap a model with concurrency limiting.

This is a convenience function to wrap a model with concurrency limiting. If the limiter is None, the model is returned unchanged.

Parameters:

| Name      | Type                  | Description                          | Default            |
| --------- | --------------------- | ------------------------------------ | ------------------ |
| `model`   | \`Model               | KnownModelName\`                     | The model to wrap. |
| `limiter` | `AnyConcurrencyLimit` | The concurrency limit configuration. | *required*         |

Returns:

| Type    | Description                                                                            |
| ------- | -------------------------------------------------------------------------------------- |
| `Model` | The wrapped model with concurrency limiting, or the original model if limiter is None. |

Example:

```python
from pydantic_ai.models.concurrency import limit_model_concurrency

model = limit_model_concurrency('openai:gpt-4o', limiter=5)
```

Source code in `pydantic_ai_slim/pydantic_ai/models/concurrency.py`

````python
def limit_model_concurrency(
    model: Model | KnownModelName,
    limiter: AnyConcurrencyLimit,
) -> Model:
    """Wrap a model with concurrency limiting.

    This is a convenience function to wrap a model with concurrency limiting.
    If the limiter is None, the model is returned unchanged.

    Args:
        model: The model to wrap.
        limiter: The concurrency limit configuration.

    Returns:
        The wrapped model with concurrency limiting, or the original model if limiter is None.

    Example:
    ```python
    from pydantic_ai.models.concurrency import limit_model_concurrency

    model = limit_model_concurrency('openai:gpt-4o', limiter=5)
    ```
    """
    normalized_limiter = normalize_to_limiter(limiter)
    if normalized_limiter is None:
        from . import infer_model

        return infer_model(model) if isinstance(model, str) else model
    return ConcurrencyLimitedModel(model, normalized_limiter)
````

Bases: `ABC`

Abstract base class for concurrency limiters.

Subclass this to create custom concurrency limiters (e.g., Redis-backed distributed limiters).

Example:

```python
from pydantic_ai.concurrency import AbstractConcurrencyLimiter


class RedisConcurrencyLimiter(AbstractConcurrencyLimiter):
    def __init__(self, redis_client, key: str, max_running: int):
        self._redis = redis_client
        self._key = key
        self._max_running = max_running

    async def acquire(self, source: str) -> None:
        # Implement Redis-based distributed locking
        ...

    def release(self) -> None:
        # Release the Redis lock
        ...
```

Source code in `pydantic_ai_slim/pydantic_ai/concurrency.py`

````python
class AbstractConcurrencyLimiter(ABC):
    """Abstract base class for concurrency limiters.

    Subclass this to create custom concurrency limiters
    (e.g., Redis-backed distributed limiters).

    Example:
    ```python
    from pydantic_ai.concurrency import AbstractConcurrencyLimiter


    class RedisConcurrencyLimiter(AbstractConcurrencyLimiter):
        def __init__(self, redis_client, key: str, max_running: int):
            self._redis = redis_client
            self._key = key
            self._max_running = max_running

        async def acquire(self, source: str) -> None:
            # Implement Redis-based distributed locking
            ...

        def release(self) -> None:
            # Release the Redis lock
            ...
    ```
    """

    @abstractmethod
    async def acquire(self, source: str) -> None:
        """Acquire a slot, waiting if necessary.

        Args:
            source: Identifier for observability (e.g., 'model:gpt-4o').
        """
        ...

    @abstractmethod
    def release(self) -> None:
        """Release a slot."""
        ...
````

### acquire

```python
acquire(source: str) -> None
```

Acquire a slot, waiting if necessary.

Parameters:

| Name     | Type  | Description                                          | Default    |
| -------- | ----- | ---------------------------------------------------- | ---------- |
| `source` | `str` | Identifier for observability (e.g., 'model:gpt-4o'). | *required* |

Source code in `pydantic_ai_slim/pydantic_ai/concurrency.py`

```python
@abstractmethod
async def acquire(self, source: str) -> None:
    """Acquire a slot, waiting if necessary.

    Args:
        source: Identifier for observability (e.g., 'model:gpt-4o').
    """
    ...
```

### release

```python
release() -> None
```

Release a slot.

Source code in `pydantic_ai_slim/pydantic_ai/concurrency.py`

```python
@abstractmethod
def release(self) -> None:
    """Release a slot."""
    ...
```

Bases: `AbstractConcurrencyLimiter`

A concurrency limiter that tracks waiting operations for observability.

This class wraps an anyio.CapacityLimiter and tracks the number of waiting operations. When an operation has to wait to acquire a slot, a span is created for observability purposes.

Source code in `pydantic_ai_slim/pydantic_ai/concurrency.py`

```python
class ConcurrencyLimiter(AbstractConcurrencyLimiter):
    """A concurrency limiter that tracks waiting operations for observability.

    This class wraps an anyio.CapacityLimiter and tracks the number of waiting operations.
    When an operation has to wait to acquire a slot, a span is created for
    observability purposes.
    """

    def __init__(
        self,
        max_running: int,
        *,
        max_queued: int | None = None,
        name: str | None = None,
        tracer: Tracer | None = None,
    ):
        """Initialize the ConcurrencyLimiter.

        Args:
            max_running: Maximum number of concurrent operations.
            max_queued: Maximum queue depth before raising ConcurrencyLimitExceeded.
            name: Optional name for this limiter, used for observability when sharing
                a limiter across multiple models or agents.
            tracer: OpenTelemetry tracer for span creation.
        """
        self._limiter = anyio.CapacityLimiter(max_running)
        self._max_queued = max_queued
        self._name = name
        self._tracer = tracer
        # Lock and counter to atomically check and track waiting tasks for max_queued enforcement
        self._queue_lock = anyio.Lock()
        self._waiting_count = 0

    @classmethod
    def from_limit(
        cls,
        limit: int | ConcurrencyLimit,
        *,
        name: str | None = None,
        tracer: Tracer | None = None,
    ) -> Self:
        """Create a ConcurrencyLimiter from a ConcurrencyLimit configuration.

        Args:
            limit: Either an int for simple limiting or a ConcurrencyLimit for full config.
            name: Optional name for this limiter, used for observability.
            tracer: OpenTelemetry tracer for span creation.

        Returns:
            A configured ConcurrencyLimiter.
        """
        if isinstance(limit, int):
            return cls(max_running=limit, name=name, tracer=tracer)
        else:
            return cls(
                max_running=limit.max_running,
                max_queued=limit.max_queued,
                name=name,
                tracer=tracer,
            )

    @property
    def name(self) -> str | None:
        """Name of the limiter for observability."""
        return self._name

    @property
    def waiting_count(self) -> int:
        """Number of operations currently waiting to acquire a slot."""
        return self._waiting_count

    @property
    def running_count(self) -> int:
        """Number of operations currently running."""
        return self._limiter.statistics().borrowed_tokens

    @property
    def available_count(self) -> int:
        """Number of slots available."""
        return int(self._limiter.available_tokens)

    @property
    def max_running(self) -> int:
        """Maximum concurrent operations allowed."""
        return int(self._limiter.total_tokens)

    def _get_tracer(self) -> Tracer:
        """Get the tracer, falling back to global tracer if not set."""
        if self._tracer is not None:
            return self._tracer
        return get_tracer('pydantic-ai')

    async def acquire(self, source: str) -> None:
        """Acquire a slot, creating a span if waiting is required.

        Args:
            source: Identifier for the source of this acquisition (e.g., 'agent:my-agent' or 'model:gpt-4').
        """
        from .exceptions import ConcurrencyLimitExceeded

        # Try to acquire immediately without blocking
        try:
            self._limiter.acquire_nowait()
            return
        except anyio.WouldBlock:
            pass

        # We need to wait - atomically check queue limits and register ourselves as waiting
        # This prevents a race condition where multiple tasks could pass the check before
        # any of them actually start waiting on the limiter
        async with self._queue_lock:
            if self._max_queued is not None and self._waiting_count >= self._max_queued:
                # Use limiter name if set, otherwise use source for error messages
                display_name = self._name or source
                raise ConcurrencyLimitExceeded(
                    f'Concurrency queue depth ({self._waiting_count + 1}) exceeds max_queued ({self._max_queued})'
                    + (f' for {display_name}' if display_name else '')
                )
            # Register ourselves as waiting before releasing the lock
            self._waiting_count += 1

        # Now we're registered as waiting, proceed to wait on the limiter
        # Use try/finally to ensure we decrement the counter even on cancellation
        try:
            # Create a span for observability while waiting
            tracer = self._get_tracer()
            display_name = self._name or source
            attributes: dict[str, str | int] = {
                'source': source,
                'waiting_count': self._waiting_count,
                'max_running': int(self._limiter.total_tokens),
            }
            if self._name is not None:
                attributes['limiter_name'] = self._name
            if self._max_queued is not None:
                attributes['max_queued'] = self._max_queued

            # Span name uses limiter name if set, otherwise source
            span_name = f'waiting for {display_name} concurrency'
            with tracer.start_as_current_span(span_name, attributes=attributes):
                await self._limiter.acquire()
        finally:
            # We're no longer waiting (either we acquired or we were cancelled)
            self._waiting_count -= 1

    def release(self) -> None:
        """Release a slot."""
        self._limiter.release()
```

### __init__

```python
__init__(
    max_running: int,
    *,
    max_queued: int | None = None,
    name: str | None = None,
    tracer: Tracer | None = None
)
```

Initialize the ConcurrencyLimiter.

Parameters:

| Name          | Type     | Description                              | Default                                                                                                         |
| ------------- | -------- | ---------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `max_running` | `int`    | Maximum number of concurrent operations. | *required*                                                                                                      |
| `max_queued`  | \`int    | None\`                                   | Maximum queue depth before raising ConcurrencyLimitExceeded.                                                    |
| `name`        | \`str    | None\`                                   | Optional name for this limiter, used for observability when sharing a limiter across multiple models or agents. |
| `tracer`      | \`Tracer | None\`                                   | OpenTelemetry tracer for span creation.                                                                         |

Source code in `pydantic_ai_slim/pydantic_ai/concurrency.py`

```python
def __init__(
    self,
    max_running: int,
    *,
    max_queued: int | None = None,
    name: str | None = None,
    tracer: Tracer | None = None,
):
    """Initialize the ConcurrencyLimiter.

    Args:
        max_running: Maximum number of concurrent operations.
        max_queued: Maximum queue depth before raising ConcurrencyLimitExceeded.
        name: Optional name for this limiter, used for observability when sharing
            a limiter across multiple models or agents.
        tracer: OpenTelemetry tracer for span creation.
    """
    self._limiter = anyio.CapacityLimiter(max_running)
    self._max_queued = max_queued
    self._name = name
    self._tracer = tracer
    # Lock and counter to atomically check and track waiting tasks for max_queued enforcement
    self._queue_lock = anyio.Lock()
    self._waiting_count = 0
```

### from_limit

```python
from_limit(
    limit: int | ConcurrencyLimit,
    *,
    name: str | None = None,
    tracer: Tracer | None = None
) -> Self
```

Create a ConcurrencyLimiter from a ConcurrencyLimit configuration.

Parameters:

| Name     | Type     | Description        | Default                                                                  |
| -------- | -------- | ------------------ | ------------------------------------------------------------------------ |
| `limit`  | \`int    | ConcurrencyLimit\` | Either an int for simple limiting or a ConcurrencyLimit for full config. |
| `name`   | \`str    | None\`             | Optional name for this limiter, used for observability.                  |
| `tracer` | \`Tracer | None\`             | OpenTelemetry tracer for span creation.                                  |

Returns:

| Type   | Description                      |
| ------ | -------------------------------- |
| `Self` | A configured ConcurrencyLimiter. |

Source code in `pydantic_ai_slim/pydantic_ai/concurrency.py`

```python
@classmethod
def from_limit(
    cls,
    limit: int | ConcurrencyLimit,
    *,
    name: str | None = None,
    tracer: Tracer | None = None,
) -> Self:
    """Create a ConcurrencyLimiter from a ConcurrencyLimit configuration.

    Args:
        limit: Either an int for simple limiting or a ConcurrencyLimit for full config.
        name: Optional name for this limiter, used for observability.
        tracer: OpenTelemetry tracer for span creation.

    Returns:
        A configured ConcurrencyLimiter.
    """
    if isinstance(limit, int):
        return cls(max_running=limit, name=name, tracer=tracer)
    else:
        return cls(
            max_running=limit.max_running,
            max_queued=limit.max_queued,
            name=name,
            tracer=tracer,
        )
```

### name

```python
name: str | None
```

Name of the limiter for observability.

### waiting_count

```python
waiting_count: int
```

Number of operations currently waiting to acquire a slot.

### running_count

```python
running_count: int
```

Number of operations currently running.

### available_count

```python
available_count: int
```

Number of slots available.

### max_running

```python
max_running: int
```

Maximum concurrent operations allowed.

### acquire

```python
acquire(source: str) -> None
```

Acquire a slot, creating a span if waiting is required.

Parameters:

| Name     | Type  | Description                                                                              | Default    |
| -------- | ----- | ---------------------------------------------------------------------------------------- | ---------- |
| `source` | `str` | Identifier for the source of this acquisition (e.g., 'agent:my-agent' or 'model:gpt-4'). | *required* |

Source code in `pydantic_ai_slim/pydantic_ai/concurrency.py`

```python
async def acquire(self, source: str) -> None:
    """Acquire a slot, creating a span if waiting is required.

    Args:
        source: Identifier for the source of this acquisition (e.g., 'agent:my-agent' or 'model:gpt-4').
    """
    from .exceptions import ConcurrencyLimitExceeded

    # Try to acquire immediately without blocking
    try:
        self._limiter.acquire_nowait()
        return
    except anyio.WouldBlock:
        pass

    # We need to wait - atomically check queue limits and register ourselves as waiting
    # This prevents a race condition where multiple tasks could pass the check before
    # any of them actually start waiting on the limiter
    async with self._queue_lock:
        if self._max_queued is not None and self._waiting_count >= self._max_queued:
            # Use limiter name if set, otherwise use source for error messages
            display_name = self._name or source
            raise ConcurrencyLimitExceeded(
                f'Concurrency queue depth ({self._waiting_count + 1}) exceeds max_queued ({self._max_queued})'
                + (f' for {display_name}' if display_name else '')
            )
        # Register ourselves as waiting before releasing the lock
        self._waiting_count += 1

    # Now we're registered as waiting, proceed to wait on the limiter
    # Use try/finally to ensure we decrement the counter even on cancellation
    try:
        # Create a span for observability while waiting
        tracer = self._get_tracer()
        display_name = self._name or source
        attributes: dict[str, str | int] = {
            'source': source,
            'waiting_count': self._waiting_count,
            'max_running': int(self._limiter.total_tokens),
        }
        if self._name is not None:
            attributes['limiter_name'] = self._name
        if self._max_queued is not None:
            attributes['max_queued'] = self._max_queued

        # Span name uses limiter name if set, otherwise source
        span_name = f'waiting for {display_name} concurrency'
        with tracer.start_as_current_span(span_name, attributes=attributes):
            await self._limiter.acquire()
    finally:
        # We're no longer waiting (either we acquired or we were cancelled)
        self._waiting_count -= 1
```

### release

```python
release() -> None
```

Release a slot.

Source code in `pydantic_ai_slim/pydantic_ai/concurrency.py`

```python
def release(self) -> None:
    """Release a slot."""
    self._limiter.release()
```

Configuration for concurrency limiting with optional backpressure.

Parameters:

| Name          | Type  | Description                                      | Default                                                                                                                           |
| ------------- | ----- | ------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------- |
| `max_running` | `int` | Maximum number of concurrent operations allowed. | *required*                                                                                                                        |
| `max_queued`  | \`int | None\`                                           | Maximum number of operations waiting in the queue. If None, the queue is unlimited. If exceeded, raises ConcurrencyLimitExceeded. |

Source code in `pydantic_ai_slim/pydantic_ai/concurrency.py`

```python
@dataclass
class ConcurrencyLimit:
    """Configuration for concurrency limiting with optional backpressure.

    Args:
        max_running: Maximum number of concurrent operations allowed.
        max_queued: Maximum number of operations waiting in the queue.
            If None, the queue is unlimited. If exceeded, raises `ConcurrencyLimitExceeded`.
    """

    max_running: int
    max_queued: int | None = None
```

Type alias for concurrency limit configuration.

Can be:

- An `int`: Simple limit on concurrent operations (unlimited queue).
- A `ConcurrencyLimit`: Full configuration with optional backpressure.
- An `AbstractConcurrencyLimiter`: A pre-created limiter instance for sharing across multiple models/agents.
- `None`: No concurrency limiting (default).

Bases: `AgentRunError`

Error raised when the concurrency queue depth exceeds max_queued.

Source code in `pydantic_ai_slim/pydantic_ai/exceptions.py`

```python
class ConcurrencyLimitExceeded(AgentRunError):
    """Error raised when the concurrency queue depth exceeds max_queued."""
```
