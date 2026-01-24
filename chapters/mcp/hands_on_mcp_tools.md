## Hands-On: MCP Tools with Agents

The previous hands-on explored the raw MCP protocol, showing the JSON-RPC messages that flow between client and server. In practice, agent frameworks handle this protocol transparently. This hands-on demonstrates how agents connect to MCP servers and use their tools through `example_agent_mcp_client_stdio.ipynb` and `example_agent_mcp_client_http.ipynb`.

## The MCP Server

Before connecting an agent, we need an MCP server that exposes tools. The file `example_mcp_server.py` defines a minimal server:

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Demo")

@mcp.tool()
def add(a: int, b: int) -> int:
    """ Add two numbers """
    return a + b
```

The `@mcp.tool()` decorator registers the function as an MCP tool. FastMCP extracts the function's type hints to generate a JSON schema and uses the docstring as the tool description. When an agent connects, it receives this schema and can invoke the tool by name with appropriate arguments.

This is the same tool definition pattern used in Chapter 3, but now the tool lives in a separate process. The agent doesn't import the function directly; it communicates with it through the MCP protocol.

## STDIO Transport

The STDIO transport spawns the MCP server as a subprocess and communicates through pipes. This is the simplest approach for local development because everything runs in a single command.

In `example_agent_mcp_client_stdio.ipynb`:

```python
from pydantic_ai.mcp import MCPServerStdio
from agentic_patterns.core.agents import get_agent, run_agent

server = MCPServerStdio(command='fastmcp', args=['run', '-t', 'stdio', 'example_mcp_server.py'])
agent = get_agent(toolsets=[server])
```

`MCPServerStdio` encapsulates the subprocess management. When passed as a toolset to `get_agent`, the agent knows to connect to this server for tool discovery. The `-t stdio` flag tells FastMCP to use STDIO transport rather than starting an HTTP server.

Running the agent establishes the connection:

```python
async with agent:
    result, nodes = await run_agent(agent, "What is 40123456789 plus 2123456789?", verbose=True)
```

The `async with agent` context manager triggers the MCP handshake: initialization, capability exchange, and tool discovery. Inside this context, the agent has access to the `add` tool. When the model decides to use it, the framework sends a `tools/call` request through the subprocess pipes and returns the result to the model.

The STDIO transport is self-contained. The notebook cell that creates `MCPServerStdio` is sufficient; no separate terminal or server startup is needed.

## HTTP Transport

For remote servers or when the MCP server needs to persist across multiple client sessions, HTTP transport is appropriate. Unlike STDIO, the server must be started separately before the client connects.

Start the server in a separate terminal:

```bash
fastmcp run example_mcp_server.py
```

This launches an HTTP server (default port 8000) that accepts MCP connections. The server remains running until manually stopped.

In `example_agent_mcp_client_http.ipynb`:

```python
from pydantic_ai.mcp import MCPServerStreamableHTTP
from agentic_patterns.core.agents import get_agent, run_agent

server = MCPServerStreamableHTTP(url='http://127.0.0.1:8000/mcp/')
agent = get_agent(toolsets=[server])
```

`MCPServerStreamableHTTP` connects to an existing server rather than spawning one. The URL points to the MCP endpoint exposed by FastMCP. From this point, agent usage is identical to STDIO: enter the async context, run the agent, and tools work transparently.

The HTTP transport adds a deployment step but enables scenarios that STDIO cannot: multiple clients sharing one server, servers running on remote machines, and servers that maintain state across sessions.

## What the Agent Sees

Regardless of transport, the agent framework performs the same operations:

1. Connect to the MCP server and complete the initialization handshake
2. Call `tools/list` to discover available tools
3. Present tool schemas to the language model alongside the conversation
4. When the model generates a tool call, send `tools/call` to the server
5. Return the result to the model for incorporation into its response

The model never knows whether tools come from MCP servers, local functions, or other sources. It sees tool schemas and decides when to call them based on the task. This abstraction is the point of MCP: tools become interchangeable components that can be developed, deployed, and composed independently.

## Key Takeaways

MCP servers expose tools through a standard protocol. The `@mcp.tool()` decorator in FastMCP handles schema generation and registration.

STDIO transport is self-contained: the agent spawns the server as a subprocess. Use this for local development and testing.

HTTP transport requires starting the server separately. Use this for remote servers, shared servers, or persistent deployments.

Agent frameworks abstract the transport details. Once configured, tools from MCP servers work identically to local tools.
