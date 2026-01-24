# MCP Integration Plan

## Goal

Enable config-driven MCP server connections (clients) and MCP server creation from config.yaml.

## Gaps

**1. No MCP configuration in config.yaml**

Currently URLs are hardcoded in notebooks.

**2. No factory functions for MCP clients or servers**

Need functions to create clients (to connect to MCP servers) and servers (to expose tools) from config.

## Implementation

### 1. Add `mcp_servers` section to config.yaml

```yaml
mcp_servers:
  filesystem:
    url: http://localhost:8001/mcp/
    read_timeout: 300

  code_analysis:
    url: http://localhost:8002/mcp/
    read_timeout: 60

  my_server:
    name: "My MCP Server"
    instructions: "Provides code analysis tools"
    port: 8003
```

### 2. Create `agentic_patterns/core/mcp.py`

```python
# Client functions (to connect to external MCP servers)
def get_mcp_client(name: str) -> MCPServerStreamableHTTP:
    """Create MCP client from config.yaml by name."""

def get_mcp_clients(names: list[str]) -> list[MCPServerStreamableHTTP]:
    """Create multiple MCP clients from config.yaml."""

# Server functions (to create MCP servers)
def get_mcp_server(name: str) -> FastMCP:
    """Create FastMCP server instance from config.yaml by name."""
```

### 3. Usage

Client usage (connecting to MCP servers as toolsets):
```python
from agentic_patterns.core.mcp import get_mcp_clients
from agentic_patterns.core.agents import get_agent

servers = get_mcp_clients(["filesystem", "code_analysis"])
agent = get_agent(toolsets=servers)
```

Server usage (creating an MCP server):
```python
from agentic_patterns.core.mcp import get_mcp_server

mcp = get_mcp_server("my_server")

@mcp.tool()
def analyze_code(code: str) -> str:
    ...

# Run with: mcp.run()
```

## Files to Create/Modify

- `config.yaml`: Add `mcp_servers` section
- `agentic_patterns/core/mcp.py`: New file with client and server factory functions
- `agentic_patterns/core/config/config.py`: Add MCP config models
