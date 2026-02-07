# `pydantic_ai.profiles`

Describes how requests to and responses from specific models or families of models need to be constructed and processed to get the best results, independent of the model and provider classes used.

Source code in `pydantic_ai_slim/pydantic_ai/profiles/__init__.py`

```python
@dataclass(kw_only=True)
class ModelProfile:
    """Describes how requests to and responses from specific models or families of models need to be constructed and processed to get the best results, independent of the model and provider classes used."""

    supports_tools: bool = True
    """Whether the model supports tools."""
    supports_json_schema_output: bool = False
    """Whether the model supports JSON schema output.

    This is also referred to as 'native' support for structured output.
    Relates to the `NativeOutput` output type.
    """
    supports_json_object_output: bool = False
    """Whether the model supports a dedicated mode to enforce JSON output, without necessarily sending a schema.

    E.g. [OpenAI's JSON mode](https://platform.openai.com/docs/guides/structured-outputs#json-mode)
    Relates to the `PromptedOutput` output type.
    """
    supports_image_output: bool = False
    """Whether the model supports image output."""
    default_structured_output_mode: StructuredOutputMode = 'tool'
    """The default structured output mode to use for the model."""
    prompted_output_template: str = dedent(
        """
        Always respond with a JSON object that's compatible with this schema:

        {schema}

        Don't include any text or Markdown fencing before or after.
        """
    )
    """The instructions template to use for prompted structured output. The '{schema}' placeholder will be replaced with the JSON schema for the output."""
    native_output_requires_schema_in_instructions: bool = False
    """Whether to add prompted output template in native structured output mode"""
    json_schema_transformer: type[JsonSchemaTransformer] | None = None
    """The transformer to use to make JSON schemas for tools and structured output compatible with the model."""

    thinking_tags: tuple[str, str] = ('<think>', '</think>')
    """The tags used to indicate thinking parts in the model's output. Defaults to ('<think>', '</think>')."""

    ignore_streamed_leading_whitespace: bool = False
    """Whether to ignore leading whitespace when streaming a response.

    This is a workaround for models that emit `<think>\n</think>\n\n` or an empty text part ahead of tool calls (e.g. Ollama + Qwen3),
    which we don't want to end up treating as a final result when using `run_stream` with `str` a valid `output_type`.

    This is currently only used by `OpenAIChatModel`, `HuggingFaceModel`, and `GroqModel`.
    """

    supported_builtin_tools: frozenset[type[AbstractBuiltinTool]] = field(
        default_factory=lambda: SUPPORTED_BUILTIN_TOOLS
    )
    """The set of builtin tool types that this model/profile supports.

    Defaults to ALL builtin tools. Profile functions should explicitly
    restrict this based on model capabilities.
    """

    @classmethod
    def from_profile(cls, profile: ModelProfile | None) -> Self:
        """Build a ModelProfile subclass instance from a ModelProfile instance."""
        if isinstance(profile, cls):
            return profile
        return cls().update(profile)

    def update(self, profile: ModelProfile | None) -> Self:
        """Update this ModelProfile (subclass) instance with the non-default values from another ModelProfile instance."""
        if not profile:
            return self
        field_names = set(f.name for f in fields(self))
        non_default_attrs = {
            f.name: getattr(profile, f.name)
            for f in fields(profile)
            if f.name in field_names and getattr(profile, f.name) != f.default
        }
        return replace(self, **non_default_attrs)
```

### supports_tools

```python
supports_tools: bool = True
```

Whether the model supports tools.

### supports_json_schema_output

```python
supports_json_schema_output: bool = False
```

Whether the model supports JSON schema output.

This is also referred to as 'native' support for structured output. Relates to the `NativeOutput` output type.

### supports_json_object_output

```python
supports_json_object_output: bool = False
```

Whether the model supports a dedicated mode to enforce JSON output, without necessarily sending a schema.

E.g. [OpenAI's JSON mode](https://platform.openai.com/docs/guides/structured-outputs#json-mode) Relates to the `PromptedOutput` output type.

### supports_image_output

```python
supports_image_output: bool = False
```

Whether the model supports image output.

### default_structured_output_mode

```python
default_structured_output_mode: StructuredOutputMode = (
    "tool"
)
```

The default structured output mode to use for the model.

### prompted_output_template

```python
prompted_output_template: str = dedent(
    "\n        Always respond with a JSON object that's compatible with this schema:\n\n        {schema}\n\n        Don't include any text or Markdown fencing before or after.\n        "
)
```

The instructions template to use for prompted structured output. The '{schema}' placeholder will be replaced with the JSON schema for the output.

### native_output_requires_schema_in_instructions

```python
native_output_requires_schema_in_instructions: bool = False
```

Whether to add prompted output template in native structured output mode

### json_schema_transformer

```python
json_schema_transformer: (
    type[JsonSchemaTransformer] | None
) = None
```

The transformer to use to make JSON schemas for tools and structured output compatible with the model.

### thinking_tags

```python
thinking_tags: tuple[str, str] = ('<think>', '</think>')
```

The tags used to indicate thinking parts in the model's output. Defaults to ('', '').

### ignore_streamed_leading_whitespace

```python
ignore_streamed_leading_whitespace: bool = False
```

Whether to ignore leading whitespace when streaming a response.

```text
This is a workaround for models that emit `<think>
```

`or an empty text part ahead of tool calls (e.g. Ollama + Qwen3), which we don't want to end up treating as a final result when using`run_stream`with`str`a valid`output_type\`.

```text
This is currently only used by `OpenAIChatModel`, `HuggingFaceModel`, and `GroqModel`.
```

### supported_builtin_tools

```python
supported_builtin_tools: frozenset[
    type[AbstractBuiltinTool]
] = field(default_factory=lambda: SUPPORTED_BUILTIN_TOOLS)
```

The set of builtin tool types that this model/profile supports.

Defaults to ALL builtin tools. Profile functions should explicitly restrict this based on model capabilities.

### from_profile

```python
from_profile(profile: ModelProfile | None) -> Self
```

Build a ModelProfile subclass instance from a ModelProfile instance.

Source code in `pydantic_ai_slim/pydantic_ai/profiles/__init__.py`

```python
@classmethod
def from_profile(cls, profile: ModelProfile | None) -> Self:
    """Build a ModelProfile subclass instance from a ModelProfile instance."""
    if isinstance(profile, cls):
        return profile
    return cls().update(profile)
```

### update

```python
update(profile: ModelProfile | None) -> Self
```

Update this ModelProfile (subclass) instance with the non-default values from another ModelProfile instance.

Source code in `pydantic_ai_slim/pydantic_ai/profiles/__init__.py`

```python
def update(self, profile: ModelProfile | None) -> Self:
    """Update this ModelProfile (subclass) instance with the non-default values from another ModelProfile instance."""
    if not profile:
        return self
    field_names = set(f.name for f in fields(self))
    non_default_attrs = {
        f.name: getattr(profile, f.name)
        for f in fields(profile)
        if f.name in field_names and getattr(profile, f.name) != f.default
    }
    return replace(self, **non_default_attrs)
```

### SAMPLING_PARAMS

```python
SAMPLING_PARAMS = (
    "temperature",
    "top_p",
    "presence_penalty",
    "frequency_penalty",
    "logit_bias",
    "openai_logprobs",
    "openai_top_logprobs",
)
```

Sampling parameter names that are incompatible with reasoning.

These parameters are not supported when reasoning is enabled (reasoning_effort != 'none'). See https://platform.openai.com/docs/guides/reasoning for details.

### OpenAIModelProfile

Bases: `ModelProfile`

Profile for models used with `OpenAIChatModel`.

ALL FIELDS MUST BE `openai_` PREFIXED SO YOU CAN MERGE THEM WITH OTHER MODELS.

Source code in `pydantic_ai_slim/pydantic_ai/profiles/openai.py`

```python
@dataclass(kw_only=True)
class OpenAIModelProfile(ModelProfile):
    """Profile for models used with `OpenAIChatModel`.

    ALL FIELDS MUST BE `openai_` PREFIXED SO YOU CAN MERGE THEM WITH OTHER MODELS.
    """

    openai_chat_thinking_field: str | None = None
    """Non-standard field name used by some providers for model thinking content in Chat Completions API responses.

    Plenty of providers use custom field names for thinking content. Ollama and newer versions of vLLM use `reasoning`,
    while DeepSeek, older vLLM and some others use `reasoning_content`.

    Notice that the thinking field configured here is currently limited to `str` type content.

    If `openai_chat_send_back_thinking_parts` is set to `'field'`, this field must be set to a non-None value."""

    openai_chat_send_back_thinking_parts: Literal['auto', 'tags', 'field', False] = 'auto'
    """Whether the model includes thinking content in requests.

    This can be:
    * `'auto'` (default): Automatically detects how to send thinking content. If thinking was received in a custom field
    (tracked via `ThinkingPart.id` and `ThinkingPart.provider_name`), it's sent back in that same field. Otherwise,
    it's sent using tags. Only the `reasoning` and `reasoning_content` fields are checked by
    default when receiving responses. If your provider uses a different field name, you must explicitly set
    `openai_chat_thinking_field` to that field name.
    * `'tags'`: The thinking content is included in the main `content` field, enclosed within thinking tags as
    specified in `thinking_tags` profile option.
    * `'field'`: The thinking content is included in a separate field specified by `openai_chat_thinking_field`.
    * `False`: No thinking content is sent in the request.

    Defaults to `'auto'` to ensure thinking is sent back in the format expected by the model/provider."""

    openai_supports_strict_tool_definition: bool = True
    """This can be set by a provider or user if the OpenAI-"compatible" API doesn't support strict tool definitions."""

    openai_supports_sampling_settings: bool = True
    """Turn off to don't send sampling settings like `temperature` and `top_p` to models that don't support them, like OpenAI's o-series reasoning models."""

    openai_unsupported_model_settings: Sequence[str] = ()
    """A list of model settings that are not supported by this model."""

    # Some OpenAI-compatible providers (e.g. MoonshotAI) currently do **not** accept
    # `tool_choice="required"`.  This flag lets the calling model know whether it's
    # safe to pass that value along.  Default is `True` to preserve existing
    # behaviour for OpenAI itself and most providers.
    openai_supports_tool_choice_required: bool = True
    """Whether the provider accepts the value ``tool_choice='required'`` in the request payload."""

    openai_system_prompt_role: OpenAISystemPromptRole | None = None
    """The role to use for the system prompt message. If not provided, defaults to `'system'`."""

    openai_chat_supports_web_search: bool = False
    """Whether the model supports web search in Chat Completions API."""

    openai_chat_audio_input_encoding: Literal['base64', 'uri'] = 'base64'
    """The encoding to use for audio input in Chat Completions requests.

    - `'base64'`: Raw base64 encoded string. (Default, used by OpenAI)
    - `'uri'`: Data URI (e.g. `data:audio/wav;base64,...`).
    """

    openai_chat_supports_file_urls: bool = False
    """Whether the Chat API supports file URLs directly in the `file_data` field.

    OpenAI's native Chat API only supports base64-encoded data, but some providers
    like OpenRouter support passing URLs directly.
    """

    openai_supports_encrypted_reasoning_content: bool = False
    """Whether the model supports including encrypted reasoning content in the response."""

    openai_supports_reasoning: bool = False
    """Whether the model supports reasoning (o-series, GPT-5+).

    When True, sampling parameters may need to be dropped depending on reasoning_effort setting."""

    openai_supports_reasoning_effort_none: bool = False
    """Whether the model supports sampling parameters (temperature, top_p, etc.) when reasoning_effort='none'.

    Models like GPT-5.1 and GPT-5.2 default to reasoning_effort='none' and support sampling params in that mode.
    When reasoning is enabled (low/medium/high/xhigh), sampling params are not supported."""

    openai_responses_requires_function_call_status_none: bool = False
    """Whether the Responses API requires the `status` field on function tool calls to be `None`.

    This is required by vLLM Responses API versions before https://github.com/vllm-project/vllm/pull/26706.
    See https://github.com/pydantic/pydantic-ai/issues/3245 for more details.
    """

    def __post_init__(self):  # pragma: no cover
        if not self.openai_supports_sampling_settings:
            warnings.warn(
                'The `openai_supports_sampling_settings` has no effect, and it will be removed in future versions. '
                'Use `openai_unsupported_model_settings` instead.',
                DeprecationWarning,
            )
        if self.openai_chat_send_back_thinking_parts == 'field' and not self.openai_chat_thinking_field:
            raise UserError(
                'If `openai_chat_send_back_thinking_parts` is "field", '
                '`openai_chat_thinking_field` must be set to a non-None value.'
            )
```

#### openai_chat_thinking_field

```python
openai_chat_thinking_field: str | None = None
```

Non-standard field name used by some providers for model thinking content in Chat Completions API responses.

Plenty of providers use custom field names for thinking content. Ollama and newer versions of vLLM use `reasoning`, while DeepSeek, older vLLM and some others use `reasoning_content`.

Notice that the thinking field configured here is currently limited to `str` type content.

If `openai_chat_send_back_thinking_parts` is set to `'field'`, this field must be set to a non-None value.

#### openai_chat_send_back_thinking_parts

```python
openai_chat_send_back_thinking_parts: Literal[
    "auto", "tags", "field", False
] = "auto"
```

Whether the model includes thinking content in requests.

This can be: * `'auto'` (default): Automatically detects how to send thinking content. If thinking was received in a custom field (tracked via `ThinkingPart.id` and `ThinkingPart.provider_name`), it's sent back in that same field. Otherwise, it's sent using tags. Only the `reasoning` and `reasoning_content` fields are checked by default when receiving responses. If your provider uses a different field name, you must explicitly set `openai_chat_thinking_field` to that field name. * `'tags'`: The thinking content is included in the main `content` field, enclosed within thinking tags as specified in `thinking_tags` profile option. * `'field'`: The thinking content is included in a separate field specified by `openai_chat_thinking_field`. * `False`: No thinking content is sent in the request.

Defaults to `'auto'` to ensure thinking is sent back in the format expected by the model/provider.

#### openai_supports_strict_tool_definition

```python
openai_supports_strict_tool_definition: bool = True
```

This can be set by a provider or user if the OpenAI-"compatible" API doesn't support strict tool definitions.

#### openai_supports_sampling_settings

```python
openai_supports_sampling_settings: bool = True
```

Turn off to don't send sampling settings like `temperature` and `top_p` to models that don't support them, like OpenAI's o-series reasoning models.

#### openai_unsupported_model_settings

```python
openai_unsupported_model_settings: Sequence[str] = ()
```

A list of model settings that are not supported by this model.

#### openai_supports_tool_choice_required

```python
openai_supports_tool_choice_required: bool = True
```

Whether the provider accepts the value `tool_choice='required'` in the request payload.

#### openai_system_prompt_role

```python
openai_system_prompt_role: OpenAISystemPromptRole | None = (
    None
)
```

The role to use for the system prompt message. If not provided, defaults to `'system'`.

#### openai_chat_supports_web_search

```python
openai_chat_supports_web_search: bool = False
```

Whether the model supports web search in Chat Completions API.

#### openai_chat_audio_input_encoding

```python
openai_chat_audio_input_encoding: Literal[
    "base64", "uri"
] = "base64"
```

The encoding to use for audio input in Chat Completions requests.

- `'base64'`: Raw base64 encoded string. (Default, used by OpenAI)
- `'uri'`: Data URI (e.g. `data:audio/wav;base64,...`).

#### openai_chat_supports_file_urls

```python
openai_chat_supports_file_urls: bool = False
```

Whether the Chat API supports file URLs directly in the `file_data` field.

OpenAI's native Chat API only supports base64-encoded data, but some providers like OpenRouter support passing URLs directly.

#### openai_supports_encrypted_reasoning_content

```python
openai_supports_encrypted_reasoning_content: bool = False
```

Whether the model supports including encrypted reasoning content in the response.

#### openai_supports_reasoning

```python
openai_supports_reasoning: bool = False
```

Whether the model supports reasoning (o-series, GPT-5+).

When True, sampling parameters may need to be dropped depending on reasoning_effort setting.

#### openai_supports_reasoning_effort_none

```python
openai_supports_reasoning_effort_none: bool = False
```

Whether the model supports sampling parameters (temperature, top_p, etc.) when reasoning_effort='none'.

Models like GPT-5.1 and GPT-5.2 default to reasoning_effort='none' and support sampling params in that mode. When reasoning is enabled (low/medium/high/xhigh), sampling params are not supported.

#### openai_responses_requires_function_call_status_none

```python
openai_responses_requires_function_call_status_none: (
    bool
) = False
```

Whether the Responses API requires the `status` field on function tool calls to be `None`.

This is required by vLLM Responses API versions before https://github.com/vllm-project/vllm/pull/26706. See https://github.com/pydantic/pydantic-ai/issues/3245 for more details.

### openai_model_profile

```python
openai_model_profile(model_name: str) -> ModelProfile
```

Get the model profile for an OpenAI model.

Source code in `pydantic_ai_slim/pydantic_ai/profiles/openai.py`

```python
def openai_model_profile(model_name: str) -> ModelProfile:
    """Get the model profile for an OpenAI model."""
    # GPT-5.1+ models use `reasoning={"effort": "none"}` by default, which allows sampling params.
    is_gpt_5_1_plus = model_name.startswith(('gpt-5.1', 'gpt-5.2'))

    # doesn't support `reasoning={"effort": "none"}` -  default is set at 'medium'
    # see https://platform.openai.com/docs/guides/reasoning
    is_gpt_5 = model_name.startswith('gpt-5') and not is_gpt_5_1_plus

    # always reasoning
    is_o_series = model_name.startswith('o')

    thinking_always_enabled = is_o_series or (is_gpt_5 and 'gpt-5-chat' not in model_name)

    supports_reasoning = thinking_always_enabled or is_gpt_5_1_plus

    # The o1-mini model doesn't support the `system` role, so we default to `user`.
    # See https://github.com/pydantic/pydantic-ai/issues/974 for more details.
    openai_system_prompt_role = 'user' if model_name.startswith('o1-mini') else None

    # Check if the model supports web search (only specific search-preview models)
    supports_web_search = '-search-preview' in model_name
    supports_image_output = (
        is_gpt_5 or is_gpt_5_1_plus or 'o3' in model_name or '4.1' in model_name or '4o' in model_name
    )

    # Structured Outputs (output mode 'native') is only supported with the gpt-4o-mini, gpt-4o-mini-2024-07-18,
    # and gpt-4o-2024-08-06 model snapshots and later. We leave it in here for all models because the
    # `default_structured_output_mode` is `'tool'`, so `native` is only used when the user specifically uses
    # the `NativeOutput` marker, so an error from the API is acceptable.
    return OpenAIModelProfile(
        json_schema_transformer=OpenAIJsonSchemaTransformer,
        supports_json_schema_output=True,
        supports_json_object_output=True,
        supports_image_output=supports_image_output,
        openai_system_prompt_role=openai_system_prompt_role,
        openai_chat_supports_web_search=supports_web_search,
        openai_supports_encrypted_reasoning_content=supports_reasoning,
        openai_supports_reasoning=supports_reasoning,
        openai_supports_reasoning_effort_none=is_gpt_5_1_plus,
    )
```

### OpenAIJsonSchemaTransformer

Bases: `JsonSchemaTransformer`

Recursively handle the schema to make it compatible with OpenAI strict mode.

See https://platform.openai.com/docs/guides/function-calling?api-mode=responses#strict-mode for more details, but this basically just requires: * `additionalProperties` must be set to false for each object in the parameters * all fields in properties must be marked as required

Source code in `pydantic_ai_slim/pydantic_ai/profiles/openai.py`

```python
@dataclass(init=False)
class OpenAIJsonSchemaTransformer(JsonSchemaTransformer):
    """Recursively handle the schema to make it compatible with OpenAI strict mode.

    See https://platform.openai.com/docs/guides/function-calling?api-mode=responses#strict-mode for more details,
    but this basically just requires:
    * `additionalProperties` must be set to false for each object in the parameters
    * all fields in properties must be marked as required
    """

    def __init__(self, schema: JsonSchema, *, strict: bool | None = None):
        super().__init__(schema, strict=strict)
        self.root_ref = schema.get('$ref')

    def walk(self) -> JsonSchema:
        # Note: OpenAI does not support anyOf at the root in strict mode
        # However, we don't need to check for it here because we ensure in pydantic_ai._utils.check_object_json_schema
        # that the root schema either has type 'object' or is recursive.
        result = super().walk()

        # For recursive models, we need to tweak the schema to make it compatible with strict mode.
        # Because the following should never change the semantics of the schema we apply it unconditionally.
        if self.root_ref is not None:
            result.pop('$ref', None)  # We replace references to the self.root_ref with just '#' in the transform method
            root_key = re.sub(r'^#/\$defs/', '', self.root_ref)
            result.update(self.defs.get(root_key) or {})

        return result

    def transform(self, schema: JsonSchema) -> JsonSchema:  # noqa: C901
        # Remove unnecessary keys
        schema.pop('title', None)
        schema.pop('$schema', None)
        schema.pop('discriminator', None)

        default = schema.get('default', _sentinel)
        if default is not _sentinel:
            # the "default" keyword is not allowed in strict mode, but including it makes some Ollama models behave
            # better, so we keep it around when not strict
            if self.strict is True:
                schema.pop('default', None)
            elif self.strict is None:  # pragma: no branch
                self.is_strict_compatible = False

        if schema_ref := schema.get('$ref'):
            if schema_ref == self.root_ref:
                schema['$ref'] = '#'
            if len(schema) > 1:
                # OpenAI Strict mode doesn't support siblings to "$ref", but _does_ allow siblings to "anyOf".
                # So if there is a "description" field or any other extra info, we move the "$ref" into an "anyOf":
                schema['anyOf'] = [{'$ref': schema.pop('$ref')}]

        # Track strict-incompatible keys
        incompatible_values: dict[str, Any] = {}
        for key in _STRICT_INCOMPATIBLE_KEYS:
            value = schema.get(key, _sentinel)
            if value is not _sentinel:
                incompatible_values[key] = value
        if format := schema.get('format'):
            if format not in _STRICT_COMPATIBLE_STRING_FORMATS:
                incompatible_values['format'] = format
        description = schema.get('description')
        if incompatible_values:
            if self.strict is True:
                notes: list[str] = []
                for key, value in incompatible_values.items():
                    schema.pop(key)
                    notes.append(f'{key}={value}')
                notes_string = ', '.join(notes)
                schema['description'] = notes_string if not description else f'{description} ({notes_string})'
            elif self.strict is None:  # pragma: no branch
                self.is_strict_compatible = False

        schema_type = schema.get('type')
        if 'oneOf' in schema:
            # OpenAI does not support oneOf in strict mode
            if self.strict is True:
                schema['anyOf'] = schema.pop('oneOf')
            else:
                self.is_strict_compatible = False

        if schema_type == 'object':
            # Always ensure 'properties' key exists - OpenAI drops objects without it
            if 'properties' not in schema:
                schema['properties'] = dict[str, Any]()

            if self.strict is True:
                # additional properties are disallowed
                schema['additionalProperties'] = False

                # all properties are required
                schema['required'] = list(schema['properties'].keys())

            elif self.strict is None:
                if schema.get('additionalProperties', None) not in (None, False):
                    self.is_strict_compatible = False
                else:
                    # additional properties are disallowed by default
                    schema['additionalProperties'] = False

                if 'properties' not in schema or 'required' not in schema:
                    self.is_strict_compatible = False
                else:
                    required = schema['required']
                    for k in schema['properties'].keys():
                        if k not in required:
                            self.is_strict_compatible = False
        return schema
```

### anthropic_model_profile

```python
anthropic_model_profile(
    model_name: str,
) -> ModelProfile | None
```

Get the model profile for an Anthropic model.

Source code in `pydantic_ai_slim/pydantic_ai/profiles/anthropic.py`

```python
def anthropic_model_profile(model_name: str) -> ModelProfile | None:
    """Get the model profile for an Anthropic model."""
    models_that_support_json_schema_output = (
        'claude-haiku-4-5',
        'claude-sonnet-4-5',
        'claude-opus-4-1',
        'claude-opus-4-5',
        'claude-opus-4-6',
    )
    """These models support both structured outputs and strict tool calling."""
    # TODO update when new models are released that support structured outputs
    # https://docs.claude.com/en/docs/build-with-claude/structured-outputs#example-usage

    supports_json_schema_output = model_name.startswith(models_that_support_json_schema_output)
    return ModelProfile(
        thinking_tags=('<thinking>', '</thinking>'),
        supports_json_schema_output=supports_json_schema_output,
    )
```

### GoogleModelProfile

Bases: `ModelProfile`

Profile for models used with `GoogleModel`.

ALL FIELDS MUST BE `google_` PREFIXED SO YOU CAN MERGE THEM WITH OTHER MODELS.

Source code in `pydantic_ai_slim/pydantic_ai/profiles/google.py`

```python
@dataclass(kw_only=True)
class GoogleModelProfile(ModelProfile):
    """Profile for models used with `GoogleModel`.

    ALL FIELDS MUST BE `google_` PREFIXED SO YOU CAN MERGE THEM WITH OTHER MODELS.
    """

    google_supports_native_output_with_builtin_tools: bool = False
    """Whether the model supports native output with builtin tools.
    See https://ai.google.dev/gemini-api/docs/structured-output?example=recipe#structured_outputs_with_tools"""
```

#### google_supports_native_output_with_builtin_tools

```python
google_supports_native_output_with_builtin_tools: bool = (
    False
)
```

Whether the model supports native output with builtin tools. See https://ai.google.dev/gemini-api/docs/structured-output?example=recipe#structured_outputs_with_tools

### google_model_profile

```python
google_model_profile(
    model_name: str,
) -> ModelProfile | None
```

Get the model profile for a Google model.

Source code in `pydantic_ai_slim/pydantic_ai/profiles/google.py`

```python
def google_model_profile(model_name: str) -> ModelProfile | None:
    """Get the model profile for a Google model."""
    is_image_model = 'image' in model_name
    is_3_or_newer = 'gemini-3' in model_name
    return GoogleModelProfile(
        json_schema_transformer=GoogleJsonSchemaTransformer,
        supports_image_output=is_image_model,
        supports_json_schema_output=is_3_or_newer or not is_image_model,
        supports_json_object_output=is_3_or_newer or not is_image_model,
        supports_tools=not is_image_model,
        google_supports_native_output_with_builtin_tools=is_3_or_newer,
    )
```

### GoogleJsonSchemaTransformer

Bases: `JsonSchemaTransformer`

Transforms the JSON Schema from Pydantic to be suitable for Gemini.

Gemini supports [a subset of OpenAPI v3.0.3](https://ai.google.dev/gemini-api/docs/function-calling#function_declarations).

Source code in `pydantic_ai_slim/pydantic_ai/profiles/google.py`

```python
class GoogleJsonSchemaTransformer(JsonSchemaTransformer):
    """Transforms the JSON Schema from Pydantic to be suitable for Gemini.

    Gemini supports [a subset of OpenAPI v3.0.3](https://ai.google.dev/gemini-api/docs/function-calling#function_declarations).
    """

    def transform(self, schema: JsonSchema) -> JsonSchema:
        # Remove properties not supported by Gemini
        schema.pop('$schema', None)
        if (const := schema.pop('const', None)) is not None:
            # Gemini doesn't support const, but it does support enum with a single value
            schema['enum'] = [const]
            # If type is not present, infer it from the const value for Gemini API compatibility
            if 'type' not in schema:
                if isinstance(const, str):
                    schema['type'] = 'string'
                elif isinstance(const, bool):
                    # bool must be checked before int since bool is a subclass of int in Python
                    schema['type'] = 'boolean'
                elif isinstance(const, int):
                    schema['type'] = 'integer'
                elif isinstance(const, float):
                    schema['type'] = 'number'
        schema.pop('discriminator', None)
        schema.pop('examples', None)

        # Remove 'title' due to https://github.com/googleapis/python-genai/issues/1732
        schema.pop('title', None)

        type_ = schema.get('type')
        if type_ == 'string' and (fmt := schema.pop('format', None)):
            description = schema.get('description')
            if description:
                schema['description'] = f'{description} (format: {fmt})'
            else:
                schema['description'] = f'Format: {fmt}'

        # Note: exclusiveMinimum/exclusiveMaximum are NOT yet supported
        schema.pop('exclusiveMinimum', None)
        schema.pop('exclusiveMaximum', None)

        return schema
```

### meta_model_profile

```python
meta_model_profile(model_name: str) -> ModelProfile | None
```

Get the model profile for a Meta model.

Source code in `pydantic_ai_slim/pydantic_ai/profiles/meta.py`

```python
def meta_model_profile(model_name: str) -> ModelProfile | None:
    """Get the model profile for a Meta model."""
    return ModelProfile(json_schema_transformer=InlineDefsJsonSchemaTransformer)
```

### amazon_model_profile

```python
amazon_model_profile(
    model_name: str,
) -> ModelProfile | None
```

Get the model profile for an Amazon model.

Source code in `pydantic_ai_slim/pydantic_ai/profiles/amazon.py`

```python
def amazon_model_profile(model_name: str) -> ModelProfile | None:
    """Get the model profile for an Amazon model."""
    return ModelProfile(json_schema_transformer=InlineDefsJsonSchemaTransformer)
```

### deepseek_model_profile

```python
deepseek_model_profile(
    model_name: str,
) -> ModelProfile | None
```

Get the model profile for a DeepSeek model.

Source code in `pydantic_ai_slim/pydantic_ai/profiles/deepseek.py`

```python
def deepseek_model_profile(model_name: str) -> ModelProfile | None:
    """Get the model profile for a DeepSeek model."""
    return ModelProfile(ignore_streamed_leading_whitespace='r1' in model_name)
```

### GrokModelProfile

Bases: `ModelProfile`

Profile for Grok models (used with both GrokProvider and XaiProvider).

ALL FIELDS MUST BE `grok_` PREFIXED SO YOU CAN MERGE THEM WITH OTHER MODELS.

Source code in `pydantic_ai_slim/pydantic_ai/profiles/grok.py`

```python
@dataclass(kw_only=True)
class GrokModelProfile(ModelProfile):
    """Profile for Grok models (used with both GrokProvider and XaiProvider).

    ALL FIELDS MUST BE `grok_` PREFIXED SO YOU CAN MERGE THEM WITH OTHER MODELS.
    """

    grok_supports_builtin_tools: bool = False
    """Whether the model supports builtin tools (web_search, code_execution, mcp)."""

    grok_supports_tool_choice_required: bool = True
    """Whether the provider accepts the value ``tool_choice='required'`` in the request payload."""
```

#### grok_supports_builtin_tools

```python
grok_supports_builtin_tools: bool = False
```

Whether the model supports builtin tools (web_search, code_execution, mcp).

#### grok_supports_tool_choice_required

```python
grok_supports_tool_choice_required: bool = True
```

Whether the provider accepts the value `tool_choice='required'` in the request payload.

### grok_model_profile

```python
grok_model_profile(model_name: str) -> ModelProfile | None
```

Get the model profile for a Grok model.

Source code in `pydantic_ai_slim/pydantic_ai/profiles/grok.py`

```python
def grok_model_profile(model_name: str) -> ModelProfile | None:
    """Get the model profile for a Grok model."""
    # Grok-4 models support builtin tools
    grok_supports_builtin_tools = model_name.startswith('grok-4') or 'code' in model_name

    # Set supported builtin tools based on model capability
    supported_builtin_tools: frozenset[type[AbstractBuiltinTool]] = (
        SUPPORTED_BUILTIN_TOOLS if grok_supports_builtin_tools else frozenset()
    )

    return GrokModelProfile(
        # xAI supports tool calling
        supports_tools=True,
        # xAI supports JSON schema output for structured responses
        supports_json_schema_output=True,
        # xAI supports JSON object output
        supports_json_object_output=True,
        # Support for builtin tools (web_search, code_execution, mcp)
        grok_supports_builtin_tools=grok_supports_builtin_tools,
        supported_builtin_tools=supported_builtin_tools,
    )
```

### mistral_model_profile

```python
mistral_model_profile(
    model_name: str,
) -> ModelProfile | None
```

Get the model profile for a Mistral model.

Source code in `pydantic_ai_slim/pydantic_ai/profiles/mistral.py`

```python
def mistral_model_profile(model_name: str) -> ModelProfile | None:
    """Get the model profile for a Mistral model."""
    return None
```

### qwen_model_profile

```python
qwen_model_profile(model_name: str) -> ModelProfile | None
```

Get the model profile for a Qwen model.

Source code in `pydantic_ai_slim/pydantic_ai/profiles/qwen.py`

```python
def qwen_model_profile(model_name: str) -> ModelProfile | None:
    """Get the model profile for a Qwen model."""
    if model_name.startswith('qwen-3-coder'):
        return OpenAIModelProfile(
            json_schema_transformer=InlineDefsJsonSchemaTransformer,
            openai_supports_tool_choice_required=False,
            openai_supports_strict_tool_definition=False,
            ignore_streamed_leading_whitespace=True,
        )
    return ModelProfile(
        json_schema_transformer=InlineDefsJsonSchemaTransformer,
        ignore_streamed_leading_whitespace=True,
    )
```
