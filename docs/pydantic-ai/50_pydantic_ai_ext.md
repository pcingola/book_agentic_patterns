# `pydantic_ai.ext`

### tool_from_langchain

```python
tool_from_langchain(langchain_tool: LangChainTool) -> Tool
```

Creates a Pydantic AI tool proxy from a LangChain tool.

Parameters:

| Name             | Type            | Description                 | Default    |
| ---------------- | --------------- | --------------------------- | ---------- |
| `langchain_tool` | `LangChainTool` | The LangChain tool to wrap. | *required* |

Returns:

| Type   | Description                                                |
| ------ | ---------------------------------------------------------- |
| `Tool` | A Pydantic AI tool that corresponds to the LangChain tool. |

Source code in `pydantic_ai_slim/pydantic_ai/ext/langchain.py`

```python
def tool_from_langchain(langchain_tool: LangChainTool) -> Tool:
    """Creates a Pydantic AI tool proxy from a LangChain tool.

    Args:
        langchain_tool: The LangChain tool to wrap.

    Returns:
        A Pydantic AI tool that corresponds to the LangChain tool.
    """
    function_name = langchain_tool.name
    function_description = langchain_tool.description
    inputs = langchain_tool.args.copy()
    required = sorted({name for name, detail in inputs.items() if 'default' not in detail})
    schema: JsonSchemaValue = langchain_tool.get_input_jsonschema()
    if 'additionalProperties' not in schema:
        schema['additionalProperties'] = False
    if required:
        schema['required'] = required

    defaults = {name: detail['default'] for name, detail in inputs.items() if 'default' in detail}

    # restructures the arguments to match langchain tool run
    def proxy(*args: Any, **kwargs: Any) -> str:
        assert not args, 'This should always be called with kwargs'
        kwargs = defaults | kwargs
        return langchain_tool.run(kwargs)

    return Tool.from_schema(
        function=proxy,
        name=function_name,
        description=function_description,
        json_schema=schema,
    )
```

### LangChainToolset

Bases: `FunctionToolset`

A toolset that wraps LangChain tools.

Source code in `pydantic_ai_slim/pydantic_ai/ext/langchain.py`

```python
class LangChainToolset(FunctionToolset):
    """A toolset that wraps LangChain tools."""

    def __init__(self, tools: list[LangChainTool], *, id: str | None = None):
        super().__init__([tool_from_langchain(tool) for tool in tools], id=id)
```

### tool_from_aci

```python
tool_from_aci(
    aci_function: str, linked_account_owner_id: str
) -> Tool
```

Creates a Pydantic AI tool proxy from an ACI.dev function.

Parameters:

| Name                      | Type  | Description                                           | Default    |
| ------------------------- | ----- | ----------------------------------------------------- | ---------- |
| `aci_function`            | `str` | The ACI.dev function to wrap.                         | *required* |
| `linked_account_owner_id` | `str` | The ACI user ID to execute the function on behalf of. | *required* |

Returns:

| Type   | Description                                              |
| ------ | -------------------------------------------------------- |
| `Tool` | A Pydantic AI tool that corresponds to the ACI.dev tool. |

Source code in `pydantic_ai_slim/pydantic_ai/ext/aci.py`

```python
def tool_from_aci(aci_function: str, linked_account_owner_id: str) -> Tool:
    """Creates a Pydantic AI tool proxy from an ACI.dev function.

    Args:
        aci_function: The ACI.dev function to wrap.
        linked_account_owner_id: The ACI user ID to execute the function on behalf of.

    Returns:
        A Pydantic AI tool that corresponds to the ACI.dev tool.
    """
    aci = ACI()
    function_definition = aci.functions.get_definition(aci_function)
    function_name = function_definition['function']['name']
    function_description = function_definition['function']['description']
    inputs = function_definition['function']['parameters']

    json_schema = {
        'additionalProperties': inputs.get('additionalProperties', False),
        'properties': inputs.get('properties', {}),
        'required': inputs.get('required', []),
        # Default to 'object' if not specified
        'type': inputs.get('type', 'object'),
    }

    # Clean the schema
    json_schema = _clean_schema(json_schema)

    def implementation(*args: Any, **kwargs: Any) -> str:
        if args:
            raise TypeError('Positional arguments are not allowed')
        return aci.handle_function_call(
            function_name,
            kwargs,
            linked_account_owner_id=linked_account_owner_id,
            allowed_apps_only=True,
        )

    return Tool.from_schema(
        function=implementation,
        name=function_name,
        description=function_description,
        json_schema=json_schema,
    )
```

### ACIToolset

Bases: `FunctionToolset`

A toolset that wraps ACI.dev tools.

Source code in `pydantic_ai_slim/pydantic_ai/ext/aci.py`

```python
class ACIToolset(FunctionToolset):
    """A toolset that wraps ACI.dev tools."""

    def __init__(self, aci_functions: Sequence[str], linked_account_owner_id: str, *, id: str | None = None):
        super().__init__(
            [tool_from_aci(aci_function, linked_account_owner_id) for aci_function in aci_functions], id=id
        )
```
