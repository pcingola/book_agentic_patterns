# Getting Prompts
Source: https://gofastmcp.com/clients/prompts

Retrieve rendered message templates with automatic argument serialization.

<VersionBadge />

Use this when you need to retrieve server-defined message templates for LLM interactions.

Prompts are reusable message templates exposed by MCP servers. They can accept arguments to generate personalized message sequences for LLM interactions.

## Basic Usage

Request a rendered prompt with `get_prompt()`:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
async with client:
    # Simple prompt without arguments
    result = await client.get_prompt("welcome_message")
    # result -> mcp.types.GetPromptResult

    # Access the generated messages
    for message in result.messages:
        print(f"Role: {message.role}")
        print(f"Content: {message.content}")
```

Pass arguments to customize the prompt:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
async with client:
    result = await client.get_prompt("user_greeting", {
        "name": "Alice",
        "role": "administrator"
    })

    for message in result.messages:
        print(f"Generated message: {message.content}")
```

## Argument Serialization

<VersionBadge />

FastMCP automatically serializes complex arguments to JSON strings as required by the MCP specification. You can pass typed objects directly:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from dataclasses import dataclass

@dataclass
class UserData:
    name: str
    age: int

async with client:
    result = await client.get_prompt("analyze_user", {
        "user": UserData(name="Alice", age=30),     # Automatically serialized
        "preferences": {"theme": "dark"},           # Dict serialized
        "scores": [85, 92, 78],                     # List serialized
        "simple_name": "Bob"                        # Strings unchanged
    })
```

The client handles serialization using `pydantic_core.to_json()` for consistent formatting. FastMCP servers automatically deserialize these JSON strings back to the expected types.

## Working with Results

The `get_prompt()` method returns a `GetPromptResult` containing a list of messages:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
async with client:
    result = await client.get_prompt("conversation_starter", {"topic": "climate"})

    for i, message in enumerate(result.messages):
        print(f"Message {i + 1}:")
        print(f"  Role: {message.role}")
        print(f"  Content: {message.content.text if hasattr(message.content, 'text') else message.content}")
```

Prompts can generate different message types. System messages configure LLM behavior:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
async with client:
    result = await client.get_prompt("system_configuration", {
        "role": "helpful assistant",
        "expertise": "python programming"
    })

    # Typically returns messages with role="system"
    system_message = result.messages[0]
    print(f"System prompt: {system_message.content}")
```

Conversation templates generate multi-turn flows:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
async with client:
    result = await client.get_prompt("interview_template", {
        "candidate_name": "Alice",
        "position": "Senior Developer"
    })

    # Multiple messages for a conversation flow
    for message in result.messages:
        print(f"{message.role}: {message.content}")
```

## Version Selection

<VersionBadge />

When a server exposes multiple versions of a prompt, you can request a specific version:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
async with client:
    # Get the highest version (default)
    result = await client.get_prompt("summarize", {"text": "..."})

    # Get a specific version
    result_v1 = await client.get_prompt("summarize", {"text": "..."}, version="1.0")
```

See [Metadata](/servers/versioning#version-discovery) for how to discover available versions.

## Multi-Server Clients

When using multi-server clients, prompts are accessible directly without prefixing:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
async with client:  # Multi-server client
    result1 = await client.get_prompt("weather_prompt", {"city": "London"})
    result2 = await client.get_prompt("assistant_prompt", {"query": "help"})
```

## Raw Protocol Access

For complete control, use `get_prompt_mcp()` which returns the full MCP protocol object:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
async with client:
    result = await client.get_prompt_mcp("example_prompt", {"arg": "value"})
    # result -> mcp.types.GetPromptResult
```
