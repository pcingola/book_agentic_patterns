# Hands-On: Structured Outputs

Structured output is the pattern of constraining a model's response to conform to a predefined schema rather than allowing free-form text. This transforms the model from a text generator into a data producer, enabling direct integration with typed code and automated validation.

This hands-on explores structured output through `example_structured_outputs.ipynb`, demonstrating how to define schemas and receive typed Python objects from the model.

## The Problem with Free-Form Text

When a model returns plain text, your code must parse that text to extract useful information. Consider asking a model about programming languages. A free-form response might look like:

```
Python is a dynamically typed language that supports multiple paradigms including
object-oriented and functional programming. JavaScript is also dynamically typed
and is primarily used for web development...
```

Extracting structured data from this response requires parsing natural language, which is error-prone and brittle. The model might phrase things differently each time, use unexpected formatting, or include information you didn't ask for.

Structured output eliminates this problem by making the model return data in a predefined format that your code can consume directly.

## Defining a Schema

In `example_structured_outputs.ipynb`, we define a schema using Pydantic:

```python
class ProgrammingLanguage(BaseModel):
    name: str
    paradigm: str = Field(description="Primary paradigm: functional, object-oriented, procedural, etc.")
    typed: bool = Field(description="Whether the language is statically typed")
```

This schema specifies exactly what data we want. Each field has a type (`str`, `bool`) and optional descriptions that help the model understand what values to provide. The model cannot return anything that doesn't fit this structure.

The `Field` descriptions serve as documentation for the model. When the schema is sent to the API, these descriptions become part of the JSON schema that guides the model's output. Clear descriptions improve the quality and consistency of the returned data.

## Configuring the Agent

The agent is configured with an `output_type` parameter:

```python
agent = get_agent(output_type=list[ProgrammingLanguage])
```

This tells the framework that the model must return a list of `ProgrammingLanguage` objects. The framework converts the Pydantic model into a JSON schema and includes it in the API request. The model's response is then validated against this schema and converted back into Python objects.

Using `list[ProgrammingLanguage]` rather than a single object demonstrates that structured output works with complex types. You can use lists, nested objects, optional fields, and other type constructs that Pydantic supports.

## Running the Agent

When we run the agent with a prompt:

```python
prompt = "List 3 popular programming languages with their characteristics."
agent_run, nodes = await run_agent(agent, prompt, verbose=True)
```

The model receives both the prompt and the schema. It must produce output that validates against the schema. If it tries to return malformed data, the framework will catch the error.

## Working with the Result

The result is not a string but a typed Python object:

```python
result = agent_run.result.output
print(f"Type: {type(result)}")  # <class 'list'>

for lang in result:
    print(f"{lang.name}: {lang.paradigm}, typed={lang.typed}")
```

Each element in the list is a `ProgrammingLanguage` instance with properly typed attributes. You can access `lang.name`, `lang.paradigm`, and `lang.typed` directly without any parsing. Your IDE provides autocomplete, and type checkers can verify your code.

This is the key benefit: the boundary between the model's probabilistic output and your deterministic code becomes a well-defined contract. The model produces data, the schema validates it, and your code receives typed objects.

## When to Use Structured Output

Structured output is appropriate when you need to process the model's response programmatically. This includes extracting entities from text, generating configuration data, producing API responses, or any situation where the output feeds into downstream code rather than being displayed directly to users.

Structured output is less appropriate when you want the model to explain, discuss, or generate content for human consumption. In those cases, free-form text is the natural choice.

## Key Takeaways

Structured output constrains the model to return data matching a predefined schema. This eliminates the need to parse free-form text and ensures type safety at the boundary between model and code.

Schemas are defined using Pydantic models. Field descriptions help the model understand what values to produce and improve output quality.

The result is a typed Python object, not a string. You can work with it directly using normal attribute access, with full IDE support and type checking.

Structured output transforms the model from a text generator into a data producer, enabling reliable integration with typed codebases.
