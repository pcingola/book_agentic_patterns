# `pydantic_ai.result`

### StreamedRunResult

Bases: `Generic[AgentDepsT, OutputDataT]`

Result of a streamed run that returns structured data via a tool call.

Source code in `pydantic_ai_slim/pydantic_ai/result.py`

```python
@dataclass(init=False)
class StreamedRunResult(Generic[AgentDepsT, OutputDataT]):
    """Result of a streamed run that returns structured data via a tool call."""

    _all_messages: list[_messages.ModelMessage]
    _new_message_index: int

    _stream_response: AgentStream[AgentDepsT, OutputDataT] | None = None
    _on_complete: Callable[[], Awaitable[None]] | None = None

    _run_result: AgentRunResult[OutputDataT] | None = None

    is_complete: bool = field(default=False, init=False)
    """Whether the stream has all been received.

    This is set to `True` when one of
    [`stream_output`][pydantic_ai.result.StreamedRunResult.stream_output],
    [`stream_text`][pydantic_ai.result.StreamedRunResult.stream_text],
    [`stream_responses`][pydantic_ai.result.StreamedRunResult.stream_responses] or
    [`get_output`][pydantic_ai.result.StreamedRunResult.get_output] completes.
    """

    @overload
    def __init__(
        self,
        all_messages: list[_messages.ModelMessage],
        new_message_index: int,
        stream_response: AgentStream[AgentDepsT, OutputDataT] | None,
        on_complete: Callable[[], Awaitable[None]] | None,
    ) -> None: ...

    @overload
    def __init__(
        self,
        all_messages: list[_messages.ModelMessage],
        new_message_index: int,
        *,
        run_result: AgentRunResult[OutputDataT],
    ) -> None: ...

    def __init__(
        self,
        all_messages: list[_messages.ModelMessage],
        new_message_index: int,
        stream_response: AgentStream[AgentDepsT, OutputDataT] | None = None,
        on_complete: Callable[[], Awaitable[None]] | None = None,
        run_result: AgentRunResult[OutputDataT] | None = None,
    ) -> None:
        self._all_messages = all_messages
        self._new_message_index = new_message_index

        self._stream_response = stream_response
        self._on_complete = on_complete
        self._run_result = run_result

    def all_messages(self, *, output_tool_return_content: str | None = None) -> list[_messages.ModelMessage]:
        """Return the history of _messages.

        Args:
            output_tool_return_content: The return content of the tool call to set in the last message.
                This provides a convenient way to modify the content of the output tool call if you want to continue
                the conversation and want to set the response to the output tool call. If `None`, the last message will
                not be modified.

        Returns:
            List of messages.
        """
        # this is a method to be consistent with the other methods
        if output_tool_return_content is not None:
            raise NotImplementedError('Setting output tool return content is not supported for this result type.')
        return self._all_messages

    def all_messages_json(self, *, output_tool_return_content: str | None = None) -> bytes:  # pragma: no cover
        """Return all messages from [`all_messages`][pydantic_ai.result.StreamedRunResult.all_messages] as JSON bytes.

        Args:
            output_tool_return_content: The return content of the tool call to set in the last message.
                This provides a convenient way to modify the content of the output tool call if you want to continue
                the conversation and want to set the response to the output tool call. If `None`, the last message will
                not be modified.

        Returns:
            JSON bytes representing the messages.
        """
        return _messages.ModelMessagesTypeAdapter.dump_json(
            self.all_messages(output_tool_return_content=output_tool_return_content)
        )

    def new_messages(self, *, output_tool_return_content: str | None = None) -> list[_messages.ModelMessage]:
        """Return new messages associated with this run.

        Messages from older runs are excluded.

        Args:
            output_tool_return_content: The return content of the tool call to set in the last message.
                This provides a convenient way to modify the content of the output tool call if you want to continue
                the conversation and want to set the response to the output tool call. If `None`, the last message will
                not be modified.

        Returns:
            List of new messages.
        """
        return self.all_messages(output_tool_return_content=output_tool_return_content)[self._new_message_index :]

    def new_messages_json(self, *, output_tool_return_content: str | None = None) -> bytes:  # pragma: no cover
        """Return new messages from [`new_messages`][pydantic_ai.result.StreamedRunResult.new_messages] as JSON bytes.

        Args:
            output_tool_return_content: The return content of the tool call to set in the last message.
                This provides a convenient way to modify the content of the output tool call if you want to continue
                the conversation and want to set the response to the output tool call. If `None`, the last message will
                not be modified.

        Returns:
            JSON bytes representing the new messages.
        """
        return _messages.ModelMessagesTypeAdapter.dump_json(
            self.new_messages(output_tool_return_content=output_tool_return_content)
        )

    @deprecated('`StreamedRunResult.stream` is deprecated, use `stream_output` instead.')
    async def stream(self, *, debounce_by: float | None = 0.1) -> AsyncIterator[OutputDataT]:
        async for output in self.stream_output(debounce_by=debounce_by):
            yield output

    async def stream_output(self, *, debounce_by: float | None = 0.1) -> AsyncIterator[OutputDataT]:
        """Stream the output as an async iterable.

        The pydantic validator for structured data will be called in
        [partial mode](https://docs.pydantic.dev/dev/concepts/experimental/#partial-validation)
        on each iteration.

        Args:
            debounce_by: by how much (if at all) to debounce/group the output chunks by. `None` means no debouncing.
                Debouncing is particularly important for long structured outputs to reduce the overhead of
                performing validation as each token is received.

        Returns:
            An async iterable of the response data.
        """
        if self._run_result is not None:
            yield self._run_result.output
            await self._marked_completed()
        elif self._stream_response is not None:
            async for output in self._stream_response.stream_output(debounce_by=debounce_by):
                yield output
            await self._marked_completed(self.response)
        else:
            raise ValueError('No stream response or run result provided')  # pragma: no cover

    async def stream_text(self, *, delta: bool = False, debounce_by: float | None = 0.1) -> AsyncIterator[str]:
        """Stream the text result as an async iterable.

        !!! note
            Result validators will NOT be called on the text result if `delta=True`.

        Args:
            delta: if `True`, yield each chunk of text as it is received, if `False` (default), yield the full text
                up to the current point.
            debounce_by: by how much (if at all) to debounce/group the response chunks by. `None` means no debouncing.
                Debouncing is particularly important for long structured responses to reduce the overhead of
                performing validation as each token is received.
        """
        if self._run_result is not None:  # pragma: no cover
            # We can't really get here, as `_run_result` is only set in `run_stream` when `CallToolsNode` produces `DeferredToolRequests` output
            # as a result of a tool function raising `CallDeferred` or `ApprovalRequired`.
            # That'll change if we ever support something like `raise EndRun(output: OutputT)` where `OutputT` could be `str`.
            if not isinstance(self._run_result.output, str):
                raise exceptions.UserError('stream_text() can only be used with text responses')
            yield self._run_result.output
            await self._marked_completed()
        elif self._stream_response is not None:
            async for text in self._stream_response.stream_text(delta=delta, debounce_by=debounce_by):
                yield text
            await self._marked_completed(self.response)
        else:
            raise ValueError('No stream response or run result provided')  # pragma: no cover

    @deprecated('`StreamedRunResult.stream_structured` is deprecated, use `stream_responses` instead.')
    async def stream_structured(
        self, *, debounce_by: float | None = 0.1
    ) -> AsyncIterator[tuple[_messages.ModelResponse, bool]]:
        async for msg, last in self.stream_responses(debounce_by=debounce_by):
            yield msg, last

    async def stream_responses(
        self, *, debounce_by: float | None = 0.1
    ) -> AsyncIterator[tuple[_messages.ModelResponse, bool]]:
        """Stream the response as an async iterable of Structured LLM Messages.

        Args:
            debounce_by: by how much (if at all) to debounce/group the response chunks by. `None` means no debouncing.
                Debouncing is particularly important for long structured responses to reduce the overhead of
                performing validation as each token is received.

        Returns:
            An async iterable of the structured response message and whether that is the last message.
        """
        if self._run_result is not None:
            yield self.response, True
            await self._marked_completed()
        elif self._stream_response is not None:
            # if the message currently has any parts with content, yield before streaming
            async for msg in self._stream_response.stream_responses(debounce_by=debounce_by):
                yield msg, False

            msg = self.response
            yield msg, True

            await self._marked_completed(msg)
        else:
            raise ValueError('No stream response or run result provided')  # pragma: no cover

    async def get_output(self) -> OutputDataT:
        """Stream the whole response, validate and return it."""
        if self._run_result is not None:
            output = self._run_result.output
            await self._marked_completed()
            return output
        elif self._stream_response is not None:
            output = await self._stream_response.get_output()
            await self._marked_completed(self.response)
            return output
        else:
            raise ValueError('No stream response or run result provided')  # pragma: no cover

    @property
    def response(self) -> _messages.ModelResponse:
        """Return the current state of the response."""
        if self._run_result is not None:
            return self._run_result.response
        elif self._stream_response is not None:
            return self._stream_response.get()
        else:
            raise ValueError('No stream response or run result provided')  # pragma: no cover

    @property
    def metadata(self) -> dict[str, Any] | None:
        """Metadata associated with this agent run, if configured."""
        if self._run_result is not None:
            return self._run_result.metadata
        elif self._stream_response is not None:
            return self._stream_response.metadata
        else:
            return None

    # TODO (v2): Make this a property
    def usage(self) -> RunUsage:
        """Return the usage of the whole run.

        !!! note
            This won't return the full usage until the stream is finished.
        """
        if self._run_result is not None:
            return self._run_result.usage()
        elif self._stream_response is not None:
            return self._stream_response.usage()
        else:
            raise ValueError('No stream response or run result provided')  # pragma: no cover

    # TODO (v2): Make this a property
    def timestamp(self) -> datetime:
        """Get the timestamp of the response."""
        if self._run_result is not None:
            return self._run_result.timestamp()
        elif self._stream_response is not None:
            return self._stream_response.timestamp()
        else:
            raise ValueError('No stream response or run result provided')  # pragma: no cover

    @property
    def run_id(self) -> str:
        """The unique identifier for the agent run."""
        if self._run_result is not None:
            return self._run_result.run_id
        elif self._stream_response is not None:
            return self._stream_response.run_id
        else:
            raise ValueError('No stream response or run result provided')  # pragma: no cover

    @deprecated('`validate_structured_output` is deprecated, use `validate_response_output` instead.')
    async def validate_structured_output(
        self, message: _messages.ModelResponse, *, allow_partial: bool = False
    ) -> OutputDataT:
        return await self.validate_response_output(message, allow_partial=allow_partial)

    async def validate_response_output(
        self, message: _messages.ModelResponse, *, allow_partial: bool = False
    ) -> OutputDataT:
        """Validate a structured result message."""
        if self._run_result is not None:
            return self._run_result.output
        elif self._stream_response is not None:
            return await self._stream_response.validate_response_output(message, allow_partial=allow_partial)
        else:
            raise ValueError('No stream response or run result provided')  # pragma: no cover

    async def _marked_completed(self, message: _messages.ModelResponse | None = None) -> None:
        if self.is_complete:
            return
        self.is_complete = True
        if message is not None:
            if self._stream_response:  # pragma: no branch
                message.run_id = self._stream_response.run_id
            self._all_messages.append(message)
        if self._on_complete is not None:
            await self._on_complete()
```

#### is_complete

```python
is_complete: bool = field(default=False, init=False)
```

Whether the stream has all been received.

This is set to `True` when one of stream_output, stream_text, stream_responses or get_output completes.

#### all_messages

```python
all_messages(
    *, output_tool_return_content: str | None = None
) -> list[ModelMessage]
```

Return the history of \_messages.

Parameters:

| Name                         | Type  | Description | Default                                                                                                                                                                                                                                                                                     |
| ---------------------------- | ----- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `output_tool_return_content` | \`str | None\`      | The return content of the tool call to set in the last message. This provides a convenient way to modify the content of the output tool call if you want to continue the conversation and want to set the response to the output tool call. If None, the last message will not be modified. |

Returns:

| Type                 | Description       |
| -------------------- | ----------------- |
| `list[ModelMessage]` | List of messages. |

Source code in `pydantic_ai_slim/pydantic_ai/result.py`

```python
def all_messages(self, *, output_tool_return_content: str | None = None) -> list[_messages.ModelMessage]:
    """Return the history of _messages.

    Args:
        output_tool_return_content: The return content of the tool call to set in the last message.
            This provides a convenient way to modify the content of the output tool call if you want to continue
            the conversation and want to set the response to the output tool call. If `None`, the last message will
            not be modified.

    Returns:
        List of messages.
    """
    # this is a method to be consistent with the other methods
    if output_tool_return_content is not None:
        raise NotImplementedError('Setting output tool return content is not supported for this result type.')
    return self._all_messages
```

#### all_messages_json

```python
all_messages_json(
    *, output_tool_return_content: str | None = None
) -> bytes
```

Return all messages from all_messages as JSON bytes.

Parameters:

| Name                         | Type  | Description | Default                                                                                                                                                                                                                                                                                     |
| ---------------------------- | ----- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `output_tool_return_content` | \`str | None\`      | The return content of the tool call to set in the last message. This provides a convenient way to modify the content of the output tool call if you want to continue the conversation and want to set the response to the output tool call. If None, the last message will not be modified. |

Returns:

| Type    | Description                           |
| ------- | ------------------------------------- |
| `bytes` | JSON bytes representing the messages. |

Source code in `pydantic_ai_slim/pydantic_ai/result.py`

```python
def all_messages_json(self, *, output_tool_return_content: str | None = None) -> bytes:  # pragma: no cover
    """Return all messages from [`all_messages`][pydantic_ai.result.StreamedRunResult.all_messages] as JSON bytes.

    Args:
        output_tool_return_content: The return content of the tool call to set in the last message.
            This provides a convenient way to modify the content of the output tool call if you want to continue
            the conversation and want to set the response to the output tool call. If `None`, the last message will
            not be modified.

    Returns:
        JSON bytes representing the messages.
    """
    return _messages.ModelMessagesTypeAdapter.dump_json(
        self.all_messages(output_tool_return_content=output_tool_return_content)
    )
```

#### new_messages

```python
new_messages(
    *, output_tool_return_content: str | None = None
) -> list[ModelMessage]
```

Return new messages associated with this run.

Messages from older runs are excluded.

Parameters:

| Name                         | Type  | Description | Default                                                                                                                                                                                                                                                                                     |
| ---------------------------- | ----- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `output_tool_return_content` | \`str | None\`      | The return content of the tool call to set in the last message. This provides a convenient way to modify the content of the output tool call if you want to continue the conversation and want to set the response to the output tool call. If None, the last message will not be modified. |

Returns:

| Type                 | Description           |
| -------------------- | --------------------- |
| `list[ModelMessage]` | List of new messages. |

Source code in `pydantic_ai_slim/pydantic_ai/result.py`

```python
def new_messages(self, *, output_tool_return_content: str | None = None) -> list[_messages.ModelMessage]:
    """Return new messages associated with this run.

    Messages from older runs are excluded.

    Args:
        output_tool_return_content: The return content of the tool call to set in the last message.
            This provides a convenient way to modify the content of the output tool call if you want to continue
            the conversation and want to set the response to the output tool call. If `None`, the last message will
            not be modified.

    Returns:
        List of new messages.
    """
    return self.all_messages(output_tool_return_content=output_tool_return_content)[self._new_message_index :]
```

#### new_messages_json

```python
new_messages_json(
    *, output_tool_return_content: str | None = None
) -> bytes
```

Return new messages from new_messages as JSON bytes.

Parameters:

| Name                         | Type  | Description | Default                                                                                                                                                                                                                                                                                     |
| ---------------------------- | ----- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `output_tool_return_content` | \`str | None\`      | The return content of the tool call to set in the last message. This provides a convenient way to modify the content of the output tool call if you want to continue the conversation and want to set the response to the output tool call. If None, the last message will not be modified. |

Returns:

| Type    | Description                               |
| ------- | ----------------------------------------- |
| `bytes` | JSON bytes representing the new messages. |

Source code in `pydantic_ai_slim/pydantic_ai/result.py`

```python
def new_messages_json(self, *, output_tool_return_content: str | None = None) -> bytes:  # pragma: no cover
    """Return new messages from [`new_messages`][pydantic_ai.result.StreamedRunResult.new_messages] as JSON bytes.

    Args:
        output_tool_return_content: The return content of the tool call to set in the last message.
            This provides a convenient way to modify the content of the output tool call if you want to continue
            the conversation and want to set the response to the output tool call. If `None`, the last message will
            not be modified.

    Returns:
        JSON bytes representing the new messages.
    """
    return _messages.ModelMessagesTypeAdapter.dump_json(
        self.new_messages(output_tool_return_content=output_tool_return_content)
    )
```

#### stream

```python
stream(
    *, debounce_by: float | None = 0.1
) -> AsyncIterator[OutputDataT]
```

Deprecated

`StreamedRunResult.stream` is deprecated, use `stream_output` instead.

Source code in `pydantic_ai_slim/pydantic_ai/result.py`

```python
@deprecated('`StreamedRunResult.stream` is deprecated, use `stream_output` instead.')
async def stream(self, *, debounce_by: float | None = 0.1) -> AsyncIterator[OutputDataT]:
    async for output in self.stream_output(debounce_by=debounce_by):
        yield output
```

#### stream_output

```python
stream_output(
    *, debounce_by: float | None = 0.1
) -> AsyncIterator[OutputDataT]
```

Stream the output as an async iterable.

The pydantic validator for structured data will be called in [partial mode](https://docs.pydantic.dev/dev/concepts/experimental/#partial-validation) on each iteration.

Parameters:

| Name          | Type    | Description | Default                                                                                                                                                                                                                               |
| ------------- | ------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `debounce_by` | \`float | None\`      | by how much (if at all) to debounce/group the output chunks by. None means no debouncing. Debouncing is particularly important for long structured outputs to reduce the overhead of performing validation as each token is received. |

Returns:

| Type                         | Description                             |
| ---------------------------- | --------------------------------------- |
| `AsyncIterator[OutputDataT]` | An async iterable of the response data. |

Source code in `pydantic_ai_slim/pydantic_ai/result.py`

```python
async def stream_output(self, *, debounce_by: float | None = 0.1) -> AsyncIterator[OutputDataT]:
    """Stream the output as an async iterable.

    The pydantic validator for structured data will be called in
    [partial mode](https://docs.pydantic.dev/dev/concepts/experimental/#partial-validation)
    on each iteration.

    Args:
        debounce_by: by how much (if at all) to debounce/group the output chunks by. `None` means no debouncing.
            Debouncing is particularly important for long structured outputs to reduce the overhead of
            performing validation as each token is received.

    Returns:
        An async iterable of the response data.
    """
    if self._run_result is not None:
        yield self._run_result.output
        await self._marked_completed()
    elif self._stream_response is not None:
        async for output in self._stream_response.stream_output(debounce_by=debounce_by):
            yield output
        await self._marked_completed(self.response)
    else:
        raise ValueError('No stream response or run result provided')  # pragma: no cover
```

#### stream_text

```python
stream_text(
    *, delta: bool = False, debounce_by: float | None = 0.1
) -> AsyncIterator[str]
```

Stream the text result as an async iterable.

Note

Result validators will NOT be called on the text result if `delta=True`.

Parameters:

| Name          | Type    | Description                                                                                                           | Default                                                                                                                                                                                                                                   |
| ------------- | ------- | --------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `delta`       | `bool`  | if True, yield each chunk of text as it is received, if False (default), yield the full text up to the current point. | `False`                                                                                                                                                                                                                                   |
| `debounce_by` | \`float | None\`                                                                                                                | by how much (if at all) to debounce/group the response chunks by. None means no debouncing. Debouncing is particularly important for long structured responses to reduce the overhead of performing validation as each token is received. |

Source code in `pydantic_ai_slim/pydantic_ai/result.py`

```python
async def stream_text(self, *, delta: bool = False, debounce_by: float | None = 0.1) -> AsyncIterator[str]:
    """Stream the text result as an async iterable.

    !!! note
        Result validators will NOT be called on the text result if `delta=True`.

    Args:
        delta: if `True`, yield each chunk of text as it is received, if `False` (default), yield the full text
            up to the current point.
        debounce_by: by how much (if at all) to debounce/group the response chunks by. `None` means no debouncing.
            Debouncing is particularly important for long structured responses to reduce the overhead of
            performing validation as each token is received.
    """
    if self._run_result is not None:  # pragma: no cover
        # We can't really get here, as `_run_result` is only set in `run_stream` when `CallToolsNode` produces `DeferredToolRequests` output
        # as a result of a tool function raising `CallDeferred` or `ApprovalRequired`.
        # That'll change if we ever support something like `raise EndRun(output: OutputT)` where `OutputT` could be `str`.
        if not isinstance(self._run_result.output, str):
            raise exceptions.UserError('stream_text() can only be used with text responses')
        yield self._run_result.output
        await self._marked_completed()
    elif self._stream_response is not None:
        async for text in self._stream_response.stream_text(delta=delta, debounce_by=debounce_by):
            yield text
        await self._marked_completed(self.response)
    else:
        raise ValueError('No stream response or run result provided')  # pragma: no cover
```

#### stream_structured

```python
stream_structured(
    *, debounce_by: float | None = 0.1
) -> AsyncIterator[tuple[ModelResponse, bool]]
```

Deprecated

`StreamedRunResult.stream_structured` is deprecated, use `stream_responses` instead.

Source code in `pydantic_ai_slim/pydantic_ai/result.py`

```python
@deprecated('`StreamedRunResult.stream_structured` is deprecated, use `stream_responses` instead.')
async def stream_structured(
    self, *, debounce_by: float | None = 0.1
) -> AsyncIterator[tuple[_messages.ModelResponse, bool]]:
    async for msg, last in self.stream_responses(debounce_by=debounce_by):
        yield msg, last
```

#### stream_responses

```python
stream_responses(
    *, debounce_by: float | None = 0.1
) -> AsyncIterator[tuple[ModelResponse, bool]]
```

Stream the response as an async iterable of Structured LLM Messages.

Parameters:

| Name          | Type    | Description | Default                                                                                                                                                                                                                                   |
| ------------- | ------- | ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `debounce_by` | \`float | None\`      | by how much (if at all) to debounce/group the response chunks by. None means no debouncing. Debouncing is particularly important for long structured responses to reduce the overhead of performing validation as each token is received. |

Returns:

| Type                                        | Description                                                                                |
| ------------------------------------------- | ------------------------------------------------------------------------------------------ |
| `AsyncIterator[tuple[ModelResponse, bool]]` | An async iterable of the structured response message and whether that is the last message. |

Source code in `pydantic_ai_slim/pydantic_ai/result.py`

```python
async def stream_responses(
    self, *, debounce_by: float | None = 0.1
) -> AsyncIterator[tuple[_messages.ModelResponse, bool]]:
    """Stream the response as an async iterable of Structured LLM Messages.

    Args:
        debounce_by: by how much (if at all) to debounce/group the response chunks by. `None` means no debouncing.
            Debouncing is particularly important for long structured responses to reduce the overhead of
            performing validation as each token is received.

    Returns:
        An async iterable of the structured response message and whether that is the last message.
    """
    if self._run_result is not None:
        yield self.response, True
        await self._marked_completed()
    elif self._stream_response is not None:
        # if the message currently has any parts with content, yield before streaming
        async for msg in self._stream_response.stream_responses(debounce_by=debounce_by):
            yield msg, False

        msg = self.response
        yield msg, True

        await self._marked_completed(msg)
    else:
        raise ValueError('No stream response or run result provided')  # pragma: no cover
```

#### get_output

```python
get_output() -> OutputDataT
```

Stream the whole response, validate and return it.

Source code in `pydantic_ai_slim/pydantic_ai/result.py`

```python
async def get_output(self) -> OutputDataT:
    """Stream the whole response, validate and return it."""
    if self._run_result is not None:
        output = self._run_result.output
        await self._marked_completed()
        return output
    elif self._stream_response is not None:
        output = await self._stream_response.get_output()
        await self._marked_completed(self.response)
        return output
    else:
        raise ValueError('No stream response or run result provided')  # pragma: no cover
```

#### response

```python
response: ModelResponse
```

Return the current state of the response.

#### metadata

```python
metadata: dict[str, Any] | None
```

Metadata associated with this agent run, if configured.

#### usage

```python
usage() -> RunUsage
```

Return the usage of the whole run.

Note

This won't return the full usage until the stream is finished.

Source code in `pydantic_ai_slim/pydantic_ai/result.py`

```python
def usage(self) -> RunUsage:
    """Return the usage of the whole run.

    !!! note
        This won't return the full usage until the stream is finished.
    """
    if self._run_result is not None:
        return self._run_result.usage()
    elif self._stream_response is not None:
        return self._stream_response.usage()
    else:
        raise ValueError('No stream response or run result provided')  # pragma: no cover
```

#### timestamp

```python
timestamp() -> datetime
```

Get the timestamp of the response.

Source code in `pydantic_ai_slim/pydantic_ai/result.py`

```python
def timestamp(self) -> datetime:
    """Get the timestamp of the response."""
    if self._run_result is not None:
        return self._run_result.timestamp()
    elif self._stream_response is not None:
        return self._stream_response.timestamp()
    else:
        raise ValueError('No stream response or run result provided')  # pragma: no cover
```

#### run_id

```python
run_id: str
```

The unique identifier for the agent run.

#### validate_structured_output

```python
validate_structured_output(
    message: ModelResponse, *, allow_partial: bool = False
) -> OutputDataT
```

Deprecated

`validate_structured_output` is deprecated, use `validate_response_output` instead.

Source code in `pydantic_ai_slim/pydantic_ai/result.py`

```python
@deprecated('`validate_structured_output` is deprecated, use `validate_response_output` instead.')
async def validate_structured_output(
    self, message: _messages.ModelResponse, *, allow_partial: bool = False
) -> OutputDataT:
    return await self.validate_response_output(message, allow_partial=allow_partial)
```

#### validate_response_output

```python
validate_response_output(
    message: ModelResponse, *, allow_partial: bool = False
) -> OutputDataT
```

Validate a structured result message.

Source code in `pydantic_ai_slim/pydantic_ai/result.py`

```python
async def validate_response_output(
    self, message: _messages.ModelResponse, *, allow_partial: bool = False
) -> OutputDataT:
    """Validate a structured result message."""
    if self._run_result is not None:
        return self._run_result.output
    elif self._stream_response is not None:
        return await self._stream_response.validate_response_output(message, allow_partial=allow_partial)
    else:
        raise ValueError('No stream response or run result provided')  # pragma: no cover
```

### StreamedRunResultSync

Bases: `Generic[AgentDepsT, OutputDataT]`

Synchronous wrapper for StreamedRunResult that only exposes sync methods.

Source code in `pydantic_ai_slim/pydantic_ai/result.py`

```python
@dataclass(init=False)
class StreamedRunResultSync(Generic[AgentDepsT, OutputDataT]):
    """Synchronous wrapper for [`StreamedRunResult`][pydantic_ai.result.StreamedRunResult] that only exposes sync methods."""

    _streamed_run_result: StreamedRunResult[AgentDepsT, OutputDataT]

    def __init__(self, streamed_run_result: StreamedRunResult[AgentDepsT, OutputDataT]) -> None:
        self._streamed_run_result = streamed_run_result

    def all_messages(self, *, output_tool_return_content: str | None = None) -> list[_messages.ModelMessage]:
        """Return the history of messages.

        Args:
            output_tool_return_content: The return content of the tool call to set in the last message.
                This provides a convenient way to modify the content of the output tool call if you want to continue
                the conversation and want to set the response to the output tool call. If `None`, the last message will
                not be modified.

        Returns:
            List of messages.
        """
        return self._streamed_run_result.all_messages(output_tool_return_content=output_tool_return_content)

    def all_messages_json(self, *, output_tool_return_content: str | None = None) -> bytes:  # pragma: no cover
        """Return all messages from [`all_messages`][pydantic_ai.result.StreamedRunResultSync.all_messages] as JSON bytes.

        Args:
            output_tool_return_content: The return content of the tool call to set in the last message.
                This provides a convenient way to modify the content of the output tool call if you want to continue
                the conversation and want to set the response to the output tool call. If `None`, the last message will
                not be modified.

        Returns:
            JSON bytes representing the messages.
        """
        return self._streamed_run_result.all_messages_json(output_tool_return_content=output_tool_return_content)

    def new_messages(self, *, output_tool_return_content: str | None = None) -> list[_messages.ModelMessage]:
        """Return new messages associated with this run.

        Messages from older runs are excluded.

        Args:
            output_tool_return_content: The return content of the tool call to set in the last message.
                This provides a convenient way to modify the content of the output tool call if you want to continue
                the conversation and want to set the response to the output tool call. If `None`, the last message will
                not be modified.

        Returns:
            List of new messages.
        """
        return self._streamed_run_result.new_messages(output_tool_return_content=output_tool_return_content)

    def new_messages_json(self, *, output_tool_return_content: str | None = None) -> bytes:  # pragma: no cover
        """Return new messages from [`new_messages`][pydantic_ai.result.StreamedRunResultSync.new_messages] as JSON bytes.

        Args:
            output_tool_return_content: The return content of the tool call to set in the last message.
                This provides a convenient way to modify the content of the output tool call if you want to continue
                the conversation and want to set the response to the output tool call. If `None`, the last message will
                not be modified.

        Returns:
            JSON bytes representing the new messages.
        """
        return self._streamed_run_result.new_messages_json(output_tool_return_content=output_tool_return_content)

    def stream_output(self, *, debounce_by: float | None = 0.1) -> Iterator[OutputDataT]:
        """Stream the output as an iterable.

        The pydantic validator for structured data will be called in
        [partial mode](https://docs.pydantic.dev/dev/concepts/experimental/#partial-validation)
        on each iteration.

        Args:
            debounce_by: by how much (if at all) to debounce/group the output chunks by. `None` means no debouncing.
                Debouncing is particularly important for long structured outputs to reduce the overhead of
                performing validation as each token is received.

        Returns:
            An iterable of the response data.
        """
        return _utils.sync_async_iterator(self._streamed_run_result.stream_output(debounce_by=debounce_by))

    def stream_text(self, *, delta: bool = False, debounce_by: float | None = 0.1) -> Iterator[str]:
        """Stream the text result as an iterable.

        !!! note
            Result validators will NOT be called on the text result if `delta=True`.

        Args:
            delta: if `True`, yield each chunk of text as it is received, if `False` (default), yield the full text
                up to the current point.
            debounce_by: by how much (if at all) to debounce/group the response chunks by. `None` means no debouncing.
                Debouncing is particularly important for long structured responses to reduce the overhead of
                performing validation as each token is received.
        """
        return _utils.sync_async_iterator(self._streamed_run_result.stream_text(delta=delta, debounce_by=debounce_by))

    def stream_responses(self, *, debounce_by: float | None = 0.1) -> Iterator[tuple[_messages.ModelResponse, bool]]:
        """Stream the response as an iterable of Structured LLM Messages.

        Args:
            debounce_by: by how much (if at all) to debounce/group the response chunks by. `None` means no debouncing.
                Debouncing is particularly important for long structured responses to reduce the overhead of
                performing validation as each token is received.

        Returns:
            An iterable of the structured response message and whether that is the last message.
        """
        return _utils.sync_async_iterator(self._streamed_run_result.stream_responses(debounce_by=debounce_by))

    def get_output(self) -> OutputDataT:
        """Stream the whole response, validate and return it."""
        return _utils.get_event_loop().run_until_complete(self._streamed_run_result.get_output())

    @property
    def response(self) -> _messages.ModelResponse:
        """Return the current state of the response."""
        return self._streamed_run_result.response

    def usage(self) -> RunUsage:
        """Return the usage of the whole run.

        !!! note
            This won't return the full usage until the stream is finished.
        """
        return self._streamed_run_result.usage()

    def timestamp(self) -> datetime:
        """Get the timestamp of the response."""
        return self._streamed_run_result.timestamp()

    @property
    def run_id(self) -> str:
        """The unique identifier for the agent run."""
        return self._streamed_run_result.run_id

    @property
    def metadata(self) -> dict[str, Any] | None:
        """Metadata associated with this agent run, if configured."""
        return self._streamed_run_result.metadata

    def validate_response_output(self, message: _messages.ModelResponse, *, allow_partial: bool = False) -> OutputDataT:
        """Validate a structured result message."""
        return _utils.get_event_loop().run_until_complete(
            self._streamed_run_result.validate_response_output(message, allow_partial=allow_partial)
        )

    @property
    def is_complete(self) -> bool:
        """Whether the stream has all been received.

        This is set to `True` when one of
        [`stream_output`][pydantic_ai.result.StreamedRunResultSync.stream_output],
        [`stream_text`][pydantic_ai.result.StreamedRunResultSync.stream_text],
        [`stream_responses`][pydantic_ai.result.StreamedRunResultSync.stream_responses] or
        [`get_output`][pydantic_ai.result.StreamedRunResultSync.get_output] completes.
        """
        return self._streamed_run_result.is_complete
```

#### all_messages

```python
all_messages(
    *, output_tool_return_content: str | None = None
) -> list[ModelMessage]
```

Return the history of messages.

Parameters:

| Name                         | Type  | Description | Default                                                                                                                                                                                                                                                                                     |
| ---------------------------- | ----- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `output_tool_return_content` | \`str | None\`      | The return content of the tool call to set in the last message. This provides a convenient way to modify the content of the output tool call if you want to continue the conversation and want to set the response to the output tool call. If None, the last message will not be modified. |

Returns:

| Type                 | Description       |
| -------------------- | ----------------- |
| `list[ModelMessage]` | List of messages. |

Source code in `pydantic_ai_slim/pydantic_ai/result.py`

```python
def all_messages(self, *, output_tool_return_content: str | None = None) -> list[_messages.ModelMessage]:
    """Return the history of messages.

    Args:
        output_tool_return_content: The return content of the tool call to set in the last message.
            This provides a convenient way to modify the content of the output tool call if you want to continue
            the conversation and want to set the response to the output tool call. If `None`, the last message will
            not be modified.

    Returns:
        List of messages.
    """
    return self._streamed_run_result.all_messages(output_tool_return_content=output_tool_return_content)
```

#### all_messages_json

```python
all_messages_json(
    *, output_tool_return_content: str | None = None
) -> bytes
```

Return all messages from all_messages as JSON bytes.

Parameters:

| Name                         | Type  | Description | Default                                                                                                                                                                                                                                                                                     |
| ---------------------------- | ----- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `output_tool_return_content` | \`str | None\`      | The return content of the tool call to set in the last message. This provides a convenient way to modify the content of the output tool call if you want to continue the conversation and want to set the response to the output tool call. If None, the last message will not be modified. |

Returns:

| Type    | Description                           |
| ------- | ------------------------------------- |
| `bytes` | JSON bytes representing the messages. |

Source code in `pydantic_ai_slim/pydantic_ai/result.py`

```python
def all_messages_json(self, *, output_tool_return_content: str | None = None) -> bytes:  # pragma: no cover
    """Return all messages from [`all_messages`][pydantic_ai.result.StreamedRunResultSync.all_messages] as JSON bytes.

    Args:
        output_tool_return_content: The return content of the tool call to set in the last message.
            This provides a convenient way to modify the content of the output tool call if you want to continue
            the conversation and want to set the response to the output tool call. If `None`, the last message will
            not be modified.

    Returns:
        JSON bytes representing the messages.
    """
    return self._streamed_run_result.all_messages_json(output_tool_return_content=output_tool_return_content)
```

#### new_messages

```python
new_messages(
    *, output_tool_return_content: str | None = None
) -> list[ModelMessage]
```

Return new messages associated with this run.

Messages from older runs are excluded.

Parameters:

| Name                         | Type  | Description | Default                                                                                                                                                                                                                                                                                     |
| ---------------------------- | ----- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `output_tool_return_content` | \`str | None\`      | The return content of the tool call to set in the last message. This provides a convenient way to modify the content of the output tool call if you want to continue the conversation and want to set the response to the output tool call. If None, the last message will not be modified. |

Returns:

| Type                 | Description           |
| -------------------- | --------------------- |
| `list[ModelMessage]` | List of new messages. |

Source code in `pydantic_ai_slim/pydantic_ai/result.py`

```python
def new_messages(self, *, output_tool_return_content: str | None = None) -> list[_messages.ModelMessage]:
    """Return new messages associated with this run.

    Messages from older runs are excluded.

    Args:
        output_tool_return_content: The return content of the tool call to set in the last message.
            This provides a convenient way to modify the content of the output tool call if you want to continue
            the conversation and want to set the response to the output tool call. If `None`, the last message will
            not be modified.

    Returns:
        List of new messages.
    """
    return self._streamed_run_result.new_messages(output_tool_return_content=output_tool_return_content)
```

#### new_messages_json

```python
new_messages_json(
    *, output_tool_return_content: str | None = None
) -> bytes
```

Return new messages from new_messages as JSON bytes.

Parameters:

| Name                         | Type  | Description | Default                                                                                                                                                                                                                                                                                     |
| ---------------------------- | ----- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `output_tool_return_content` | \`str | None\`      | The return content of the tool call to set in the last message. This provides a convenient way to modify the content of the output tool call if you want to continue the conversation and want to set the response to the output tool call. If None, the last message will not be modified. |

Returns:

| Type    | Description                               |
| ------- | ----------------------------------------- |
| `bytes` | JSON bytes representing the new messages. |

Source code in `pydantic_ai_slim/pydantic_ai/result.py`

```python
def new_messages_json(self, *, output_tool_return_content: str | None = None) -> bytes:  # pragma: no cover
    """Return new messages from [`new_messages`][pydantic_ai.result.StreamedRunResultSync.new_messages] as JSON bytes.

    Args:
        output_tool_return_content: The return content of the tool call to set in the last message.
            This provides a convenient way to modify the content of the output tool call if you want to continue
            the conversation and want to set the response to the output tool call. If `None`, the last message will
            not be modified.

    Returns:
        JSON bytes representing the new messages.
    """
    return self._streamed_run_result.new_messages_json(output_tool_return_content=output_tool_return_content)
```

#### stream_output

```python
stream_output(
    *, debounce_by: float | None = 0.1
) -> Iterator[OutputDataT]
```

Stream the output as an iterable.

The pydantic validator for structured data will be called in [partial mode](https://docs.pydantic.dev/dev/concepts/experimental/#partial-validation) on each iteration.

Parameters:

| Name          | Type    | Description | Default                                                                                                                                                                                                                               |
| ------------- | ------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `debounce_by` | \`float | None\`      | by how much (if at all) to debounce/group the output chunks by. None means no debouncing. Debouncing is particularly important for long structured outputs to reduce the overhead of performing validation as each token is received. |

Returns:

| Type                    | Description                       |
| ----------------------- | --------------------------------- |
| `Iterator[OutputDataT]` | An iterable of the response data. |

Source code in `pydantic_ai_slim/pydantic_ai/result.py`

```python
def stream_output(self, *, debounce_by: float | None = 0.1) -> Iterator[OutputDataT]:
    """Stream the output as an iterable.

    The pydantic validator for structured data will be called in
    [partial mode](https://docs.pydantic.dev/dev/concepts/experimental/#partial-validation)
    on each iteration.

    Args:
        debounce_by: by how much (if at all) to debounce/group the output chunks by. `None` means no debouncing.
            Debouncing is particularly important for long structured outputs to reduce the overhead of
            performing validation as each token is received.

    Returns:
        An iterable of the response data.
    """
    return _utils.sync_async_iterator(self._streamed_run_result.stream_output(debounce_by=debounce_by))
```

#### stream_text

```python
stream_text(
    *, delta: bool = False, debounce_by: float | None = 0.1
) -> Iterator[str]
```

Stream the text result as an iterable.

Note

Result validators will NOT be called on the text result if `delta=True`.

Parameters:

| Name          | Type    | Description                                                                                                           | Default                                                                                                                                                                                                                                   |
| ------------- | ------- | --------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `delta`       | `bool`  | if True, yield each chunk of text as it is received, if False (default), yield the full text up to the current point. | `False`                                                                                                                                                                                                                                   |
| `debounce_by` | \`float | None\`                                                                                                                | by how much (if at all) to debounce/group the response chunks by. None means no debouncing. Debouncing is particularly important for long structured responses to reduce the overhead of performing validation as each token is received. |

Source code in `pydantic_ai_slim/pydantic_ai/result.py`

```python
def stream_text(self, *, delta: bool = False, debounce_by: float | None = 0.1) -> Iterator[str]:
    """Stream the text result as an iterable.

    !!! note
        Result validators will NOT be called on the text result if `delta=True`.

    Args:
        delta: if `True`, yield each chunk of text as it is received, if `False` (default), yield the full text
            up to the current point.
        debounce_by: by how much (if at all) to debounce/group the response chunks by. `None` means no debouncing.
            Debouncing is particularly important for long structured responses to reduce the overhead of
            performing validation as each token is received.
    """
    return _utils.sync_async_iterator(self._streamed_run_result.stream_text(delta=delta, debounce_by=debounce_by))
```

#### stream_responses

```python
stream_responses(
    *, debounce_by: float | None = 0.1
) -> Iterator[tuple[ModelResponse, bool]]
```

Stream the response as an iterable of Structured LLM Messages.

Parameters:

| Name          | Type    | Description | Default                                                                                                                                                                                                                                   |
| ------------- | ------- | ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `debounce_by` | \`float | None\`      | by how much (if at all) to debounce/group the response chunks by. None means no debouncing. Debouncing is particularly important for long structured responses to reduce the overhead of performing validation as each token is received. |

Returns:

| Type                                   | Description                                                                          |
| -------------------------------------- | ------------------------------------------------------------------------------------ |
| `Iterator[tuple[ModelResponse, bool]]` | An iterable of the structured response message and whether that is the last message. |

Source code in `pydantic_ai_slim/pydantic_ai/result.py`

```python
def stream_responses(self, *, debounce_by: float | None = 0.1) -> Iterator[tuple[_messages.ModelResponse, bool]]:
    """Stream the response as an iterable of Structured LLM Messages.

    Args:
        debounce_by: by how much (if at all) to debounce/group the response chunks by. `None` means no debouncing.
            Debouncing is particularly important for long structured responses to reduce the overhead of
            performing validation as each token is received.

    Returns:
        An iterable of the structured response message and whether that is the last message.
    """
    return _utils.sync_async_iterator(self._streamed_run_result.stream_responses(debounce_by=debounce_by))
```

#### get_output

```python
get_output() -> OutputDataT
```

Stream the whole response, validate and return it.

Source code in `pydantic_ai_slim/pydantic_ai/result.py`

```python
def get_output(self) -> OutputDataT:
    """Stream the whole response, validate and return it."""
    return _utils.get_event_loop().run_until_complete(self._streamed_run_result.get_output())
```

#### response

```python
response: ModelResponse
```

Return the current state of the response.

#### usage

```python
usage() -> RunUsage
```

Return the usage of the whole run.

Note

This won't return the full usage until the stream is finished.

Source code in `pydantic_ai_slim/pydantic_ai/result.py`

```python
def usage(self) -> RunUsage:
    """Return the usage of the whole run.

    !!! note
        This won't return the full usage until the stream is finished.
    """
    return self._streamed_run_result.usage()
```

#### timestamp

```python
timestamp() -> datetime
```

Get the timestamp of the response.

Source code in `pydantic_ai_slim/pydantic_ai/result.py`

```python
def timestamp(self) -> datetime:
    """Get the timestamp of the response."""
    return self._streamed_run_result.timestamp()
```

#### run_id

```python
run_id: str
```

The unique identifier for the agent run.

#### metadata

```python
metadata: dict[str, Any] | None
```

Metadata associated with this agent run, if configured.

#### validate_response_output

```python
validate_response_output(
    message: ModelResponse, *, allow_partial: bool = False
) -> OutputDataT
```

Validate a structured result message.

Source code in `pydantic_ai_slim/pydantic_ai/result.py`

```python
def validate_response_output(self, message: _messages.ModelResponse, *, allow_partial: bool = False) -> OutputDataT:
    """Validate a structured result message."""
    return _utils.get_event_loop().run_until_complete(
        self._streamed_run_result.validate_response_output(message, allow_partial=allow_partial)
    )
```

#### is_complete

```python
is_complete: bool
```

Whether the stream has all been received.

This is set to `True` when one of stream_output, stream_text, stream_responses or get_output completes.
