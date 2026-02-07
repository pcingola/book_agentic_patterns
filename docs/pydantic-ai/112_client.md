# Client

Pydantic AI can act as an [MCP client](https://modelcontextprotocol.io/quickstart/client), connecting to MCP servers to use their tools.

## Install

You need to either install [`pydantic-ai`](https://ai.pydantic.dev/install/index.md), or [`pydantic-ai-slim`](https://ai.pydantic.dev/install/#slim-install) with the `mcp` optional group:

```bash
pip install "pydantic-ai-slim[mcp]"
```

```bash
uv add "pydantic-ai-slim[mcp]"
```

## Usage

Pydantic AI comes with three ways to connect to MCP servers:

- MCPServerStreamableHTTP which connects to an MCP server using the [Streamable HTTP](https://modelcontextprotocol.io/introduction#streamable-http) transport
- MCPServerSSE which connects to an MCP server using the [HTTP SSE](https://spec.modelcontextprotocol.io/specification/2024-11-05/basic/transports/#http-with-sse) transport
- MCPServerStdio which runs the server as a subprocess and connects to it using the [stdio](https://spec.modelcontextprotocol.io/specification/2024-11-05/basic/transports/#stdio) transport

Examples of all three are shown below.

Each MCP server instance is a [toolset](https://ai.pydantic.dev/toolsets/index.md) and can be registered with an Agent using the `toolsets` argument.

You can use the async with agent context manager to open and close connections to all registered servers (and in the case of stdio servers, start and stop the subprocesses) around the context where they'll be used in agent runs. You can also use async with server to manage the connection or subprocess of a specific server, for example if you'd like to use it with multiple agents. If you don't explicitly enter one of these context managers to set up the server, this will be done automatically when it's needed (e.g. to list the available tools or call a specific tool), but it's more efficient to do so around the entire context where you expect the servers to be used.

### Streamable HTTP Client

MCPServerStreamableHTTP connects over HTTP using the [Streamable HTTP](https://modelcontextprotocol.io/introduction#streamable-http) transport to a server.

Note

MCPServerStreamableHTTP requires an MCP server to be running and accepting HTTP connections before running the agent. Running the server is not managed by Pydantic AI.

Before creating the Streamable HTTP client, we need to run a server that supports the Streamable HTTP transport.

streamable_http_server.py

```python
from mcp.server.fastmcp import FastMCP

app = FastMCP()

@app.tool()
def add(a: int, b: int) -> int:
    return a + b

if __name__ == '__main__':
    app.run(transport='streamable-http')
```

Then we can create the client:

[Learn about Gateway](https://ai.pydantic.dev/gateway) mcp_streamable_http_client.py

```python
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStreamableHTTP

server = MCPServerStreamableHTTP('http://localhost:8000/mcp')  # (1)!
agent = Agent('gateway/openai:gpt-5.2', toolsets=[server])  # (2)!

async def main():
    result = await agent.run('What is 7 plus 5?')
    print(result.output)
    #> The answer is 12.
```

1. Define the MCP server with the URL used to connect.
1. Create an agent with the MCP server attached.

mcp_streamable_http_client.py

```python
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStreamableHTTP

server = MCPServerStreamableHTTP('http://localhost:8000/mcp')  # (1)!
agent = Agent('openai:gpt-5.2', toolsets=[server])  # (2)!

async def main():
    result = await agent.run('What is 7 plus 5?')
    print(result.output)
    #> The answer is 12.
```

1. Define the MCP server with the URL used to connect.
1. Create an agent with the MCP server attached.

*(This example is complete, it can be run "as is" â€” you'll need to add `asyncio.run(main())` to run `main`)*

**What's happening here?**

- The model receives the prompt "What is 7 plus 5?"
- The model decides "Oh, I've got this `add` tool, that will be a good way to answer this question"
- The model returns a tool call
- Pydantic AI sends the tool call to the MCP server using the Streamable HTTP transport
- The model is called again with the return value of running the `add` tool (12)
- The model returns the final answer

You can visualise this clearly, and even see the tool call, by adding three lines of code to instrument the example with [logfire](https://logfire.pydantic.dev/docs):

mcp_sse_client_logfire.py

```python
import logfire

logfire.configure()
logfire.instrument_pydantic_ai()
```

### SSE Client

MCPServerSSE connects over HTTP using the [HTTP + Server Sent Events transport](https://spec.modelcontextprotocol.io/specification/2024-11-05/basic/transports/#http-with-sse) to a server.

Note

The SSE transport in MCP is deprecated, you should use Streamable HTTP instead.

Before creating the SSE client, we need to run a server that supports the SSE transport.

sse_server.py

```python
from mcp.server.fastmcp import FastMCP

app = FastMCP()

@app.tool()
def add(a: int, b: int) -> int:
    return a + b

if __name__ == '__main__':
    app.run(transport='sse')
```

Then we can create the client:

[Learn about Gateway](https://ai.pydantic.dev/gateway) mcp_sse_client.py

```python
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerSSE

server = MCPServerSSE('http://localhost:3001/sse')  # (1)!
agent = Agent('gateway/openai:gpt-5.2', toolsets=[server])  # (2)!


async def main():
    result = await agent.run('What is 7 plus 5?')
    print(result.output)
    #> The answer is 12.
```

1. Define the MCP server with the URL used to connect.
1. Create an agent with the MCP server attached.

mcp_sse_client.py

```python
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerSSE

server = MCPServerSSE('http://localhost:3001/sse')  # (1)!
agent = Agent('openai:gpt-5.2', toolsets=[server])  # (2)!


async def main():
    result = await agent.run('What is 7 plus 5?')
    print(result.output)
    #> The answer is 12.
```

1. Define the MCP server with the URL used to connect.
1. Create an agent with the MCP server attached.

*(This example is complete, it can be run "as is" â€” you'll need to add `asyncio.run(main())` to run `main`)*

### MCP "stdio" Server

MCP also offers [stdio transport](https://spec.modelcontextprotocol.io/specification/2024-11-05/basic/transports/#stdio) where the server is run as a subprocess and communicates with the client over `stdin` and `stdout`. In this case, you'd use the MCPServerStdio class.

In this example we use a simple MCP server that provides weather tools.

[Learn about Gateway](https://ai.pydantic.dev/gateway) mcp_stdio_client.py

```python
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio

server = MCPServerStdio('python', args=['mcp_server.py'], timeout=10)
agent = Agent('gateway/openai:gpt-5.2', toolsets=[server])


async def main():
    result = await agent.run('What is the weather in Paris?')
    print(result.output)
    #> The weather in Paris is sunny and 26 degrees Celsius.
```

mcp_stdio_client.py

```python
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio

server = MCPServerStdio('python', args=['mcp_server.py'], timeout=10)
agent = Agent('openai:gpt-5.2', toolsets=[server])


async def main():
    result = await agent.run('What is the weather in Paris?')
    print(result.output)
    #> The weather in Paris is sunny and 26 degrees Celsius.
```

## Loading MCP Servers from Configuration

Instead of creating MCP server instances individually in code, you can load multiple servers from a JSON configuration file using load_mcp_servers().

This is particularly useful when you need to manage multiple MCP servers or want to configure servers externally without modifying code.

### Configuration Format

The configuration file should be a JSON file with an `mcpServers` object containing server definitions. Each server is identified by a unique key and contains the configuration for that server type:

mcp_config.json

```json
{
  "mcpServers": {
    "python-runner": {
        "command": "uv",
        "args": ["run", "mcp-run-python", "stdio"]
    },
    "weather": {
      "command": "python",
      "args": ["mcp_server.py"]
    },
    "weather-api": {
      "url": "http://localhost:3001/sse"
    },
    "calculator": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

Note

The MCP server is only inferred to be an SSE server because of the `/sse` suffix. Any other server with the "url" field will be inferred to be a Streamable HTTP server.

We made this decision given that the SSE transport is deprecated.

### Environment Variables

The configuration file supports environment variable expansion using the `${VAR}` and `${VAR:-default}` syntax, [like Claude Code](https://code.claude.com/docs/en/mcp#environment-variable-expansion-in-mcp-json). This is useful for keeping sensitive information like API keys or host names out of your configuration files:

mcp_config_with_env.json

```json
{
  "mcpServers": {
    "python-runner": {
      "command": "${PYTHON_CMD:-python3}",
      "args": ["run", "${MCP_MODULE}", "stdio"],
      "env": {
        "API_KEY": "${MY_API_KEY}"
      }
    },
    "weather-api": {
      "url": "https://${SERVER_HOST:-localhost}:${SERVER_PORT:-8080}/sse"
    }
  }
}
```

When loading this configuration with load_mcp_servers():

- `${VAR}` references will be replaced with the corresponding environment variable values.
- `${VAR:-default}` references will use the environment variable value if set, otherwise the default value.

Warning

If a referenced environment variable using `${VAR}` syntax is not defined, a `ValueError` will be raised. Use the `${VAR:-default}` syntax to provide a fallback value.

### Usage

[Learn about Gateway](https://ai.pydantic.dev/gateway) mcp_config_loader.py

```python
from pydantic_ai import Agent
from pydantic_ai.mcp import load_mcp_servers

# Load all servers from configuration file
servers = load_mcp_servers('mcp_config.json')

# Create agent with all loaded servers
agent = Agent('gateway/openai:gpt-5.2', toolsets=servers)

async def main():
    result = await agent.run('What is 7 plus 5?')
    print(result.output)
```

mcp_config_loader.py

```python
from pydantic_ai import Agent
from pydantic_ai.mcp import load_mcp_servers

# Load all servers from configuration file
servers = load_mcp_servers('mcp_config.json')

# Create agent with all loaded servers
agent = Agent('openai:gpt-5.2', toolsets=servers)

async def main():
    result = await agent.run('What is 7 plus 5?')
    print(result.output)
```

*(This example is complete, it can be run "as is" â€” you'll need to add `asyncio.run(main())` to run `main`)*

## Tool call customization

The MCP servers provide the ability to set a `process_tool_call` which allows the customization of tool call requests and their responses.

A common use case for this is to inject metadata to the requests which the server call needs:

mcp_process_tool_call.py

```python
from typing import Any

from pydantic_ai import Agent, RunContext
from pydantic_ai.mcp import CallToolFunc, MCPServerStdio, ToolResult
from pydantic_ai.models.test import TestModel


async def process_tool_call(
    ctx: RunContext[int],
    call_tool: CallToolFunc,
    name: str,
    tool_args: dict[str, Any],
) -> ToolResult:
    """A tool call processor that passes along the deps."""
    return await call_tool(name, tool_args, {'deps': ctx.deps})


server = MCPServerStdio('python', args=['mcp_server.py'], process_tool_call=process_tool_call)
agent = Agent(
    model=TestModel(call_tools=['echo_deps']),
    deps_type=int,
    toolsets=[server]
)


async def main():
    result = await agent.run('Echo with deps set to 42', deps=42)
    print(result.output)
    #> {"echo_deps":{"echo":"This is an echo message","deps":42}}
```

How to access the metadata is MCP server SDK specific. For example with the [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk), it is accessible via the [`ctx: Context`](https://github.com/modelcontextprotocol/python-sdk#context) argument that can be included on tool call handlers:

mcp_server.py

```python
from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession

mcp = FastMCP('Pydantic AI MCP Server')
log_level = 'unset'


@mcp.tool()
async def echo_deps(ctx: Context[ServerSession, None]) -> dict[str, Any]:
    """Echo the run context.

    Args:
        ctx: Context object containing request and session information.

    Returns:
        Dictionary with an echo message and the deps.
    """
    await ctx.info('This is an info message')

    deps: Any = getattr(ctx.request_context.meta, 'deps')
    return {'echo': 'This is an echo message', 'deps': deps}

if __name__ == '__main__':
    mcp.run()
```

## Using Tool Prefixes to Avoid Naming Conflicts

When connecting to multiple MCP servers that might provide tools with the same name, you can use the `tool_prefix` parameter to avoid naming conflicts. This parameter adds a prefix to all tool names from a specific server.

This allows you to use multiple servers that might have overlapping tool names without conflicts:

[Learn about Gateway](https://ai.pydantic.dev/gateway) mcp_tool_prefix_http_client.py

```python
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerSSE

# Create two servers with different prefixes
weather_server = MCPServerSSE(
    'http://localhost:3001/sse',
    tool_prefix='weather'  # Tools will be prefixed with 'weather_'
)

calculator_server = MCPServerSSE(
    'http://localhost:3002/sse',
    tool_prefix='calc'  # Tools will be prefixed with 'calc_'
)

# Both servers might have a tool named 'get_data', but they'll be exposed as:
# - 'weather_get_data'
# - 'calc_get_data'
agent = Agent('gateway/openai:gpt-5.2', toolsets=[weather_server, calculator_server])
```

mcp_tool_prefix_http_client.py

```python
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerSSE

# Create two servers with different prefixes
weather_server = MCPServerSSE(
    'http://localhost:3001/sse',
    tool_prefix='weather'  # Tools will be prefixed with 'weather_'
)

calculator_server = MCPServerSSE(
    'http://localhost:3002/sse',
    tool_prefix='calc'  # Tools will be prefixed with 'calc_'
)

# Both servers might have a tool named 'get_data', but they'll be exposed as:
# - 'weather_get_data'
# - 'calc_get_data'
agent = Agent('openai:gpt-5.2', toolsets=[weather_server, calculator_server])
```

## Server Instructions

MCP servers can provide instructions during initialization that give context about how to best interact with the server's tools. These instructions are accessible via the instructions property after the server connection is established.

[Learn about Gateway](https://ai.pydantic.dev/gateway) mcp_server_instructions.py

```python
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStreamableHTTP

server = MCPServerStreamableHTTP('http://localhost:8000/mcp')
agent = Agent('gateway/openai:gpt-5.2', toolsets=[server])

@agent.instructions
async def mcp_server_instructions():
    return server.instructions  # (1)!

async def main():
    result = await agent.run('What is 7 plus 5?')
    print(result.output)
    #> The answer is 12.
```

1. The server connection is guaranteed to be established by this point, so `server.instructions` is available.

mcp_server_instructions.py

```python
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStreamableHTTP

server = MCPServerStreamableHTTP('http://localhost:8000/mcp')
agent = Agent('openai:gpt-5.2', toolsets=[server])

@agent.instructions
async def mcp_server_instructions():
    return server.instructions  # (1)!

async def main():
    result = await agent.run('What is 7 plus 5?')
    print(result.output)
    #> The answer is 12.
```

1. The server connection is guaranteed to be established by this point, so `server.instructions` is available.

## Tool metadata

MCP tools can include metadata that provides additional information about the tool's characteristics, which can be useful when filtering tools. The `meta`, `annotations`, and `output_schema` fields can be found on the `metadata` dict on the ToolDefinition object that's passed to filter functions.

## Resources

MCP servers can provide [resources](https://modelcontextprotocol.io/docs/concepts/resources) - files, data, or content that can be accessed by the client. Resources in MCP are application-driven, with host applications determining how to incorporate context manually, based on their needs. This means they will *not* be exposed to the LLM automatically (unless a tool returns a `ResourceLink` or `EmbeddedResource`).

Pydantic AI provides methods to discover and read resources from MCP servers:

- list_resources() - List all available resources on the server
- list_resource_templates() - List resource templates with parameter placeholders
- read_resource(uri) - Read the contents of a specific resource by URI

Resources are automatically converted: text content is returned as `str`, and binary content is returned as BinaryContent.

Before consuming resources, we need to run a server that exposes some:

mcp_resource_server.py

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP('Pydantic AI MCP Server')
log_level = 'unset'


@mcp.resource('resource://user_name.txt', mime_type='text/plain')
async def user_name_resource() -> str:
    return 'Alice'


if __name__ == '__main__':
    mcp.run()
```

Then we can create the client:

mcp_resources.py

```python
import asyncio

from pydantic_ai.mcp import MCPServerStdio


async def main():
    server = MCPServerStdio('python', args=['-m', 'mcp_resource_server'])

    async with server:
        # List all available resources
        resources = await server.list_resources()
        for resource in resources:
            print(f' - {resource.name}: {resource.uri} ({resource.mime_type})')
            #>  - user_name_resource: resource://user_name.txt (text/plain)

        # Read a text resource
        user_name = await server.read_resource('resource://user_name.txt')
        print(f'Text content: {user_name}')
        #> Text content: Alice


if __name__ == '__main__':
    asyncio.run(main())
```

*(This example is complete, it can be run "as is")*

## Custom TLS / SSL configuration

In some environments you need to tweak how HTTPS connections are established â€“ for example to trust an internal Certificate Authority, present a client certificate for **mTLS**, or (during local development only!) disable certificate verification altogether. All HTTP-based MCP client classes (MCPServerStreamableHTTP and MCPServerSSE) expose an `http_client` parameter that lets you pass your own pre-configured [`httpx.AsyncClient`](https://www.python-httpx.org/async/).

[Learn about Gateway](https://ai.pydantic.dev/gateway) mcp_custom_tls_client.py

```python
import ssl

import httpx

from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerSSE

# Trust an internal / self-signed CA
ssl_ctx = ssl.create_default_context(cafile='/etc/ssl/private/my_company_ca.pem')

# OPTIONAL: if the server requires **mutual TLS** load your client certificate
ssl_ctx.load_cert_chain(certfile='/etc/ssl/certs/client.crt', keyfile='/etc/ssl/private/client.key',)

http_client = httpx.AsyncClient(
    verify=ssl_ctx,
    timeout=httpx.Timeout(10.0),
)

server = MCPServerSSE(
    'http://localhost:3001/sse',
    http_client=http_client,  # (1)!
)
agent = Agent('gateway/openai:gpt-5.2', toolsets=[server])

async def main():
    result = await agent.run('How many days between 2000-01-01 and 2025-03-18?')
    print(result.output)
    #> There are 9,208 days between January 1, 2000, and March 18, 2025.
```

1. When you supply `http_client`, Pydantic AI re-uses this client for every request. Anything supported by **httpx** (`verify`, `cert`, custom proxies, timeouts, etc.) therefore applies to all MCP traffic.

mcp_custom_tls_client.py

```python
import ssl

import httpx

from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerSSE

# Trust an internal / self-signed CA
ssl_ctx = ssl.create_default_context(cafile='/etc/ssl/private/my_company_ca.pem')

# OPTIONAL: if the server requires **mutual TLS** load your client certificate
ssl_ctx.load_cert_chain(certfile='/etc/ssl/certs/client.crt', keyfile='/etc/ssl/private/client.key',)

http_client = httpx.AsyncClient(
    verify=ssl_ctx,
    timeout=httpx.Timeout(10.0),
)

server = MCPServerSSE(
    'http://localhost:3001/sse',
    http_client=http_client,  # (1)!
)
agent = Agent('openai:gpt-5.2', toolsets=[server])

async def main():
    result = await agent.run('How many days between 2000-01-01 and 2025-03-18?')
    print(result.output)
    #> There are 9,208 days between January 1, 2000, and March 18, 2025.
```

1. When you supply `http_client`, Pydantic AI re-uses this client for every request. Anything supported by **httpx** (`verify`, `cert`, custom proxies, timeouts, etc.) therefore applies to all MCP traffic.

## Client Identification

When connecting to an MCP server, you can optionally specify an [Implementation](https://modelcontextprotocol.io/specification/2025-11-25/schema#implementation) object as client information that will be sent to the server during initialization. This is useful for:

- Identifying your application in server logs
- Allowing servers to provide custom behavior based on the client
- Debugging and monitoring MCP connections
- Version-specific feature negotiation

All MCP client classes (MCPServerStdio, MCPServerStreamableHTTP, and MCPServerSSE) support the `client_info` parameter:

mcp_client_with_name.py

```python
from mcp import types as mcp_types

from pydantic_ai.mcp import MCPServerSSE

server = MCPServerSSE(
    'http://localhost:3001/sse',
    client_info=mcp_types.Implementation(
        name='MyApplication',
        version='2.1.0',
    ),
)
```

## MCP Sampling

What is MCP Sampling?

In MCP [sampling](https://modelcontextprotocol.io/docs/concepts/sampling) is a system by which an MCP server can make LLM calls via the MCP client - effectively proxying requests to an LLM via the client over whatever transport is being used.

Sampling is extremely useful when MCP servers need to use Gen AI but you don't want to provision them each with their own LLM credentials or when a public MCP server would like the connecting client to pay for LLM calls.

Confusingly it has nothing to do with the concept of "sampling" in observability, or frankly the concept of "sampling" in any other domain.

Sampling Diagram

Here's a mermaid diagram that may or may not make the data flow clearer:

```
sequenceDiagram
    participant LLM
    participant MCP_Client as MCP client
    participant MCP_Server as MCP server

    MCP_Client->>LLM: LLM call
    LLM->>MCP_Client: LLM tool call response

    MCP_Client->>MCP_Server: tool call
    MCP_Server->>MCP_Client: sampling "create message"

    MCP_Client->>LLM: LLM call
    LLM->>MCP_Client: LLM text response

    MCP_Client->>MCP_Server: sampling response
    MCP_Server->>MCP_Client: tool call response
```

Pydantic AI supports sampling as both a client and server. See the [server](https://ai.pydantic.dev/mcp/server/#mcp-sampling) documentation for details on how to use sampling within a server.

Sampling is automatically supported by Pydantic AI agents when they act as a client.

To be able to use sampling, an MCP server instance needs to have a sampling_model set. This can be done either directly on the server using the constructor keyword argument or the property, or by using agent.set_mcp_sampling_model() to set the agent's model or one specified as an argument as the sampling model on all MCP servers registered with that agent.

Let's say we have an MCP server that wants to use sampling (in this case to generate an SVG as per the tool arguments).

Sampling MCP Server

generate_svg.py

````python
import re
from pathlib import Path

from mcp import SamplingMessage
from mcp.server.fastmcp import Context, FastMCP
from mcp.types import TextContent

app = FastMCP()


@app.tool()
async def image_generator(ctx: Context, subject: str, style: str) -> str:
    prompt = f'{subject=} {style=}'
    # `ctx.session.create_message` is the sampling call
    result = await ctx.session.create_message(
        [SamplingMessage(role='user', content=TextContent(type='text', text=prompt))],
        max_tokens=1_024,
        system_prompt='Generate an SVG image as per the user input',
    )
    assert isinstance(result.content, TextContent)

    path = Path(f'{subject}_{style}.svg')
    # remove triple backticks if the svg was returned within markdown
    if m := re.search(r'^```\w*$(.+?)```$', result.content.text, re.S | re.M):
        path.write_text(m.group(1), encoding='utf-8')
    else:
        path.write_text(result.content.text, encoding='utf-8')
    return f'See {path}'


if __name__ == '__main__':
    # run the server via stdio
    app.run()
````

Using this server with an `Agent` will automatically allow sampling:

sampling_mcp_client.py

```python
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio

server = MCPServerStdio('python', args=['generate_svg.py'])
agent = Agent('openai:gpt-5.2', toolsets=[server])


async def main():
    agent.set_mcp_sampling_model()
    result = await agent.run('Create an image of a robot in a punk style.')
    print(result.output)
    #> Image file written to robot_punk.svg.
```

*(This example is complete, it can be run "as is")*

You can disallow sampling by setting allow_sampling=False when creating the server reference, e.g.:

sampling_disallowed.py

```python
from pydantic_ai.mcp import MCPServerStdio

server = MCPServerStdio(
    'python',
    args=['generate_svg.py'],
    allow_sampling=False,
)
```

## Elicitation

In MCP, [elicitation](https://modelcontextprotocol.io/docs/concepts/elicitation) allows a server to request for [structured input](https://modelcontextprotocol.io/specification/2025-06-18/client/elicitation#supported-schema-types) from the client for missing or additional context during a session.

Elicitation let models essentially say "Hold on - I need to know X before i can continue" rather than requiring everything upfront or taking a shot in the dark.

### How Elicitation works

Elicitation introduces a new protocol message type called [`ElicitRequest`](https://modelcontextprotocol.io/specification/2025-06-18/schema#elicitrequest), which is sent from the server to the client when it needs additional information. The client can then respond with an [`ElicitResult`](https://modelcontextprotocol.io/specification/2025-06-18/schema#elicitresult) or an `ErrorData` message.

Here's a typical interaction:

- User makes a request to the MCP server (e.g. "Book a table at that Italian place")
- The server identifies that it needs more information (e.g. "Which Italian place?", "What date and time?")
- The server sends an `ElicitRequest` to the client asking for the missing information.
- The client receives the request, presents it to the user (e.g. via a terminal prompt, GUI dialog, or web interface).
- User provides the requested information, `decline` or `cancel` the request.
- The client sends an `ElicitResult` back to the server with the user's response.
- With the structured data, the server can continue processing the original request.

This allows for a more interactive and user-friendly experience, especially for multi-staged workflows. Instead of requiring all information upfront, the server can ask for it as needed, making the interaction feel more natural.

### Setting up Elicitation

To enable elicitation, provide an elicitation_callback function when creating your MCP server instance:

restaurant_server.py

```python
from mcp.server.fastmcp import Context, FastMCP
from pydantic import BaseModel, Field

mcp = FastMCP(name='Restaurant Booking')


class BookingDetails(BaseModel):
    """Schema for restaurant booking information."""

    restaurant: str = Field(description='Choose a restaurant')
    party_size: int = Field(description='Number of people', ge=1, le=8)
    date: str = Field(description='Reservation date (DD-MM-YYYY)')


@mcp.tool()
async def book_table(ctx: Context) -> str:
    """Book a restaurant table with user input."""
    # Ask user for booking details using Pydantic schema
    result = await ctx.elicit(message='Please provide your booking details:', schema=BookingDetails)

    if result.action == 'accept' and result.data:
        booking = result.data
        return f'âœ… Booked table for {booking.party_size} at {booking.restaurant} on {booking.date}'
    elif result.action == 'decline':
        return 'No problem! Maybe another time.'
    else:  # cancel
        return 'Booking cancelled.'


if __name__ == '__main__':
    mcp.run(transport='stdio')
```

This server demonstrates elicitation by requesting structured booking details from the client when the `book_table` tool is called. Here's how to create a client that handles these elicitation requests:

[Learn about Gateway](https://ai.pydantic.dev/gateway) client_example.py

```python
import asyncio
from typing import Any

from mcp.client.session import ClientSession
from mcp.shared.context import RequestContext
from mcp.types import ElicitRequestParams, ElicitResult

from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio


async def handle_elicitation(
    context: RequestContext[ClientSession, Any, Any],
    params: ElicitRequestParams,
) -> ElicitResult:
    """Handle elicitation requests from MCP server."""
    print(f'\n{params.message}')

    if not params.requestedSchema:
        response = input('Response: ')
        return ElicitResult(action='accept', content={'response': response})

    # Collect data for each field
    properties = params.requestedSchema['properties']
    data = {}

    for field, info in properties.items():
        description = info.get('description', field)

        value = input(f'{description}: ')

        # Convert to proper type based on JSON schema
        if info.get('type') == 'integer':
            data[field] = int(value)
        else:
            data[field] = value

    # Confirm
    confirm = input('\nConfirm booking? (y/n/c): ').lower()

    if confirm == 'y':
        print('Booking details:', data)
        return ElicitResult(action='accept', content=data)
    elif confirm == 'n':
        return ElicitResult(action='decline')
    else:
        return ElicitResult(action='cancel')


# Set up MCP server connection
restaurant_server = MCPServerStdio(
    'python', args=['restaurant_server.py'], elicitation_callback=handle_elicitation
)

# Create agent
agent = Agent('gateway/openai:gpt-5.2', toolsets=[restaurant_server])


async def main():
    """Run the agent to book a restaurant table."""
    result = await agent.run('Book me a table')
    print(f'\nResult: {result.output}')


if __name__ == '__main__':
    asyncio.run(main())
```

client_example.py

```python
import asyncio
from typing import Any

from mcp.client.session import ClientSession
from mcp.shared.context import RequestContext
from mcp.types import ElicitRequestParams, ElicitResult

from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio


async def handle_elicitation(
    context: RequestContext[ClientSession, Any, Any],
    params: ElicitRequestParams,
) -> ElicitResult:
    """Handle elicitation requests from MCP server."""
    print(f'\n{params.message}')

    if not params.requestedSchema:
        response = input('Response: ')
        return ElicitResult(action='accept', content={'response': response})

    # Collect data for each field
    properties = params.requestedSchema['properties']
    data = {}

    for field, info in properties.items():
        description = info.get('description', field)

        value = input(f'{description}: ')

        # Convert to proper type based on JSON schema
        if info.get('type') == 'integer':
            data[field] = int(value)
        else:
            data[field] = value

    # Confirm
    confirm = input('\nConfirm booking? (y/n/c): ').lower()

    if confirm == 'y':
        print('Booking details:', data)
        return ElicitResult(action='accept', content=data)
    elif confirm == 'n':
        return ElicitResult(action='decline')
    else:
        return ElicitResult(action='cancel')


# Set up MCP server connection
restaurant_server = MCPServerStdio(
    'python', args=['restaurant_server.py'], elicitation_callback=handle_elicitation
)

# Create agent
agent = Agent('openai:gpt-5.2', toolsets=[restaurant_server])


async def main():
    """Run the agent to book a restaurant table."""
    result = await agent.run('Book me a table')
    print(f'\nResult: {result.output}')


if __name__ == '__main__':
    asyncio.run(main())
```

### Supported Schema Types

MCP elicitation supports string, number, boolean, and enum types with flat object structures only. These limitations ensure reliable cross-client compatibility. See [supported schema types](https://modelcontextprotocol.io/specification/2025-06-18/client/elicitation#supported-schema-types) for details.

### Security

MCP Elicitation requires careful handling - servers must not request sensitive information, and clients must implement user approval controls with clear explanations. See [security considerations](https://modelcontextprotocol.io/specification/2025-06-18/client/elicitation#security-considerations) for details.
