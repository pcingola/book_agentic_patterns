# `pydantic_ai.ui.vercel_ai`

Vercel AI protocol adapter for Pydantic AI agents.

This module provides classes for integrating Pydantic AI agents with the Vercel AI protocol, enabling streaming event-based communication for interactive AI applications.

Converted to Python from: https://github.com/vercel/ai/blob/ai%405.0.34/packages/ai/src/ui/ui-messages.ts

### VercelAIAdapter

Bases: `UIAdapter[RequestData, UIMessage, BaseChunk, AgentDepsT, OutputDataT]`

UI adapter for the Vercel AI protocol.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/_adapter.py`

```python
@dataclass
class VercelAIAdapter(UIAdapter[RequestData, UIMessage, BaseChunk, AgentDepsT, OutputDataT]):
    """UI adapter for the Vercel AI protocol."""

    _: KW_ONLY
    sdk_version: Literal[5, 6] = 5
    """Vercel AI SDK version to target. Default is 5 for backwards compatibility."""

    @classmethod
    def build_run_input(cls, body: bytes) -> RequestData:
        """Build a Vercel AI run input object from the request body."""
        return request_data_ta.validate_json(body)

    def build_event_stream(self) -> UIEventStream[RequestData, BaseChunk, AgentDepsT, OutputDataT]:
        """Build a Vercel AI event stream transformer."""
        return VercelAIEventStream(self.run_input, accept=self.accept, sdk_version=self.sdk_version)

    @cached_property
    def messages(self) -> list[ModelMessage]:
        """Pydantic AI messages from the Vercel AI run input."""
        return self.load_messages(self.run_input.messages)

    @classmethod
    def load_messages(cls, messages: Sequence[UIMessage]) -> list[ModelMessage]:  # noqa: C901
        """Transform Vercel AI messages into Pydantic AI messages."""
        builder = MessagesBuilder()

        for msg in messages:
            if msg.role == 'system':
                for part in msg.parts:
                    if isinstance(part, TextUIPart):
                        builder.add(SystemPromptPart(content=part.text))
                    else:  # pragma: no cover
                        raise ValueError(f'Unsupported system message part type: {type(part)}')
            elif msg.role == 'user':
                user_prompt_content: str | list[UserContent] = []
                for part in msg.parts:
                    if isinstance(part, TextUIPart):
                        user_prompt_content.append(part.text)
                    elif isinstance(part, FileUIPart):
                        try:
                            file = BinaryContent.from_data_uri(part.url)
                        except ValueError:
                            media_type_prefix = part.media_type.split('/', 1)[0]
                            match media_type_prefix:
                                case 'image':
                                    file = ImageUrl(url=part.url, media_type=part.media_type)
                                case 'video':
                                    file = VideoUrl(url=part.url, media_type=part.media_type)
                                case 'audio':
                                    file = AudioUrl(url=part.url, media_type=part.media_type)
                                case _:
                                    file = DocumentUrl(url=part.url, media_type=part.media_type)
                        user_prompt_content.append(file)
                    else:  # pragma: no cover
                        raise ValueError(f'Unsupported user message part type: {type(part)}')

                if user_prompt_content:  # pragma: no branch
                    if len(user_prompt_content) == 1 and isinstance(user_prompt_content[0], str):
                        user_prompt_content = user_prompt_content[0]
                    builder.add(UserPromptPart(content=user_prompt_content))

            elif msg.role == 'assistant':
                for part in msg.parts:
                    if isinstance(part, TextUIPart):
                        provider_meta = load_provider_metadata(part.provider_metadata)
                        builder.add(
                            TextPart(
                                content=part.text,
                                id=provider_meta.get('id'),
                                provider_name=provider_meta.get('provider_name'),
                                provider_details=provider_meta.get('provider_details'),
                            )
                        )
                    elif isinstance(part, ReasoningUIPart):
                        provider_meta = load_provider_metadata(part.provider_metadata)
                        builder.add(
                            ThinkingPart(
                                content=part.text,
                                id=provider_meta.get('id'),
                                signature=provider_meta.get('signature'),
                                provider_name=provider_meta.get('provider_name'),
                                provider_details=provider_meta.get('provider_details'),
                            )
                        )
                    elif isinstance(part, FileUIPart):
                        try:
                            file = BinaryContent.from_data_uri(part.url)
                        except ValueError as e:  # pragma: no cover
                            # We don't yet handle non-data-URI file URLs returned by assistants, as no Pydantic AI models do this.
                            raise ValueError(
                                'Vercel AI integration can currently only handle assistant file parts with data URIs.'
                            ) from e
                        provider_meta = load_provider_metadata(part.provider_metadata)
                        builder.add(
                            FilePart(
                                content=file,
                                id=provider_meta.get('id'),
                                provider_name=provider_meta.get('provider_name'),
                                provider_details=provider_meta.get('provider_details'),
                            )
                        )
                    elif isinstance(part, ToolUIPart | DynamicToolUIPart):
                        if isinstance(part, DynamicToolUIPart):
                            tool_name = part.tool_name
                            builtin_tool = False
                        else:
                            tool_name = part.type.removeprefix('tool-')
                            builtin_tool = part.provider_executed

                        tool_call_id = part.tool_call_id

                        args: str | dict[str, Any] | None = part.input

                        if isinstance(args, str):
                            try:
                                parsed = json.loads(args)
                                if isinstance(parsed, dict):
                                    args = cast(dict[str, Any], parsed)
                            except json.JSONDecodeError:
                                pass
                        elif isinstance(args, dict) or args is None:
                            pass
                        else:
                            assert_never(args)

                        provider_meta = load_provider_metadata(part.call_provider_metadata)
                        part_id = provider_meta.get('id')
                        provider_name = provider_meta.get('provider_name')
                        provider_details = provider_meta.get('provider_details')

                        if builtin_tool:
                            # For builtin tools, we need to create 2 parts (BuiltinToolCall & BuiltinToolReturn) for a single Vercel ToolOutput
                            # The call and return metadata are combined in the output part.
                            # So we extract and return them to the respective parts
                            call_meta = return_meta = {}
                            has_tool_output = isinstance(part, (ToolOutputAvailablePart, ToolOutputErrorPart))

                            if has_tool_output:
                                call_meta, return_meta = cls._load_builtin_tool_meta(provider_meta)

                            builder.add(
                                BuiltinToolCallPart(
                                    tool_name=tool_name,
                                    tool_call_id=tool_call_id,
                                    args=args,
                                    id=call_meta.get('id') or part_id,
                                    provider_name=call_meta.get('provider_name') or provider_name,
                                    provider_details=call_meta.get('provider_details') or provider_details,
                                )
                            )

                            if has_tool_output:
                                output: Any | None = None
                                if isinstance(part, ToolOutputAvailablePart):
                                    output = part.output
                                elif isinstance(part, ToolOutputErrorPart):  # pragma: no branch
                                    output = {'error_text': part.error_text, 'is_error': True}
                                builder.add(
                                    BuiltinToolReturnPart(
                                        tool_name=tool_name,
                                        tool_call_id=tool_call_id,
                                        content=output,
                                        provider_name=return_meta.get('provider_name') or provider_name,
                                        provider_details=return_meta.get('provider_details') or provider_details,
                                    )
                                )
                        else:
                            builder.add(
                                ToolCallPart(
                                    tool_name=tool_name,
                                    tool_call_id=tool_call_id,
                                    args=args,
                                    id=part_id,
                                    provider_name=provider_name,
                                    provider_details=provider_details,
                                )
                            )

                            if part.state == 'output-available':
                                builder.add(
                                    ToolReturnPart(tool_name=tool_name, tool_call_id=tool_call_id, content=part.output)
                                )
                            elif part.state == 'output-error':
                                builder.add(
                                    RetryPromptPart(
                                        tool_name=tool_name, tool_call_id=tool_call_id, content=part.error_text
                                    )
                                )
                    elif isinstance(part, DataUIPart):  # pragma: no cover
                        # Contains custom data that shouldn't be sent to the model
                        pass
                    elif isinstance(part, SourceUrlUIPart):  # pragma: no cover
                        # TODO: Once we support citations: https://github.com/pydantic/pydantic-ai/issues/3126
                        pass
                    elif isinstance(part, SourceDocumentUIPart):  # pragma: no cover
                        # TODO: Once we support citations: https://github.com/pydantic/pydantic-ai/issues/3126
                        pass
                    elif isinstance(part, StepStartUIPart):  # pragma: no cover
                        # Nothing to do here
                        pass
                    else:
                        assert_never(part)
            else:
                assert_never(msg.role)

        return builder.messages

    @staticmethod
    def _dump_builtin_tool_meta(
        call_provider_metadata: ProviderMetadata | None, return_provider_metadata: ProviderMetadata | None
    ) -> ProviderMetadata | None:
        """Use special keys (call_meta and return_meta) to dump combined provider metadata."""
        return dump_provider_metadata(call_meta=call_provider_metadata, return_meta=return_provider_metadata)

    @staticmethod
    def _load_builtin_tool_meta(
        provider_metadata: ProviderMetadata,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Use special keys (call_meta and return_meta) to load combined provider metadata."""
        return provider_metadata.get('call_meta') or {}, provider_metadata.get('return_meta') or {}

    @staticmethod
    def _dump_request_message(msg: ModelRequest) -> tuple[list[UIMessagePart], list[UIMessagePart]]:
        """Convert a ModelRequest into a UIMessage."""
        system_ui_parts: list[UIMessagePart] = []
        user_ui_parts: list[UIMessagePart] = []

        for part in msg.parts:
            if isinstance(part, SystemPromptPart):
                system_ui_parts.append(TextUIPart(text=part.content, state='done'))
            elif isinstance(part, UserPromptPart):
                user_ui_parts.extend(_convert_user_prompt_part(part))
            elif isinstance(part, ToolReturnPart):
                # Tool returns are merged into the tool call in the assistant message
                pass
            elif isinstance(part, RetryPromptPart):
                if part.tool_name:
                    # Tool-related retries are handled when processing ToolCallPart in ModelResponse
                    pass
                else:
                    # Non-tool retries (e.g., output validation errors) become user text
                    user_ui_parts.append(TextUIPart(text=part.model_response(), state='done'))
            else:
                assert_never(part)

        return system_ui_parts, user_ui_parts

    @classmethod
    def _dump_response_message(
        cls, msg: ModelResponse, tool_results: dict[str, ToolReturnPart | RetryPromptPart]
    ) -> list[UIMessagePart]:
        """Convert a ModelResponse into a UIMessage."""
        ui_parts: list[UIMessagePart] = []

        # For builtin tools, returns can be in the same ModelResponse as calls
        local_builtin_returns: dict[str, BuiltinToolReturnPart] = {
            part.tool_call_id: part for part in msg.parts if isinstance(part, BuiltinToolReturnPart)
        }

        for part in msg.parts:
            if isinstance(part, BuiltinToolReturnPart):
                continue
            elif isinstance(part, TextPart):
                # Combine consecutive text parts
                if ui_parts and isinstance(ui_parts[-1], TextUIPart):
                    ui_parts[-1].text += part.content
                else:
                    provider_metadata = dump_provider_metadata(
                        id=part.id, provider_name=part.provider_name, provider_details=part.provider_details
                    )
                    ui_parts.append(TextUIPart(text=part.content, state='done', provider_metadata=provider_metadata))
            elif isinstance(part, ThinkingPart):
                provider_metadata = dump_provider_metadata(
                    id=part.id,
                    signature=part.signature,
                    provider_name=part.provider_name,
                    provider_details=part.provider_details,
                )
                ui_parts.append(ReasoningUIPart(text=part.content, state='done', provider_metadata=provider_metadata))
            elif isinstance(part, FilePart):
                ui_parts.append(
                    FileUIPart(
                        url=part.content.data_uri,
                        media_type=part.content.media_type,
                        provider_metadata=dump_provider_metadata(
                            id=part.id, provider_name=part.provider_name, provider_details=part.provider_details
                        ),
                    )
                )
            elif isinstance(part, BuiltinToolCallPart):
                tool_name = f'tool-{part.tool_name}'
                if builtin_return := local_builtin_returns.get(part.tool_call_id):
                    # Builtin tool calls are represented by two parts in pydantic_ai:
                    #   1. BuiltinToolCallPart (the tool request) -> part
                    #   2. BuiltinToolReturnPart (the tool's output) -> builtin_return
                    # The Vercel AI SDK only has a single ToolOutputPart (ToolOutputAvailablePart or ToolOutputErrorPart).
                    # So, we need to combine the metadata so that when we later convert back from Vercel AI to pydantic_ai,
                    # we can properly reconstruct both the call and return parts with their respective metadata.
                    # Note: This extra metadata handling is only needed for built-in tools, since normal tool returns
                    # (ToolReturnPart) do not include provider metadata.

                    call_meta = dump_provider_metadata(
                        wrapper_key=None,
                        id=part.id,
                        provider_name=part.provider_name,
                        provider_details=part.provider_details,
                    )
                    return_meta = dump_provider_metadata(
                        wrapper_key=None,
                        provider_name=builtin_return.provider_name,
                        provider_details=builtin_return.provider_details,
                    )
                    combined_provider_meta = cls._dump_builtin_tool_meta(call_meta, return_meta)

                    response_object = builtin_return.model_response_object()
                    # These `is_error`/`error_text` fields are only present when the BuiltinToolReturnPart
                    # was parsed from an incoming VercelAI request. We can't detect errors for other sources
                    # until BuiltinToolReturnPart has standardized error fields (see https://github.com/pydantic/pydantic-ai/issues/3561).3
                    if response_object.get('is_error') is True and (
                        (error_text := response_object.get('error_text')) is not None
                    ):
                        ui_parts.append(
                            ToolOutputErrorPart(
                                type=tool_name,
                                tool_call_id=part.tool_call_id,
                                input=part.args_as_json_str(),
                                error_text=error_text,
                                state='output-error',
                                provider_executed=True,
                                call_provider_metadata=combined_provider_meta,
                            )
                        )
                    else:
                        content = builtin_return.model_response_str()
                        ui_parts.append(
                            ToolOutputAvailablePart(
                                type=tool_name,
                                tool_call_id=part.tool_call_id,
                                input=part.args_as_json_str(),
                                output=content,
                                state='output-available',
                                provider_executed=True,
                                call_provider_metadata=combined_provider_meta,
                            )
                        )
                else:
                    call_provider_metadata = dump_provider_metadata(
                        id=part.id, provider_name=part.provider_name, provider_details=part.provider_details
                    )
                    ui_parts.append(
                        ToolInputAvailablePart(
                            type=tool_name,
                            tool_call_id=part.tool_call_id,
                            input=part.args_as_json_str(),
                            state='input-available',
                            provider_executed=True,
                            call_provider_metadata=call_provider_metadata,
                        )
                    )
            elif isinstance(part, ToolCallPart):
                tool_result = tool_results.get(part.tool_call_id)
                call_provider_metadata = dump_provider_metadata(
                    id=part.id, provider_name=part.provider_name, provider_details=part.provider_details
                )

                if isinstance(tool_result, ToolReturnPart):
                    content = tool_result.model_response_str()
                    ui_parts.append(
                        DynamicToolOutputAvailablePart(
                            tool_name=part.tool_name,
                            tool_call_id=part.tool_call_id,
                            input=part.args_as_json_str(),
                            output=content,
                            state='output-available',
                            call_provider_metadata=call_provider_metadata,
                        )
                    )
                elif isinstance(tool_result, RetryPromptPart):
                    error_text = tool_result.model_response()
                    ui_parts.append(
                        DynamicToolOutputErrorPart(
                            tool_name=part.tool_name,
                            tool_call_id=part.tool_call_id,
                            input=part.args_as_json_str(),
                            error_text=error_text,
                            state='output-error',
                            call_provider_metadata=call_provider_metadata,
                        )
                    )
                else:
                    ui_parts.append(
                        DynamicToolInputAvailablePart(
                            tool_name=part.tool_name,
                            tool_call_id=part.tool_call_id,
                            input=part.args_as_json_str(),
                            state='input-available',
                            call_provider_metadata=call_provider_metadata,
                        )
                    )
            else:
                assert_never(part)

        return ui_parts

    @classmethod
    def dump_messages(
        cls,
        messages: Sequence[ModelMessage],
    ) -> list[UIMessage]:
        """Transform Pydantic AI messages into Vercel AI messages.

        Args:
            messages: A sequence of ModelMessage objects to convert

        Returns:
            A list of UIMessage objects in Vercel AI format
        """
        tool_results: dict[str, ToolReturnPart | RetryPromptPart] = {}

        for msg in messages:
            if isinstance(msg, ModelRequest):
                for part in msg.parts:
                    if isinstance(part, ToolReturnPart):
                        tool_results[part.tool_call_id] = part
                    elif isinstance(part, RetryPromptPart) and part.tool_name:
                        tool_results[part.tool_call_id] = part

        result: list[UIMessage] = []

        for msg in messages:
            if isinstance(msg, ModelRequest):
                system_ui_parts, user_ui_parts = cls._dump_request_message(msg)
                if system_ui_parts:
                    result.append(UIMessage(id=str(uuid.uuid4()), role='system', parts=system_ui_parts))

                if user_ui_parts:
                    result.append(UIMessage(id=str(uuid.uuid4()), role='user', parts=user_ui_parts))

            elif isinstance(  # pragma: no branch
                msg, ModelResponse
            ):
                ui_parts: list[UIMessagePart] = cls._dump_response_message(msg, tool_results)
                if ui_parts:  # pragma: no branch
                    result.append(UIMessage(id=str(uuid.uuid4()), role='assistant', parts=ui_parts))
            else:
                assert_never(msg)

        return result
```

#### sdk_version

```python
sdk_version: Literal[5, 6] = 5
```

Vercel AI SDK version to target. Default is 5 for backwards compatibility.

#### build_run_input

```python
build_run_input(body: bytes) -> RequestData
```

Build a Vercel AI run input object from the request body.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/_adapter.py`

```python
@classmethod
def build_run_input(cls, body: bytes) -> RequestData:
    """Build a Vercel AI run input object from the request body."""
    return request_data_ta.validate_json(body)
```

#### build_event_stream

```python
build_event_stream() -> (
    UIEventStream[
        RequestData, BaseChunk, AgentDepsT, OutputDataT
    ]
)
```

Build a Vercel AI event stream transformer.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/_adapter.py`

```python
def build_event_stream(self) -> UIEventStream[RequestData, BaseChunk, AgentDepsT, OutputDataT]:
    """Build a Vercel AI event stream transformer."""
    return VercelAIEventStream(self.run_input, accept=self.accept, sdk_version=self.sdk_version)
```

#### messages

```python
messages: list[ModelMessage]
```

Pydantic AI messages from the Vercel AI run input.

#### load_messages

```python
load_messages(
    messages: Sequence[UIMessage],
) -> list[ModelMessage]
```

Transform Vercel AI messages into Pydantic AI messages.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/_adapter.py`

```python
@classmethod
def load_messages(cls, messages: Sequence[UIMessage]) -> list[ModelMessage]:  # noqa: C901
    """Transform Vercel AI messages into Pydantic AI messages."""
    builder = MessagesBuilder()

    for msg in messages:
        if msg.role == 'system':
            for part in msg.parts:
                if isinstance(part, TextUIPart):
                    builder.add(SystemPromptPart(content=part.text))
                else:  # pragma: no cover
                    raise ValueError(f'Unsupported system message part type: {type(part)}')
        elif msg.role == 'user':
            user_prompt_content: str | list[UserContent] = []
            for part in msg.parts:
                if isinstance(part, TextUIPart):
                    user_prompt_content.append(part.text)
                elif isinstance(part, FileUIPart):
                    try:
                        file = BinaryContent.from_data_uri(part.url)
                    except ValueError:
                        media_type_prefix = part.media_type.split('/', 1)[0]
                        match media_type_prefix:
                            case 'image':
                                file = ImageUrl(url=part.url, media_type=part.media_type)
                            case 'video':
                                file = VideoUrl(url=part.url, media_type=part.media_type)
                            case 'audio':
                                file = AudioUrl(url=part.url, media_type=part.media_type)
                            case _:
                                file = DocumentUrl(url=part.url, media_type=part.media_type)
                    user_prompt_content.append(file)
                else:  # pragma: no cover
                    raise ValueError(f'Unsupported user message part type: {type(part)}')

            if user_prompt_content:  # pragma: no branch
                if len(user_prompt_content) == 1 and isinstance(user_prompt_content[0], str):
                    user_prompt_content = user_prompt_content[0]
                builder.add(UserPromptPart(content=user_prompt_content))

        elif msg.role == 'assistant':
            for part in msg.parts:
                if isinstance(part, TextUIPart):
                    provider_meta = load_provider_metadata(part.provider_metadata)
                    builder.add(
                        TextPart(
                            content=part.text,
                            id=provider_meta.get('id'),
                            provider_name=provider_meta.get('provider_name'),
                            provider_details=provider_meta.get('provider_details'),
                        )
                    )
                elif isinstance(part, ReasoningUIPart):
                    provider_meta = load_provider_metadata(part.provider_metadata)
                    builder.add(
                        ThinkingPart(
                            content=part.text,
                            id=provider_meta.get('id'),
                            signature=provider_meta.get('signature'),
                            provider_name=provider_meta.get('provider_name'),
                            provider_details=provider_meta.get('provider_details'),
                        )
                    )
                elif isinstance(part, FileUIPart):
                    try:
                        file = BinaryContent.from_data_uri(part.url)
                    except ValueError as e:  # pragma: no cover
                        # We don't yet handle non-data-URI file URLs returned by assistants, as no Pydantic AI models do this.
                        raise ValueError(
                            'Vercel AI integration can currently only handle assistant file parts with data URIs.'
                        ) from e
                    provider_meta = load_provider_metadata(part.provider_metadata)
                    builder.add(
                        FilePart(
                            content=file,
                            id=provider_meta.get('id'),
                            provider_name=provider_meta.get('provider_name'),
                            provider_details=provider_meta.get('provider_details'),
                        )
                    )
                elif isinstance(part, ToolUIPart | DynamicToolUIPart):
                    if isinstance(part, DynamicToolUIPart):
                        tool_name = part.tool_name
                        builtin_tool = False
                    else:
                        tool_name = part.type.removeprefix('tool-')
                        builtin_tool = part.provider_executed

                    tool_call_id = part.tool_call_id

                    args: str | dict[str, Any] | None = part.input

                    if isinstance(args, str):
                        try:
                            parsed = json.loads(args)
                            if isinstance(parsed, dict):
                                args = cast(dict[str, Any], parsed)
                        except json.JSONDecodeError:
                            pass
                    elif isinstance(args, dict) or args is None:
                        pass
                    else:
                        assert_never(args)

                    provider_meta = load_provider_metadata(part.call_provider_metadata)
                    part_id = provider_meta.get('id')
                    provider_name = provider_meta.get('provider_name')
                    provider_details = provider_meta.get('provider_details')

                    if builtin_tool:
                        # For builtin tools, we need to create 2 parts (BuiltinToolCall & BuiltinToolReturn) for a single Vercel ToolOutput
                        # The call and return metadata are combined in the output part.
                        # So we extract and return them to the respective parts
                        call_meta = return_meta = {}
                        has_tool_output = isinstance(part, (ToolOutputAvailablePart, ToolOutputErrorPart))

                        if has_tool_output:
                            call_meta, return_meta = cls._load_builtin_tool_meta(provider_meta)

                        builder.add(
                            BuiltinToolCallPart(
                                tool_name=tool_name,
                                tool_call_id=tool_call_id,
                                args=args,
                                id=call_meta.get('id') or part_id,
                                provider_name=call_meta.get('provider_name') or provider_name,
                                provider_details=call_meta.get('provider_details') or provider_details,
                            )
                        )

                        if has_tool_output:
                            output: Any | None = None
                            if isinstance(part, ToolOutputAvailablePart):
                                output = part.output
                            elif isinstance(part, ToolOutputErrorPart):  # pragma: no branch
                                output = {'error_text': part.error_text, 'is_error': True}
                            builder.add(
                                BuiltinToolReturnPart(
                                    tool_name=tool_name,
                                    tool_call_id=tool_call_id,
                                    content=output,
                                    provider_name=return_meta.get('provider_name') or provider_name,
                                    provider_details=return_meta.get('provider_details') or provider_details,
                                )
                            )
                    else:
                        builder.add(
                            ToolCallPart(
                                tool_name=tool_name,
                                tool_call_id=tool_call_id,
                                args=args,
                                id=part_id,
                                provider_name=provider_name,
                                provider_details=provider_details,
                            )
                        )

                        if part.state == 'output-available':
                            builder.add(
                                ToolReturnPart(tool_name=tool_name, tool_call_id=tool_call_id, content=part.output)
                            )
                        elif part.state == 'output-error':
                            builder.add(
                                RetryPromptPart(
                                    tool_name=tool_name, tool_call_id=tool_call_id, content=part.error_text
                                )
                            )
                elif isinstance(part, DataUIPart):  # pragma: no cover
                    # Contains custom data that shouldn't be sent to the model
                    pass
                elif isinstance(part, SourceUrlUIPart):  # pragma: no cover
                    # TODO: Once we support citations: https://github.com/pydantic/pydantic-ai/issues/3126
                    pass
                elif isinstance(part, SourceDocumentUIPart):  # pragma: no cover
                    # TODO: Once we support citations: https://github.com/pydantic/pydantic-ai/issues/3126
                    pass
                elif isinstance(part, StepStartUIPart):  # pragma: no cover
                    # Nothing to do here
                    pass
                else:
                    assert_never(part)
        else:
            assert_never(msg.role)

    return builder.messages
```

#### dump_messages

```python
dump_messages(
    messages: Sequence[ModelMessage],
) -> list[UIMessage]
```

Transform Pydantic AI messages into Vercel AI messages.

Parameters:

| Name       | Type                     | Description                                   | Default    |
| ---------- | ------------------------ | --------------------------------------------- | ---------- |
| `messages` | `Sequence[ModelMessage]` | A sequence of ModelMessage objects to convert | *required* |

Returns:

| Type              | Description                                     |
| ----------------- | ----------------------------------------------- |
| `list[UIMessage]` | A list of UIMessage objects in Vercel AI format |

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/_adapter.py`

```python
@classmethod
def dump_messages(
    cls,
    messages: Sequence[ModelMessage],
) -> list[UIMessage]:
    """Transform Pydantic AI messages into Vercel AI messages.

    Args:
        messages: A sequence of ModelMessage objects to convert

    Returns:
        A list of UIMessage objects in Vercel AI format
    """
    tool_results: dict[str, ToolReturnPart | RetryPromptPart] = {}

    for msg in messages:
        if isinstance(msg, ModelRequest):
            for part in msg.parts:
                if isinstance(part, ToolReturnPart):
                    tool_results[part.tool_call_id] = part
                elif isinstance(part, RetryPromptPart) and part.tool_name:
                    tool_results[part.tool_call_id] = part

    result: list[UIMessage] = []

    for msg in messages:
        if isinstance(msg, ModelRequest):
            system_ui_parts, user_ui_parts = cls._dump_request_message(msg)
            if system_ui_parts:
                result.append(UIMessage(id=str(uuid.uuid4()), role='system', parts=system_ui_parts))

            if user_ui_parts:
                result.append(UIMessage(id=str(uuid.uuid4()), role='user', parts=user_ui_parts))

        elif isinstance(  # pragma: no branch
            msg, ModelResponse
        ):
            ui_parts: list[UIMessagePart] = cls._dump_response_message(msg, tool_results)
            if ui_parts:  # pragma: no branch
                result.append(UIMessage(id=str(uuid.uuid4()), role='assistant', parts=ui_parts))
        else:
            assert_never(msg)

    return result
```

### VercelAIEventStream

Bases: `UIEventStream[RequestData, BaseChunk, AgentDepsT, OutputDataT]`

UI event stream transformer for the Vercel AI protocol.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/_event_stream.py`

```python
@dataclass
class VercelAIEventStream(UIEventStream[RequestData, BaseChunk, AgentDepsT, OutputDataT]):
    """UI event stream transformer for the Vercel AI protocol."""

    _: KW_ONLY
    sdk_version: Literal[5, 6] = 5
    """Vercel AI SDK version to target."""

    _step_started: bool = False
    _finish_reason: FinishReason = None

    @property
    def response_headers(self) -> Mapping[str, str] | None:
        return VERCEL_AI_DSP_HEADERS

    def encode_event(self, event: BaseChunk) -> str:
        return f'data: {event.encode(self.sdk_version)}\n\n'

    async def before_stream(self) -> AsyncIterator[BaseChunk]:
        yield StartChunk()

    async def before_response(self) -> AsyncIterator[BaseChunk]:
        if self._step_started:
            yield FinishStepChunk()

        self._step_started = True
        yield StartStepChunk()

    async def after_stream(self) -> AsyncIterator[BaseChunk]:
        yield FinishStepChunk()

        yield FinishChunk(finish_reason=self._finish_reason)
        yield DoneChunk()

    async def handle_run_result(self, event: AgentRunResultEvent) -> AsyncIterator[BaseChunk]:
        pydantic_reason = event.result.response.finish_reason
        if pydantic_reason:
            self._finish_reason = _FINISH_REASON_MAP.get(pydantic_reason, 'other')
        return
        yield

    async def on_error(self, error: Exception) -> AsyncIterator[BaseChunk]:
        self._finish_reason = 'error'
        yield ErrorChunk(error_text=str(error))

    async def handle_text_start(self, part: TextPart, follows_text: bool = False) -> AsyncIterator[BaseChunk]:
        provider_metadata = dump_provider_metadata(
            id=part.id, provider_name=part.provider_name, provider_details=part.provider_details
        )
        if follows_text:
            message_id = self.message_id
        else:
            message_id = self.new_message_id()
            yield TextStartChunk(id=message_id, provider_metadata=provider_metadata)

        if part.content:
            yield TextDeltaChunk(id=message_id, delta=part.content, provider_metadata=provider_metadata)

    async def handle_text_delta(self, delta: TextPartDelta) -> AsyncIterator[BaseChunk]:
        if delta.content_delta:  # pragma: no branch
            provider_metadata = dump_provider_metadata(
                provider_name=delta.provider_name, provider_details=delta.provider_details
            )
            yield TextDeltaChunk(id=self.message_id, delta=delta.content_delta, provider_metadata=provider_metadata)

    async def handle_text_end(self, part: TextPart, followed_by_text: bool = False) -> AsyncIterator[BaseChunk]:
        if not followed_by_text:
            provider_metadata = dump_provider_metadata(
                id=part.id, provider_name=part.provider_name, provider_details=part.provider_details
            )
            yield TextEndChunk(id=self.message_id, provider_metadata=provider_metadata)

    async def handle_thinking_start(
        self, part: ThinkingPart, follows_thinking: bool = False
    ) -> AsyncIterator[BaseChunk]:
        message_id = self.new_message_id()
        provider_metadata = dump_provider_metadata(
            id=part.id,
            signature=part.signature,
            provider_name=part.provider_name,
            provider_details=part.provider_details,
        )
        yield ReasoningStartChunk(id=message_id, provider_metadata=provider_metadata)
        if part.content:
            yield ReasoningDeltaChunk(id=message_id, delta=part.content, provider_metadata=provider_metadata)

    async def handle_thinking_delta(self, delta: ThinkingPartDelta) -> AsyncIterator[BaseChunk]:
        if delta.content_delta:  # pragma: no branch
            provider_metadata = dump_provider_metadata(
                provider_name=delta.provider_name,
                signature=delta.signature_delta,
                provider_details=delta.provider_details,
            )
            yield ReasoningDeltaChunk(
                id=self.message_id, delta=delta.content_delta, provider_metadata=provider_metadata
            )

    async def handle_thinking_end(
        self, part: ThinkingPart, followed_by_thinking: bool = False
    ) -> AsyncIterator[BaseChunk]:
        provider_metadata = dump_provider_metadata(
            id=part.id,
            signature=part.signature,
            provider_name=part.provider_name,
            provider_details=part.provider_details,
        )
        yield ReasoningEndChunk(id=self.message_id, provider_metadata=provider_metadata)

    def handle_tool_call_start(self, part: ToolCallPart | BuiltinToolCallPart) -> AsyncIterator[BaseChunk]:
        return self._handle_tool_call_start(part)

    def handle_builtin_tool_call_start(self, part: BuiltinToolCallPart) -> AsyncIterator[BaseChunk]:
        return self._handle_tool_call_start(part, provider_executed=True)

    async def _handle_tool_call_start(
        self,
        part: ToolCallPart | BuiltinToolCallPart,
        tool_call_id: str | None = None,
        provider_executed: bool | None = None,
    ) -> AsyncIterator[BaseChunk]:
        tool_call_id = tool_call_id or part.tool_call_id
        yield ToolInputStartChunk(
            tool_call_id=tool_call_id,
            tool_name=part.tool_name,
            provider_executed=provider_executed,
            provider_metadata=dump_provider_metadata(
                id=part.id, provider_name=part.provider_name, provider_details=part.provider_details
            ),
        )
        if part.args:
            yield ToolInputDeltaChunk(tool_call_id=tool_call_id, input_text_delta=part.args_as_json_str())

    async def handle_tool_call_delta(self, delta: ToolCallPartDelta) -> AsyncIterator[BaseChunk]:
        tool_call_id = delta.tool_call_id or ''
        assert tool_call_id, '`ToolCallPartDelta.tool_call_id` must be set'
        yield ToolInputDeltaChunk(
            tool_call_id=tool_call_id,
            input_text_delta=delta.args_delta if isinstance(delta.args_delta, str) else _json_dumps(delta.args_delta),
        )

    async def handle_tool_call_end(self, part: ToolCallPart) -> AsyncIterator[BaseChunk]:
        yield ToolInputAvailableChunk(
            tool_call_id=part.tool_call_id,
            tool_name=part.tool_name,
            input=part.args_as_dict(),
            provider_metadata=dump_provider_metadata(
                id=part.id, provider_name=part.provider_name, provider_details=part.provider_details
            ),
        )

    async def handle_builtin_tool_call_end(self, part: BuiltinToolCallPart) -> AsyncIterator[BaseChunk]:
        yield ToolInputAvailableChunk(
            tool_call_id=part.tool_call_id,
            tool_name=part.tool_name,
            input=part.args_as_dict(),
            provider_executed=True,
            provider_metadata=dump_provider_metadata(
                id=part.id, provider_name=part.provider_name, provider_details=part.provider_details
            ),
        )

    async def handle_builtin_tool_return(self, part: BuiltinToolReturnPart) -> AsyncIterator[BaseChunk]:
        yield ToolOutputAvailableChunk(
            tool_call_id=part.tool_call_id,
            output=self._tool_return_output(part),
            provider_executed=True,
        )

    async def handle_file(self, part: FilePart) -> AsyncIterator[BaseChunk]:
        file = part.content
        yield FileChunk(url=file.data_uri, media_type=file.media_type)

    async def handle_function_tool_result(self, event: FunctionToolResultEvent) -> AsyncIterator[BaseChunk]:
        part = event.result
        if isinstance(part, RetryPromptPart):
            yield ToolOutputErrorChunk(tool_call_id=part.tool_call_id, error_text=part.model_response())
        else:
            yield ToolOutputAvailableChunk(tool_call_id=part.tool_call_id, output=self._tool_return_output(part))

        # ToolCallResultEvent.content may hold user parts (e.g. text, images) that Vercel AI does not currently have events for

    def _tool_return_output(self, part: BaseToolReturnPart) -> Any:
        output = part.model_response_object()
        # Unwrap the return value from the output dictionary if it exists
        return output.get('return_value', output)
```

#### sdk_version

```python
sdk_version: Literal[5, 6] = 5
```

Vercel AI SDK version to target.

Vercel AI request types (UI messages).

Converted to Python from: https://github.com/vercel/ai/blob/ai%406.0.57/packages/ai/src/ui/ui-messages.ts

### ProviderMetadata

```python
ProviderMetadata = dict[str, dict[str, JSONValue]]
```

Provider metadata.

### BaseUIPart

Bases: `CamelBaseModel`, `ABC`

Abstract base class for all UI parts.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/request_types.py`

```python
class BaseUIPart(CamelBaseModel, ABC):
    """Abstract base class for all UI parts."""
```

### TextUIPart

Bases: `BaseUIPart`

A text part of a message.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/request_types.py`

```python
class TextUIPart(BaseUIPart):
    """A text part of a message."""

    type: Literal['text'] = 'text'

    text: str
    """The text content."""

    state: Literal['streaming', 'done'] | None = None
    """The state of the text part."""

    provider_metadata: ProviderMetadata | None = None
    """The provider metadata."""
```

#### text

```python
text: str
```

The text content.

#### state

```python
state: Literal['streaming', 'done'] | None = None
```

The state of the text part.

#### provider_metadata

```python
provider_metadata: ProviderMetadata | None = None
```

The provider metadata.

### ReasoningUIPart

Bases: `BaseUIPart`

A reasoning part of a message.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/request_types.py`

```python
class ReasoningUIPart(BaseUIPart):
    """A reasoning part of a message."""

    type: Literal['reasoning'] = 'reasoning'

    text: str
    """The reasoning text."""

    state: Literal['streaming', 'done'] | None = None
    """The state of the reasoning part."""

    provider_metadata: ProviderMetadata | None = None
    """The provider metadata."""
```

#### text

```python
text: str
```

The reasoning text.

#### state

```python
state: Literal['streaming', 'done'] | None = None
```

The state of the reasoning part.

#### provider_metadata

```python
provider_metadata: ProviderMetadata | None = None
```

The provider metadata.

### SourceUrlUIPart

Bases: `BaseUIPart`

A source part of a message.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/request_types.py`

```python
class SourceUrlUIPart(BaseUIPart):
    """A source part of a message."""

    type: Literal['source-url'] = 'source-url'
    source_id: str
    url: str
    title: str | None = None
    provider_metadata: ProviderMetadata | None = None
```

### SourceDocumentUIPart

Bases: `BaseUIPart`

A document source part of a message.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/request_types.py`

```python
class SourceDocumentUIPart(BaseUIPart):
    """A document source part of a message."""

    type: Literal['source-document'] = 'source-document'
    source_id: str
    media_type: str
    title: str
    filename: str | None = None
    provider_metadata: ProviderMetadata | None = None
```

### FileUIPart

Bases: `BaseUIPart`

A file part of a message.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/request_types.py`

```python
class FileUIPart(BaseUIPart):
    """A file part of a message."""

    type: Literal['file'] = 'file'

    media_type: str
    """
    IANA media type of the file.
    @see https://www.iana.org/assignments/media-types/media-types.xhtml
    """

    filename: str | None = None
    """Optional filename of the file."""

    url: str
    """
    The URL of the file.
    It can either be a URL to a hosted file or a [Data URL](https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/Data_URLs).
    """

    provider_metadata: ProviderMetadata | None = None
    """The provider metadata."""
```

#### media_type

```python
media_type: str
```

IANA media type of the file. @see https://www.iana.org/assignments/media-types/media-types.xhtml

#### filename

```python
filename: str | None = None
```

Optional filename of the file.

#### url

```python
url: str
```

The URL of the file. It can either be a URL to a hosted file or a [Data URL](https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/Data_URLs).

#### provider_metadata

```python
provider_metadata: ProviderMetadata | None = None
```

The provider metadata.

### StepStartUIPart

Bases: `BaseUIPart`

A step boundary part of a message.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/request_types.py`

```python
class StepStartUIPart(BaseUIPart):
    """A step boundary part of a message."""

    type: Literal['step-start'] = 'step-start'
```

### DataUIPart

Bases: `BaseUIPart`

Data part with dynamic type based on data name.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/request_types.py`

```python
class DataUIPart(BaseUIPart):
    """Data part with dynamic type based on data name."""

    type: Annotated[str, Field(pattern=r'^data-')]
    id: str | None = None
    data: Any
```

### ToolInputStreamingPart

Bases: `BaseUIPart`

Tool part in input-streaming state.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/request_types.py`

```python
class ToolInputStreamingPart(BaseUIPart):
    """Tool part in input-streaming state."""

    type: Annotated[str, Field(pattern=r'^tool-')]
    tool_call_id: str
    state: Literal['input-streaming'] = 'input-streaming'
    input: Any | None = None
    provider_executed: bool | None = None
    call_provider_metadata: ProviderMetadata | None = None
```

### ToolInputAvailablePart

Bases: `BaseUIPart`

Tool part in input-available state.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/request_types.py`

```python
class ToolInputAvailablePart(BaseUIPart):
    """Tool part in input-available state."""

    type: Annotated[str, Field(pattern=r'^tool-')]
    tool_call_id: str
    state: Literal['input-available'] = 'input-available'
    input: Any | None = None
    provider_executed: bool | None = None
    call_provider_metadata: ProviderMetadata | None = None
```

### ToolOutputAvailablePart

Bases: `BaseUIPart`

Tool part in output-available state.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/request_types.py`

```python
class ToolOutputAvailablePart(BaseUIPart):
    """Tool part in output-available state."""

    type: Annotated[str, Field(pattern=r'^tool-')]
    tool_call_id: str
    state: Literal['output-available'] = 'output-available'
    input: Any | None = None
    output: Any | None = None
    provider_executed: bool | None = None
    call_provider_metadata: ProviderMetadata | None = None
    preliminary: bool | None = None
```

### ToolOutputErrorPart

Bases: `BaseUIPart`

Tool part in output-error state.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/request_types.py`

```python
class ToolOutputErrorPart(BaseUIPart):
    """Tool part in output-error state."""

    type: Annotated[str, Field(pattern=r'^tool-')]
    tool_call_id: str
    state: Literal['output-error'] = 'output-error'
    input: Any | None = None
    raw_input: Any | None = None
    error_text: str
    provider_executed: bool | None = None
    call_provider_metadata: ProviderMetadata | None = None
```

### ToolUIPart

```python
ToolUIPart = (
    ToolInputStreamingPart
    | ToolInputAvailablePart
    | ToolOutputAvailablePart
    | ToolOutputErrorPart
)
```

Union of all tool part types.

### DynamicToolInputStreamingPart

Bases: `BaseUIPart`

Dynamic tool part in input-streaming state.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/request_types.py`

```python
class DynamicToolInputStreamingPart(BaseUIPart):
    """Dynamic tool part in input-streaming state."""

    type: Literal['dynamic-tool'] = 'dynamic-tool'
    tool_name: str
    tool_call_id: str
    state: Literal['input-streaming'] = 'input-streaming'
    input: Any | None = None
    call_provider_metadata: ProviderMetadata | None = None
```

### DynamicToolInputAvailablePart

Bases: `BaseUIPart`

Dynamic tool part in input-available state.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/request_types.py`

```python
class DynamicToolInputAvailablePart(BaseUIPart):
    """Dynamic tool part in input-available state."""

    type: Literal['dynamic-tool'] = 'dynamic-tool'
    tool_name: str
    tool_call_id: str
    state: Literal['input-available'] = 'input-available'
    input: Any
    call_provider_metadata: ProviderMetadata | None = None
```

### DynamicToolOutputAvailablePart

Bases: `BaseUIPart`

Dynamic tool part in output-available state.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/request_types.py`

```python
class DynamicToolOutputAvailablePart(BaseUIPart):
    """Dynamic tool part in output-available state."""

    type: Literal['dynamic-tool'] = 'dynamic-tool'
    tool_name: str
    tool_call_id: str
    state: Literal['output-available'] = 'output-available'
    input: Any
    output: Any
    call_provider_metadata: ProviderMetadata | None = None
    preliminary: bool | None = None
```

### DynamicToolOutputErrorPart

Bases: `BaseUIPart`

Dynamic tool part in output-error state.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/request_types.py`

```python
class DynamicToolOutputErrorPart(BaseUIPart):
    """Dynamic tool part in output-error state."""

    type: Literal['dynamic-tool'] = 'dynamic-tool'
    tool_name: str
    tool_call_id: str
    state: Literal['output-error'] = 'output-error'
    input: Any
    error_text: str
    call_provider_metadata: ProviderMetadata | None = None
```

### DynamicToolUIPart

```python
DynamicToolUIPart = (
    DynamicToolInputStreamingPart
    | DynamicToolInputAvailablePart
    | DynamicToolOutputAvailablePart
    | DynamicToolOutputErrorPart
)
```

Union of all dynamic tool part types.

### UIMessagePart

```python
UIMessagePart = (
    TextUIPart
    | ReasoningUIPart
    | ToolUIPart
    | DynamicToolUIPart
    | SourceUrlUIPart
    | SourceDocumentUIPart
    | FileUIPart
    | DataUIPart
    | StepStartUIPart
)
```

Union of all message part types.

### UIMessage

Bases: `CamelBaseModel`

A message as displayed in the UI by Vercel AI Elements.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/request_types.py`

```python
class UIMessage(CamelBaseModel):
    """A message as displayed in the UI by Vercel AI Elements."""

    id: str
    """A unique identifier for the message."""

    role: Literal['system', 'user', 'assistant']
    """The role of the message."""

    metadata: Any | None = None
    """The metadata of the message."""

    parts: list[UIMessagePart]
    """
    The parts of the message. Use this for rendering the message in the UI.
    System messages should be avoided (set the system prompt on the server instead).
    They can have text parts.
    User messages can have text parts and file parts.
    Assistant messages can have text, reasoning, tool invocation, and file parts.
    """
```

#### id

```python
id: str
```

A unique identifier for the message.

#### role

```python
role: Literal['system', 'user', 'assistant']
```

The role of the message.

#### metadata

```python
metadata: Any | None = None
```

The metadata of the message.

#### parts

```python
parts: list[UIMessagePart]
```

The parts of the message. Use this for rendering the message in the UI. System messages should be avoided (set the system prompt on the server instead). They can have text parts. User messages can have text parts and file parts. Assistant messages can have text, reasoning, tool invocation, and file parts.

### SubmitMessage

Bases: `CamelBaseModel`

Submit message request.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/request_types.py`

```python
class SubmitMessage(CamelBaseModel, extra='allow'):
    """Submit message request."""

    trigger: Literal['submit-message'] = 'submit-message'
    id: str
    messages: list[UIMessage]
```

### RegenerateMessage

Bases: `CamelBaseModel`

Ask the agent to regenerate a message.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/request_types.py`

```python
class RegenerateMessage(CamelBaseModel, extra='allow'):
    """Ask the agent to regenerate a message."""

    trigger: Literal['regenerate-message']
    id: str
    messages: list[UIMessage]
    message_id: str
```

### RequestData

```python
RequestData = Annotated[
    SubmitMessage | RegenerateMessage,
    Discriminator("trigger"),
]
```

Union of all request data types.

Vercel AI response types (SSE chunks).

Converted to Python from: https://github.com/vercel/ai/blob/ai%406.0.57/packages/ai/src/ui-message-stream/ui-message-chunks.ts

### ProviderMetadata

```python
ProviderMetadata = dict[str, dict[str, JSONValue]]
```

Provider metadata.

### FinishReason

```python
FinishReason = (
    Literal[
        "stop",
        "length",
        "content-filter",
        "tool-calls",
        "error",
        "other",
    ]
    | None
)
```

Reason why the model finished generating.

### BaseChunk

Bases: `CamelBaseModel`, `ABC`

Abstract base class for response SSE events.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/response_types.py`

```python
class BaseChunk(CamelBaseModel, ABC):
    """Abstract base class for response SSE events."""

    def encode(self, sdk_version: int) -> str:
        return self.model_dump_json(by_alias=True, exclude_none=True)
```

### TextStartChunk

Bases: `BaseChunk`

Text start chunk.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/response_types.py`

```python
class TextStartChunk(BaseChunk):
    """Text start chunk."""

    type: Literal['text-start'] = 'text-start'
    id: str
    provider_metadata: ProviderMetadata | None = None
```

### TextDeltaChunk

Bases: `BaseChunk`

Text delta chunk.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/response_types.py`

```python
class TextDeltaChunk(BaseChunk):
    """Text delta chunk."""

    type: Literal['text-delta'] = 'text-delta'
    delta: str
    id: str
    provider_metadata: ProviderMetadata | None = None
```

### TextEndChunk

Bases: `BaseChunk`

Text end chunk.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/response_types.py`

```python
class TextEndChunk(BaseChunk):
    """Text end chunk."""

    type: Literal['text-end'] = 'text-end'
    id: str
    provider_metadata: ProviderMetadata | None = None
```

### ReasoningStartChunk

Bases: `BaseChunk`

Reasoning start chunk.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/response_types.py`

```python
class ReasoningStartChunk(BaseChunk):
    """Reasoning start chunk."""

    type: Literal['reasoning-start'] = 'reasoning-start'
    id: str
    provider_metadata: ProviderMetadata | None = None
```

### ReasoningDeltaChunk

Bases: `BaseChunk`

Reasoning delta chunk.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/response_types.py`

```python
class ReasoningDeltaChunk(BaseChunk):
    """Reasoning delta chunk."""

    type: Literal['reasoning-delta'] = 'reasoning-delta'
    id: str
    delta: str
    provider_metadata: ProviderMetadata | None = None
```

### ReasoningEndChunk

Bases: `BaseChunk`

Reasoning end chunk.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/response_types.py`

```python
class ReasoningEndChunk(BaseChunk):
    """Reasoning end chunk."""

    type: Literal['reasoning-end'] = 'reasoning-end'
    id: str
    provider_metadata: ProviderMetadata | None = None
```

### ErrorChunk

Bases: `BaseChunk`

Error chunk.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/response_types.py`

```python
class ErrorChunk(BaseChunk):
    """Error chunk."""

    type: Literal['error'] = 'error'
    error_text: str
```

### ToolInputStartChunk

Bases: `BaseChunk`

Tool input start chunk.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/response_types.py`

```python
class ToolInputStartChunk(BaseChunk):
    """Tool input start chunk."""

    type: Literal['tool-input-start'] = 'tool-input-start'
    tool_call_id: str
    tool_name: str
    provider_executed: bool | None = None
    provider_metadata: ProviderMetadata | None = None
    dynamic: bool | None = None

    def encode(self, sdk_version: int) -> str:
        exclude = {'provider_metadata'} if sdk_version < 6 else None
        return self.model_dump_json(by_alias=True, exclude_none=True, exclude=exclude)
```

### ToolInputDeltaChunk

Bases: `BaseChunk`

Tool input delta chunk.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/response_types.py`

```python
class ToolInputDeltaChunk(BaseChunk):
    """Tool input delta chunk."""

    type: Literal['tool-input-delta'] = 'tool-input-delta'
    tool_call_id: str
    input_text_delta: str
```

### ToolOutputAvailableChunk

Bases: `BaseChunk`

Tool output available chunk.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/response_types.py`

```python
class ToolOutputAvailableChunk(BaseChunk):
    """Tool output available chunk."""

    type: Literal['tool-output-available'] = 'tool-output-available'
    tool_call_id: str
    output: Any
    provider_executed: bool | None = None
    dynamic: bool | None = None
    preliminary: bool | None = None
```

### ToolInputAvailableChunk

Bases: `BaseChunk`

Tool input available chunk.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/response_types.py`

```python
class ToolInputAvailableChunk(BaseChunk):
    """Tool input available chunk."""

    type: Literal['tool-input-available'] = 'tool-input-available'
    tool_call_id: str
    tool_name: str
    input: Any
    provider_executed: bool | None = None
    provider_metadata: ProviderMetadata | None = None
    dynamic: bool | None = None
```

### ToolInputErrorChunk

Bases: `BaseChunk`

Tool input error chunk.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/response_types.py`

```python
class ToolInputErrorChunk(BaseChunk):
    """Tool input error chunk."""

    type: Literal['tool-input-error'] = 'tool-input-error'
    tool_call_id: str
    tool_name: str
    input: Any
    provider_executed: bool | None = None
    provider_metadata: ProviderMetadata | None = None
    dynamic: bool | None = None
    error_text: str
```

### ToolOutputErrorChunk

Bases: `BaseChunk`

Tool output error chunk.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/response_types.py`

```python
class ToolOutputErrorChunk(BaseChunk):
    """Tool output error chunk."""

    type: Literal['tool-output-error'] = 'tool-output-error'
    tool_call_id: str
    error_text: str
    provider_executed: bool | None = None
    dynamic: bool | None = None
```

### ToolApprovalRequestChunk

Bases: `BaseChunk`

Tool approval request chunk for human-in-the-loop approval.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/response_types.py`

```python
class ToolApprovalRequestChunk(BaseChunk):
    """Tool approval request chunk for human-in-the-loop approval."""

    type: Literal['tool-approval-request'] = 'tool-approval-request'
    approval_id: str
    tool_call_id: str
```

### ToolOutputDeniedChunk

Bases: `BaseChunk`

Tool output denied chunk when user denies tool execution.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/response_types.py`

```python
class ToolOutputDeniedChunk(BaseChunk):
    """Tool output denied chunk when user denies tool execution."""

    type: Literal['tool-output-denied'] = 'tool-output-denied'
    tool_call_id: str
```

### SourceUrlChunk

Bases: `BaseChunk`

Source URL chunk.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/response_types.py`

```python
class SourceUrlChunk(BaseChunk):
    """Source URL chunk."""

    type: Literal['source-url'] = 'source-url'
    source_id: str
    url: str
    title: str | None = None
    provider_metadata: ProviderMetadata | None = None
```

### SourceDocumentChunk

Bases: `BaseChunk`

Source document chunk.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/response_types.py`

```python
class SourceDocumentChunk(BaseChunk):
    """Source document chunk."""

    type: Literal['source-document'] = 'source-document'
    source_id: str
    media_type: str
    title: str
    filename: str | None = None
    provider_metadata: ProviderMetadata | None = None
```

### FileChunk

Bases: `BaseChunk`

File chunk.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/response_types.py`

```python
class FileChunk(BaseChunk):
    """File chunk."""

    type: Literal['file'] = 'file'
    url: str
    media_type: str
```

### DataChunk

Bases: `BaseChunk`

Data chunk with dynamic type.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/response_types.py`

```python
class DataChunk(BaseChunk):
    """Data chunk with dynamic type."""

    type: Annotated[str, Field(pattern=r'^data-')]
    id: str | None = None
    data: Any
    transient: bool | None = None
```

### StartStepChunk

Bases: `BaseChunk`

Start step chunk.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/response_types.py`

```python
class StartStepChunk(BaseChunk):
    """Start step chunk."""

    type: Literal['start-step'] = 'start-step'
```

### FinishStepChunk

Bases: `BaseChunk`

Finish step chunk.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/response_types.py`

```python
class FinishStepChunk(BaseChunk):
    """Finish step chunk."""

    type: Literal['finish-step'] = 'finish-step'
```

### StartChunk

Bases: `BaseChunk`

Start chunk.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/response_types.py`

```python
class StartChunk(BaseChunk):
    """Start chunk."""

    type: Literal['start'] = 'start'
    message_id: str | None = None
    message_metadata: Any | None = None
```

### FinishChunk

Bases: `BaseChunk`

Finish chunk.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/response_types.py`

```python
class FinishChunk(BaseChunk):
    """Finish chunk."""

    type: Literal['finish'] = 'finish'
    finish_reason: FinishReason = None
    message_metadata: Any | None = None
```

### AbortChunk

Bases: `BaseChunk`

Abort chunk.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/response_types.py`

```python
class AbortChunk(BaseChunk):
    """Abort chunk."""

    type: Literal['abort'] = 'abort'
    reason: str | None = None
```

### MessageMetadataChunk

Bases: `BaseChunk`

Message metadata chunk.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/response_types.py`

```python
class MessageMetadataChunk(BaseChunk):
    """Message metadata chunk."""

    type: Literal['message-metadata'] = 'message-metadata'
    message_metadata: Any
```

### DoneChunk

Bases: `BaseChunk`

Done chunk.

Source code in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/response_types.py`

```python
class DoneChunk(BaseChunk):
    """Done chunk."""

    type: Literal['done'] = 'done'

    def encode(self, sdk_version: int) -> str:
        return '[DONE]'
```
