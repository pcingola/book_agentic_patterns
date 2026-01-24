## Hands-On: MCP Features

The previous hands-on sections covered the raw MCP protocol and how agents use MCP tools. This hands-on explores the broader set of MCP server features through `example_mcp_features.ipynb`: tools, resources, and prompts. These features structure how context and capabilities are exposed to clients.

## The MCP Server

The server in `example_mcp_server_v2.py` demonstrates all three feature types:

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Demo")

@mcp.tool()
def add(a: int, b: int) -> int:
    """ Add two numbers """
    return a + b

@mcp.resource("postgres://{database}/{table_name}/schema")
def table_schema(database: str, table_name: str) -> str:
    """Get a table's schema"""
    return f"""
        -- This is the schema for the {table_name} table
        -- in the {database} database
        CREATE TABLE {table_name} (id INT, name VARCHAR(255));
        """

@mcp.prompt()
def hello_prompt(name: str) -> str:
    """Get a personalized greeting"""
    return f"Your name is {name} and you are a helpful assistant."
```

Each decorator registers a different type of capability. The `@mcp.tool()` decorator exposes a callable function. The `@mcp.resource()` decorator exposes data at a URI pattern. The `@mcp.prompt()` decorator exposes an instruction template.

## The FastMCP Client

The notebook uses the FastMCP `Client` class, which provides a programmatic interface for interacting with MCP servers. Unlike the agent integrations shown earlier, this client requires explicit calls and gives direct control over all MCP operations.

```python
from fastmcp import Client

client = Client("http://127.0.0.1:8000/mcp")
```

The client connects via HTTP to a running server. All operations happen within an async context manager that handles connection lifecycle:

```python
async with client:
    # MCP operations here
```

## Tools

Tools are the most familiar MCP feature. They expose callable functions that clients can discover and invoke.

Discovery returns metadata about each tool:

```python
async with client:
    tools = await client.list_tools()
    for tool in tools:
        print(f"Tool: {tool.name}")
        print(f"  Description: {tool.description}")
        print(f"  Schema: {tool.inputSchema}")
```

The schema describes the expected arguments using JSON Schema. Agent frameworks use this schema to present tools to language models, which decide when and how to call them.

Invocation passes arguments and returns the result:

```python
async with client:
    result = await client.call_tool("add", {"a": 40, "b": 2})
```

The server validates arguments against the schema before execution.

## Resources

Resources expose data through URI-addressable endpoints. Unlike tools, which perform actions, resources provide read access to information.

The server defines a resource template with parameters in the URI pattern:

```python
@mcp.resource("postgres://{database}/{table_name}/schema")
def table_schema(database: str, table_name: str) -> str:
    ...
```

The `{database}` and `{table_name}` placeholders become parameters. Clients discover these templates:

```python
async with client:
    templates = await client.list_resource_templates()
    for template in templates:
        print(f"Template: {template.uriTemplate}")
```

Reading a resource requires filling in the template parameters:

```python
async with client:
    content = await client.read_resource("postgres://mydb/users/schema")
```

The URI `postgres://mydb/users/schema` matches the template with `database=mydb` and `table_name=users`. The server executes the function with these values and returns the content.

Resources enable workspace-style workflows where artifacts are produced, stored, and retrieved across multiple interactions. They avoid copying large documents into every prompt by making data addressable and fetchable on demand.

## Prompts

Prompts are server-defined instruction templates. They centralize behavioral contracts on the server side, allowing prompt engineering to evolve independently of client code.

The server defines a prompt with parameters:

```python
@mcp.prompt()
def hello_prompt(name: str) -> str:
    """Get a personalized greeting"""
    return f"Your name is {name} and you are a helpful assistant."
```

Clients discover available prompts:

```python
async with client:
    prompts = await client.list_prompts()
    for prompt in prompts:
        print(f"Prompt: {prompt.name}")
        print(f"  Arguments: {prompt.arguments}")
```

Retrieving a prompt renders it with the provided arguments:

```python
async with client:
    result = await client.get_prompt("hello_prompt", {"name": "Alice"})
    for msg in result.messages:
        print(f"Content: {msg.content.text}")
```

The result contains messages ready to be used in a conversation. The client never embeds the instruction text directly; it requests the prompt by name and receives the rendered version. This separation means prompt changes can be deployed server-side without modifying clients.

## How These Features Complement Each Other

Tools, resources, and prompts serve different purposes in an MCP architecture:

**Tools** perform actions. They execute logic, call APIs, modify state, or compute results. An agent decides when to call them based on the task.

**Resources** provide data. They expose documents, configurations, or generated artifacts without requiring the client to know how to fetch or generate them.

**Prompts** define behavior. They encapsulate instructions, constraints, and framing that shape how an agent approaches a task.

A typical workflow might retrieve a resource containing relevant data, use a prompt to frame the analysis task, and invoke tools to perform specific operations. Each feature type has a clear role, and the MCP protocol makes them all discoverable and addressable through a uniform interface.

## Key Takeaways

MCP servers can expose three types of capabilities: tools for actions, resources for data, and prompts for instructions.

The FastMCP `Client` provides programmatic access to all three. It handles connection management and exposes async methods for discovery and usage.

Resources use URI templates with parameters, enabling addressable data endpoints that support workspace-style workflows.

Prompts centralize instruction management on the server, separating behavioral definitions from client logic.
