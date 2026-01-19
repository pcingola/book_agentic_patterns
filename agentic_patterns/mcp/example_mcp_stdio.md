# MCP example & Demo

## Example: Run on STDIN

Run the MCP server:
```bash
./scripts/example_mcp_server.sh
```

### 1. Initialize request

```
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2025-03-26",
    "capabilities": {
      "roots": {
        "listChanged": true
      },
      "sampling": {}
    },
    "clientInfo": {
      "name": "ExampleClient",
      "version": "1.0.0"
    }
  }
}
```

Note: It MUST be in one line!
```
{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-03-26", "capabilities": {"roots": {"listChanged": true}, "sampling": {}}, "clientInfo": {"name": "ExampleClient", "version": "1.0.0"}}}
```

### 2. Initialized OK

```
{"jsonrpc": "2.0", "method": "notifications/initialized" }
```

### 3. Ping
```
{"jsonrpc": "2.0", "id":"123", "method":"ping"}
```

### 4. List tools
```
{"jsonrpc" :"2.0", "id" :1, "method" :"tools/list"}
```

### 5. Call tool: `Add`

```
{
  "jsonrpc": "2.0",
  "id": 2,
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

```
{"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "add", "arguments": {"a": 40 ,"b": 2}}}
```

### 6. Call tool: `Add`, with an error

```
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "add",
    "arguments": {
      "a": 40,
      "z": "2"
    }
  }
}
```

```
{"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "add", "arguments": {"a": 40 ,"z": "2"}}}
```

## Example 2: Use MCP inspector

Run in 'dev' mode:
```
mcp dev server.py
```