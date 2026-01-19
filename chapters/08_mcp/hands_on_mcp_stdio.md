# Hands-On: MCP STDIO Transport

The STDIO transport is MCP's simplest communication mechanism. The client spawns the server as a subprocess and exchanges JSON-RPC messages through standard input and output streams. This transport is ideal for local tool servers where the client and server run on the same machine.

This hands-on explores the raw MCP protocol through `example_mcp_stdio.ipynb`, demonstrating the message format and lifecycle that underlies all MCP communication.

## Why STDIO Matters

Before examining high-level MCP client libraries, understanding the underlying protocol clarifies what those libraries abstract. STDIO transport strips away network complexity, authentication layers, and connection management. What remains is the essential exchange: newline-delimited JSON-RPC messages flowing between client and server.

This simplicity makes STDIO the default choice for local development and testing. When you run `fastmcp run -t stdio server.py`, you get an MCP server that speaks the full protocol without requiring HTTP infrastructure, TLS certificates, or port management.

## Starting the Server

In `example_mcp_stdio.ipynb`, the server starts as a subprocess:

```python
proc = subprocess.Popen(
    ['fastmcp', 'run', '-t', 'stdio', 'example_mcp_server.py'],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=1
)
```

The `-t stdio` flag tells FastMCP to use STDIO transport rather than HTTP. The subprocess pipes capture stdin and stdout for bidirectional communication. Line buffering (`bufsize=1`) ensures messages are sent immediately rather than waiting for buffer fills.

## Message Format

MCP uses JSON-RPC 2.0 as its message format. Every message is a single line of JSON terminated by a newline. This constraint is critical: multi-line pretty-printed JSON will break the protocol.

The helper function in the notebook handles this:

```python
def send_message(message: dict) -> dict | None:
    line = json.dumps(message)
    proc.stdin.write(line + '\n')
    proc.stdin.flush()

    if 'id' in message:
        response = proc.stdout.readline()
        return json.loads(response)
```

`json.dumps()` produces compact single-line JSON by default. The function distinguishes between requests (which have an `id` and expect a response) and notifications (which have no `id` and expect nothing back).

## The MCP Lifecycle

MCP sessions follow a defined lifecycle: initialization, active operation, and shutdown. The protocol enforces this order; attempting to call tools before initialization completes will fail.

### Initialization

The client initiates the session with an `initialize` request:

```python
init_request = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-03-26",
        "capabilities": {
            "roots": {"listChanged": True},
            "sampling": {}
        },
        "clientInfo": {
            "name": "ExampleClient",
            "version": "1.0.0"
        }
    }
}
```

The request includes the protocol version for compatibility checking, the client's capabilities (what features it supports), and client identification. The server responds with its own capabilities, establishing what operations are available for this session.

### Initialized Notification

After receiving the initialization response, the client sends a notification to confirm readiness:

```python
initialized_notification = {
    "jsonrpc": "2.0",
    "method": "notifications/initialized"
}
```

This is a notification, not a request. It has no `id` field and receives no response. The server uses this signal to transition the session into the active phase.

### Active Phase

Once initialized, the client can discover and invoke server capabilities. The `tools/list` method returns available tools:

```python
list_tools_request = {
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/list"
}
```

The response includes tool names, descriptions, and JSON schemas for their inputs. This is the same information that agent frameworks use to present tools to language models.

Tool invocation uses `tools/call`:

```python
call_tool_request = {
    "jsonrpc": "2.0",
    "id": 4,
    "method": "tools/call",
    "params": {
        "name": "add",
        "arguments": {
            "a": 40,
            "b": 2
        }
    }
}
```

The server validates arguments against the tool's schema, executes the tool, and returns the result. If arguments are invalid or the tool fails, the response contains an error object instead of a result.

## Error Handling

The protocol distinguishes between transport errors and application errors. When the notebook sends invalid arguments:

```python
call_tool_error = {
    "jsonrpc": "2.0",
    "id": 5,
    "method": "tools/call",
    "params": {
        "name": "add",
        "arguments": {
            "a": 40,
            "z": "2"  # Invalid argument
        }
    }
}
```

The server returns a structured error response rather than crashing. This allows clients to handle failures gracefully and potentially retry with corrected arguments.

## Connection to Higher-Level Abstractions

When you use `MCPServerStdio` from PydanticAI, it performs exactly this sequence internally. The agent framework handles initialization, capability discovery, and message formatting transparently. Understanding the raw protocol helps debug issues when they arise and clarifies what information flows between agents and tools.

The same protocol semantics apply regardless of transport. Whether communicating over STDIO, HTTP, or WebSockets, the message structure and lifecycle remain identical. Only the delivery mechanism changes.

## Key Takeaways

STDIO transport provides the simplest MCP communication path: subprocess pipes carrying newline-delimited JSON-RPC messages.

The MCP lifecycle is explicit: initialize, confirm initialization, operate, shutdown. Each phase has defined rules about what operations are permitted.

Messages are either requests (with `id`, expecting response) or notifications (without `id`, fire-and-forget). This distinction matters for correct protocol implementation.

Tool discovery through `tools/list` and invocation through `tools/call` form the foundation of MCP's tool integration. The protocol handles argument validation and error reporting in a structured way.
