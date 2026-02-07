# pydantic_ai.models.mcp_sampling

### MCPSamplingModelSettings

Bases: `ModelSettings`

Settings used for an MCP Sampling model request.

Source code in `pydantic_ai_slim/pydantic_ai/models/mcp_sampling.py`

```python
class MCPSamplingModelSettings(ModelSettings, total=False):
    """Settings used for an MCP Sampling model request."""

    # ALL FIELDS MUST BE `mcp_` PREFIXED SO YOU CAN MERGE THEM WITH OTHER MODELS.

    mcp_model_preferences: ModelPreferences
    """Model preferences to use for MCP Sampling."""
```

#### mcp_model_preferences

```python
mcp_model_preferences: ModelPreferences
```

Model preferences to use for MCP Sampling.

### MCPSamplingModel

Bases: `Model`

A model that uses MCP Sampling.

[MCP Sampling](https://modelcontextprotocol.io/docs/concepts/sampling) allows an MCP server to make requests to a model by calling back to the MCP client that connected to it.

Source code in `pydantic_ai_slim/pydantic_ai/models/mcp_sampling.py`

```python
@dataclass
class MCPSamplingModel(Model):
    """A model that uses MCP Sampling.

    [MCP Sampling](https://modelcontextprotocol.io/docs/concepts/sampling)
    allows an MCP server to make requests to a model by calling back to the MCP client that connected to it.
    """

    session: ServerSession
    """The MCP server session to use for sampling."""

    _: KW_ONLY

    default_max_tokens: int = 16_384
    """Default max tokens to use if not set in [`ModelSettings`][pydantic_ai.settings.ModelSettings.max_tokens].

    Max tokens is a required parameter for MCP Sampling, but optional on
    [`ModelSettings`][pydantic_ai.settings.ModelSettings], so this value is used as fallback.
    """

    async def request(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> ModelResponse:
        system_prompt, sampling_messages = _mcp.map_from_pai_messages(messages)

        model_settings, _ = self.prepare_request(model_settings, model_request_parameters)
        model_settings = cast(MCPSamplingModelSettings, model_settings or {})

        result = await self.session.create_message(
            sampling_messages,
            max_tokens=model_settings.get('max_tokens', self.default_max_tokens),
            system_prompt=system_prompt,
            temperature=model_settings.get('temperature'),
            model_preferences=model_settings.get('mcp_model_preferences'),
            stop_sequences=model_settings.get('stop_sequences'),
        )
        if result.role == 'assistant':
            return ModelResponse(
                parts=[_mcp.map_from_sampling_content(result.content)],
                model_name=result.model,
            )
        else:
            raise exceptions.UnexpectedModelBehavior(
                f'Unexpected result from MCP sampling, expected "assistant" role, got {result.role}.'
            )

    @asynccontextmanager
    async def request_stream(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
        run_context: RunContext[Any] | None = None,
    ) -> AsyncIterator[StreamedResponse]:
        raise NotImplementedError('MCP Sampling does not support streaming')
        yield

    @property
    def model_name(self) -> str:
        """The model name.

        Since the model name isn't known until the request is made, this property always returns `'mcp-sampling'`.
        """
        return 'mcp-sampling'

    @property
    def system(self) -> str:
        """The system / model provider, returns `'MCP'`."""
        return 'MCP'
```

#### session

```python
session: ServerSession
```

The MCP server session to use for sampling.

#### default_max_tokens

```python
default_max_tokens: int = 16384
```

Default max tokens to use if not set in ModelSettings.

Max tokens is a required parameter for MCP Sampling, but optional on ModelSettings, so this value is used as fallback.

#### model_name

```python
model_name: str
```

The model name.

Since the model name isn't known until the request is made, this property always returns `'mcp-sampling'`.

#### system

```python
system: str
```

The system / model provider, returns `'MCP'`.
