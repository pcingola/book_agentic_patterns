# `pydantic_ai.output`

### OutputDataT

```python
OutputDataT = TypeVar(
    "OutputDataT", default=str, covariant=True
)
```

Covariant type variable for the output data type of a run.

### ToolOutput

Bases: `Generic[OutputDataT]`

Marker class to use a tool for output and optionally customize the tool.

Example:

tool_output.py

```python
from pydantic import BaseModel

from pydantic_ai import Agent, ToolOutput


class Fruit(BaseModel):
    name: str
    color: str


class Vehicle(BaseModel):
    name: str
    wheels: int


agent = Agent(
    'openai:gpt-5.2',
    output_type=[
        ToolOutput(Fruit, name='return_fruit'),
        ToolOutput(Vehicle, name='return_vehicle'),
    ],
)
result = agent.run_sync('What is a banana?')
print(repr(result.output))
#> Fruit(name='banana', color='yellow')
```

Source code in `pydantic_ai_slim/pydantic_ai/output.py`

````python
@dataclass(init=False)
class ToolOutput(Generic[OutputDataT]):
    """Marker class to use a tool for output and optionally customize the tool.

    Example:
    ```python {title="tool_output.py"}
    from pydantic import BaseModel

    from pydantic_ai import Agent, ToolOutput


    class Fruit(BaseModel):
        name: str
        color: str


    class Vehicle(BaseModel):
        name: str
        wheels: int


    agent = Agent(
        'openai:gpt-5.2',
        output_type=[
            ToolOutput(Fruit, name='return_fruit'),
            ToolOutput(Vehicle, name='return_vehicle'),
        ],
    )
    result = agent.run_sync('What is a banana?')
    print(repr(result.output))
    #> Fruit(name='banana', color='yellow')
    ```
    """

    output: OutputTypeOrFunction[OutputDataT]
    """An output type or function."""
    name: str | None
    """The name of the tool that will be passed to the model. If not specified and only one output is provided, `final_result` will be used. If multiple outputs are provided, the name of the output type or function will be added to the tool name."""
    description: str | None
    """The description of the tool that will be passed to the model. If not specified, the docstring of the output type or function will be used."""
    max_retries: int | None
    """The maximum number of retries for the tool."""
    strict: bool | None
    """Whether to use strict mode for the tool."""

    def __init__(
        self,
        type_: OutputTypeOrFunction[OutputDataT],
        *,
        name: str | None = None,
        description: str | None = None,
        max_retries: int | None = None,
        strict: bool | None = None,
    ):
        self.output = type_
        self.name = name
        self.description = description
        self.max_retries = max_retries
        self.strict = strict
````

#### output

```python
output: OutputTypeOrFunction[OutputDataT] = type_
```

An output type or function.

#### name

```python
name: str | None = name
```

The name of the tool that will be passed to the model. If not specified and only one output is provided, `final_result` will be used. If multiple outputs are provided, the name of the output type or function will be added to the tool name.

#### description

```python
description: str | None = description
```

The description of the tool that will be passed to the model. If not specified, the docstring of the output type or function will be used.

#### max_retries

```python
max_retries: int | None = max_retries
```

The maximum number of retries for the tool.

#### strict

```python
strict: bool | None = strict
```

Whether to use strict mode for the tool.

### NativeOutput

Bases: `Generic[OutputDataT]`

Marker class to use the model's native structured outputs functionality for outputs and optionally customize the name and description.

Example:

native_output.py

```python
from pydantic_ai import Agent, NativeOutput

from tool_output import Fruit, Vehicle

agent = Agent(
    'openai:gpt-5.2',
    output_type=NativeOutput(
        [Fruit, Vehicle],
        name='Fruit or vehicle',
        description='Return a fruit or vehicle.'
    ),
)
result = agent.run_sync('What is a Ford Explorer?')
print(repr(result.output))
#> Vehicle(name='Ford Explorer', wheels=4)
```

Source code in `pydantic_ai_slim/pydantic_ai/output.py`

````python
@dataclass(init=False)
class NativeOutput(Generic[OutputDataT]):
    """Marker class to use the model's native structured outputs functionality for outputs and optionally customize the name and description.

    Example:
    ```python {title="native_output.py" requires="tool_output.py"}
    from pydantic_ai import Agent, NativeOutput

    from tool_output import Fruit, Vehicle

    agent = Agent(
        'openai:gpt-5.2',
        output_type=NativeOutput(
            [Fruit, Vehicle],
            name='Fruit or vehicle',
            description='Return a fruit or vehicle.'
        ),
    )
    result = agent.run_sync('What is a Ford Explorer?')
    print(repr(result.output))
    #> Vehicle(name='Ford Explorer', wheels=4)
    ```
    """

    outputs: OutputTypeOrFunction[OutputDataT] | Sequence[OutputTypeOrFunction[OutputDataT]]
    """The output types or functions."""
    name: str | None
    """The name of the structured output that will be passed to the model. If not specified and only one output is provided, the name of the output type or function will be used."""
    description: str | None
    """The description of the structured output that will be passed to the model. If not specified and only one output is provided, the docstring of the output type or function will be used."""
    strict: bool | None
    """Whether to use strict mode for the output, if the model supports it."""
    template: str | None
    """Template for the prompt passed to the model.
    The '{schema}' placeholder will be replaced with the output JSON schema.
    If no template is specified but the model's profile indicates that it requires the schema to be sent as a prompt, the default template specified on the profile will be used.
    """

    def __init__(
        self,
        outputs: OutputTypeOrFunction[OutputDataT] | Sequence[OutputTypeOrFunction[OutputDataT]],
        *,
        name: str | None = None,
        description: str | None = None,
        strict: bool | None = None,
        template: str | None = None,
    ):
        self.outputs = outputs
        self.name = name
        self.description = description
        self.strict = strict
        self.template = template
````

#### outputs

```python
outputs: (
    OutputTypeOrFunction[OutputDataT]
    | Sequence[OutputTypeOrFunction[OutputDataT]]
) = outputs
```

The output types or functions.

#### name

```python
name: str | None = name
```

The name of the structured output that will be passed to the model. If not specified and only one output is provided, the name of the output type or function will be used.

#### description

```python
description: str | None = description
```

The description of the structured output that will be passed to the model. If not specified and only one output is provided, the docstring of the output type or function will be used.

#### strict

```python
strict: bool | None = strict
```

Whether to use strict mode for the output, if the model supports it.

#### template

```python
template: str | None = template
```

Template for the prompt passed to the model. The '{schema}' placeholder will be replaced with the output JSON schema. If no template is specified but the model's profile indicates that it requires the schema to be sent as a prompt, the default template specified on the profile will be used.

### PromptedOutput

Bases: `Generic[OutputDataT]`

Marker class to use a prompt to tell the model what to output and optionally customize the prompt.

Example:

prompted_output.py

```python
from pydantic import BaseModel

from pydantic_ai import Agent, PromptedOutput

from tool_output import Vehicle


class Device(BaseModel):
    name: str
    kind: str


agent = Agent(
    'openai:gpt-5.2',
    output_type=PromptedOutput(
        [Vehicle, Device],
        name='Vehicle or device',
        description='Return a vehicle or device.'
    ),
)
result = agent.run_sync('What is a MacBook?')
print(repr(result.output))
#> Device(name='MacBook', kind='laptop')

agent = Agent(
    'openai:gpt-5.2',
    output_type=PromptedOutput(
        [Vehicle, Device],
        template='Gimme some JSON: {schema}'
    ),
)
result = agent.run_sync('What is a Ford Explorer?')
print(repr(result.output))
#> Vehicle(name='Ford Explorer', wheels=4)
```

Source code in `pydantic_ai_slim/pydantic_ai/output.py`

````python
@dataclass(init=False)
class PromptedOutput(Generic[OutputDataT]):
    """Marker class to use a prompt to tell the model what to output and optionally customize the prompt.

    Example:
    ```python {title="prompted_output.py" requires="tool_output.py"}
    from pydantic import BaseModel

    from pydantic_ai import Agent, PromptedOutput

    from tool_output import Vehicle


    class Device(BaseModel):
        name: str
        kind: str


    agent = Agent(
        'openai:gpt-5.2',
        output_type=PromptedOutput(
            [Vehicle, Device],
            name='Vehicle or device',
            description='Return a vehicle or device.'
        ),
    )
    result = agent.run_sync('What is a MacBook?')
    print(repr(result.output))
    #> Device(name='MacBook', kind='laptop')

    agent = Agent(
        'openai:gpt-5.2',
        output_type=PromptedOutput(
            [Vehicle, Device],
            template='Gimme some JSON: {schema}'
        ),
    )
    result = agent.run_sync('What is a Ford Explorer?')
    print(repr(result.output))
    #> Vehicle(name='Ford Explorer', wheels=4)
    ```
    """

    outputs: OutputTypeOrFunction[OutputDataT] | Sequence[OutputTypeOrFunction[OutputDataT]]
    """The output types or functions."""
    name: str | None
    """The name of the structured output that will be passed to the model. If not specified and only one output is provided, the name of the output type or function will be used."""
    description: str | None
    """The description that will be passed to the model. If not specified and only one output is provided, the docstring of the output type or function will be used."""
    template: str | None
    """Template for the prompt passed to the model.
    The '{schema}' placeholder will be replaced with the output JSON schema.
    If not specified, the default template specified on the model's profile will be used.
    """

    def __init__(
        self,
        outputs: OutputTypeOrFunction[OutputDataT] | Sequence[OutputTypeOrFunction[OutputDataT]],
        *,
        name: str | None = None,
        description: str | None = None,
        template: str | None = None,
    ):
        self.outputs = outputs
        self.name = name
        self.description = description
        self.template = template
````

#### outputs

```python
outputs: (
    OutputTypeOrFunction[OutputDataT]
    | Sequence[OutputTypeOrFunction[OutputDataT]]
) = outputs
```

The output types or functions.

#### name

```python
name: str | None = name
```

The name of the structured output that will be passed to the model. If not specified and only one output is provided, the name of the output type or function will be used.

#### description

```python
description: str | None = description
```

The description that will be passed to the model. If not specified and only one output is provided, the docstring of the output type or function will be used.

#### template

```python
template: str | None = template
```

Template for the prompt passed to the model. The '{schema}' placeholder will be replaced with the output JSON schema. If not specified, the default template specified on the model's profile will be used.

### TextOutput

Bases: `Generic[OutputDataT]`

Marker class to use text output for an output function taking a string argument.

Example:

```python
from pydantic_ai import Agent, TextOutput


def split_into_words(text: str) -> list[str]:
    return text.split()


agent = Agent(
    'openai:gpt-5.2',
    output_type=TextOutput(split_into_words),
)
result = agent.run_sync('Who was Albert Einstein?')
print(result.output)
#> ['Albert', 'Einstein', 'was', 'a', 'German-born', 'theoretical', 'physicist.']
```

Source code in `pydantic_ai_slim/pydantic_ai/output.py`

````python
@dataclass
class TextOutput(Generic[OutputDataT]):
    """Marker class to use text output for an output function taking a string argument.

    Example:
    ```python
    from pydantic_ai import Agent, TextOutput


    def split_into_words(text: str) -> list[str]:
        return text.split()


    agent = Agent(
        'openai:gpt-5.2',
        output_type=TextOutput(split_into_words),
    )
    result = agent.run_sync('Who was Albert Einstein?')
    print(result.output)
    #> ['Albert', 'Einstein', 'was', 'a', 'German-born', 'theoretical', 'physicist.']
    ```
    """

    output_function: TextOutputFunc[OutputDataT]
    """The function that will be called to process the model's plain text output. The function must take a single string argument."""
````

#### output_function

```python
output_function: TextOutputFunc[OutputDataT]
```

The function that will be called to process the model's plain text output. The function must take a single string argument.

### StructuredDict

```python
StructuredDict(
    json_schema: JsonSchemaValue,
    name: str | None = None,
    description: str | None = None,
) -> type[JsonSchemaValue]
```

Returns a `dict[str, Any]` subclass with a JSON schema attached that will be used for structured output.

Parameters:

| Name          | Type              | Description                                                                    | Default                                                                                                                                |
| ------------- | ----------------- | ------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------- |
| `json_schema` | `JsonSchemaValue` | A JSON schema of type object defining the structure of the dictionary content. | *required*                                                                                                                             |
| `name`        | \`str             | None\`                                                                         | Optional name of the structured output. If not provided, the title field of the JSON schema will be used if it's present.              |
| `description` | \`str             | None\`                                                                         | Optional description of the structured output. If not provided, the description field of the JSON schema will be used if it's present. |

Example:

structured_dict.py

```python
from pydantic_ai import Agent, StructuredDict

schema = {
    'type': 'object',
    'properties': {
        'name': {'type': 'string'},
        'age': {'type': 'integer'}
    },
    'required': ['name', 'age']
}

agent = Agent('openai:gpt-5.2', output_type=StructuredDict(schema))
result = agent.run_sync('Create a person')
print(result.output)
#> {'name': 'John Doe', 'age': 30}
```

Source code in `pydantic_ai_slim/pydantic_ai/output.py`

````python
def StructuredDict(
    json_schema: JsonSchemaValue, name: str | None = None, description: str | None = None
) -> type[JsonSchemaValue]:
    """Returns a `dict[str, Any]` subclass with a JSON schema attached that will be used for structured output.

    Args:
        json_schema: A JSON schema of type `object` defining the structure of the dictionary content.
        name: Optional name of the structured output. If not provided, the `title` field of the JSON schema will be used if it's present.
        description: Optional description of the structured output. If not provided, the `description` field of the JSON schema will be used if it's present.

    Example:
    ```python {title="structured_dict.py"}
    from pydantic_ai import Agent, StructuredDict

    schema = {
        'type': 'object',
        'properties': {
            'name': {'type': 'string'},
            'age': {'type': 'integer'}
        },
        'required': ['name', 'age']
    }

    agent = Agent('openai:gpt-5.2', output_type=StructuredDict(schema))
    result = agent.run_sync('Create a person')
    print(result.output)
    #> {'name': 'John Doe', 'age': 30}
    ```
    """
    json_schema = _utils.check_object_json_schema(json_schema)

    # Pydantic `TypeAdapter` fails when `object.__get_pydantic_json_schema__` has `$defs`, so we inline them
    # See https://github.com/pydantic/pydantic/issues/12145
    if '$defs' in json_schema:
        json_schema = InlineDefsJsonSchemaTransformer(json_schema).walk()
        if '$defs' in json_schema:
            raise exceptions.UserError(
                '`StructuredDict` does not currently support recursive `$ref`s and `$defs`. See https://github.com/pydantic/pydantic/issues/12145 for more information.'
            )

    if name:
        json_schema['title'] = name

    if description:
        json_schema['description'] = description

    class _StructuredDict(JsonSchemaValue):
        __is_model_like__ = True

        @classmethod
        def __get_pydantic_core_schema__(
            cls, source_type: Any, handler: GetCoreSchemaHandler
        ) -> core_schema.CoreSchema:
            return core_schema.dict_schema(
                keys_schema=core_schema.str_schema(),
                values_schema=core_schema.any_schema(),
            )

        @classmethod
        def __get_pydantic_json_schema__(
            cls, core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
        ) -> JsonSchemaValue:
            return json_schema

    return _StructuredDict
````

### DeferredToolRequests

Tool calls that require approval or external execution.

This can be used as an agent's `output_type` and will be used as the output of the agent run if the model called any deferred tools.

Results can be passed to the next agent run using a DeferredToolResults object with the same tool call IDs.

See [deferred tools docs](https://ai.pydantic.dev/deferred-tools/#deferred-tools) for more information.

Source code in `pydantic_ai_slim/pydantic_ai/tools.py`

```python
@dataclass(kw_only=True)
class DeferredToolRequests:
    """Tool calls that require approval or external execution.

    This can be used as an agent's `output_type` and will be used as the output of the agent run if the model called any deferred tools.

    Results can be passed to the next agent run using a [`DeferredToolResults`][pydantic_ai.tools.DeferredToolResults] object with the same tool call IDs.

    See [deferred tools docs](../deferred-tools.md#deferred-tools) for more information.
    """

    calls: list[ToolCallPart] = field(default_factory=list[ToolCallPart])
    """Tool calls that require external execution."""
    approvals: list[ToolCallPart] = field(default_factory=list[ToolCallPart])
    """Tool calls that require human-in-the-loop approval."""
    metadata: dict[str, dict[str, Any]] = field(default_factory=dict[str, dict[str, Any]])
    """Metadata for deferred tool calls, keyed by `tool_call_id`."""
```

#### calls

```python
calls: list[ToolCallPart] = field(
    default_factory=list[ToolCallPart]
)
```

Tool calls that require external execution.

#### approvals

```python
approvals: list[ToolCallPart] = field(
    default_factory=list[ToolCallPart]
)
```

Tool calls that require human-in-the-loop approval.

#### metadata

```python
metadata: dict[str, dict[str, Any]] = field(
    default_factory=dict[str, dict[str, Any]]
)
```

Metadata for deferred tool calls, keyed by `tool_call_id`.
