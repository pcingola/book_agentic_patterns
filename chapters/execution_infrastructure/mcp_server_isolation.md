## MCP Server Isolation

MCP servers deserve the same network isolation treatment as code-execution sandboxes. When your agent connects to an MCP server -- particularly one you did not write -- every tool call is an opportunity for arbitrary code to run on the server side. A tool that fetches data from an external API, sends an email, or posts to a webhook can exfiltrate private data just as easily as a line of Python in a REPL sandbox. Running MCP servers inside Docker containers and applying the kill switch pattern from the previous section closes this gap.

### Two containers, one server

The approach is straightforward: run two instances of the same MCP server image, each with a different network mode. The first instance runs on the bridge network with full connectivity. The second runs on an isolated network with no external access (or proxied access through Envoy, depending on the sensitivity level). Both containers mount the same workspace volume so they share state. The agent's MCP client switches which instance it connects to based on the session's `PrivateData` status.

```
 +--------+       no private data        +-------------------+
 |        | ---------------------------> | MCP Server        |
 | Agent  |                              | (bridge network)  |
 |        |       private data present   +-------------------+
 |        | ---------------------------> +-------------------+
 +--------+                              | MCP Server        |
                                         | (no network)      |
                                         +-------------------+
```

The MCP server code does not change between instances. The only difference is the Docker network configuration. Tools that require external connectivity will fail with connection errors in the isolated instance, which is the desired behavior -- the agent should not be able to reach external services through MCP tools once private data enters the session.

### Configuration

The `config.yaml` already holds MCP client entries with a `url` field pointing at the server. To support the dual-container pattern, each MCP server entry gets a `url_isolated` field for the restricted instance:

```yaml
mcp_servers:
  data_tools:
    type: client
    url: "http://data-tools:8000/mcp"
    url_isolated: "http://data-tools-isolated:8000/mcp"
    read_timeout: 60
```

The `MCPClientConfig` model adds the optional field:

```python
class MCPClientConfig(BaseModel):
    type: str = Field(default="client")
    url: str
    url_isolated: str | None = None
    read_timeout: int = Field(default=60)
```

When `url_isolated` is not set, the client always uses `url` regardless of private data status -- the server either does not need isolation or handles it internally.

### Client-side switching

The `get_mcp_client()` function resolves the correct URL at connection time by checking the session's private data status:

```python
def get_mcp_client(
    name: str,
    config_path: Path | str | None = None,
    bearer_token: str | None = None,
) -> MCPServerStreamableHTTP:
    settings = _load_mcp_settings(config_path)
    config = settings.get(name)

    url = config.url
    if config.url_isolated and session_has_private_data(*get_user_session()):
        url = config.url_isolated

    headers = {"Authorization": f"Bearer {bearer_token}"} if bearer_token else None
    return MCPServerStreamableHTTP(url=url, timeout=config.read_timeout, headers=headers)
```

Because PydanticAI creates a new MCP connection context for each agent run, the switch happens naturally between turns. When private data enters the session mid-conversation, the next agent run picks up the isolated URL automatically. No container recreation or connection teardown is needed on the client side -- it simply points at a different endpoint.

### Deploying the containers

A typical `docker-compose.yaml` runs both instances from the same image:

```yaml
services:
  data-tools:
    image: my-mcp-server:latest
    networks: [bridge]
    volumes: [workspace:/workspace]

  data-tools-isolated:
    image: my-mcp-server:latest
    network_mode: "none"
    volumes: [workspace:/workspace]
```

For CONFIDENTIAL data where proxied access is acceptable, the isolated instance can use the same Envoy sidecar pattern described in the kill switch section, attaching it to an internal Docker network with the proxy as the only gateway.

### When to use this pattern

This pattern is essential for third-party or untrusted MCP servers where you cannot audit or control the tool implementations. But it is also highly recommended for your own servers: even well-tested code can have bugs, missed edge cases, or regressions that accidentally leak private data over the network. The container-level network block acts as a safety net that enforces the invariant regardless of application-level correctness. Think of it as defense-in-depth -- `@tool_permission(CONNECT)` and compliance checks are the first line, but the network kill switch ensures that a code mistake cannot silently bypass them.
