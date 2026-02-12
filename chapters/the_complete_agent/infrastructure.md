## Infrastructure: The Distributed Agent

The Full Agent runs everything in a single process. Tools are Python functions imported directly, sub-agents are instantiated from `AgentSpec` objects and executed by the `TaskBroker` in the same event loop. This is convenient for development, but it means every capability must live in the same Python environment and share the same process lifetime.

The Infrastructure Agent keeps the same agent architecture -- `AgentSpec`, `OrchestratorAgent`, prompt templates, skills -- but replaces the tool source and delegation target. Direct Python tool imports become MCP server connections. In-process sub-agents become remote A2A servers. The agent itself does not change; the `AgentSpec` fields do.

### What Changes

The monolithic agent imports tools as Python functions and passes them via the `tools` field of `AgentSpec`. The infrastructure agent declares `mcp_servers` instead, each pointing to a running FastMCP server. When the `OrchestratorAgent` enters its async context, it creates `MCPServerStreamableHTTP` toolset objects and passes them to `get_agent(toolsets=[...])`. The PydanticAI `Agent` then discovers available tools by connecting to each MCP server at startup.

Similarly, the monolithic agent declares `sub_agents` -- a list of `AgentSpec` objects that the `TaskBroker` instantiates on demand. The infrastructure agent declares `a2a_clients` instead, each pointing to a running A2A server. The `OrchestratorAgent` fetches each server's agent card, generates a delegation tool per card via `create_a2a_tool()`, and appends the agent descriptions to the system prompt.

The resulting config has no `tools` and no `sub_agents`:

```yaml
agents:
  infrastructure_agent:
    system_prompt: the_complete_agent/agent_infrastructure.md
    mcp_servers: [file_ops, sandbox, todo, format_conversion]
    a2a_clients: [nl2sql, data_analysis, vocabulary]
```

The notebook loads it with `AgentSpec.from_config("infrastructure_agent")`, same as V3-V5.

### MCP Servers as Tool Providers

The coordinator connects to four MCP servers for its direct tools: `file_ops` (file, CSV, and JSON operations), `sandbox` (Docker execution), `todo` (task management), and `format_conversion` (document conversion). Each runs as an independent HTTP service started via `fastmcp run ... --transport http --port N`.

The A2A servers also connect to MCP servers internally. The `data_analysis` A2A server connects to four: `data_analysis` (DataFrame operations), `data_viz` (plotting), `file_ops` (file, CSV, and JSON I/O), and `repl` (Python notebook execution). The monolithic version imported file, CSV, and JSON tools from three separate modules; the distributed version consolidates them into a single `file_ops` MCP server. The `nl2sql` A2A server connects to `sql`. The `vocabulary` A2A server connects to `vocabulary`. All MCP connections are declared in `config.yaml` under `mcp_servers`.

### A2A Servers as Delegation Targets

Each A2A server wraps a PydanticAI agent with MCP toolsets and exposes it via the A2A protocol. The pattern is minimal:

```python
mcp_client = get_mcp_client("vocabulary")
agent = get_agent(toolsets=[mcp_client], instructions=system_prompt)
app = agent.to_a2a(name="VocabularyExpert", description="...", skills=skills)
app.add_middleware(AuthSessionMiddleware)
```

The coordinator discovers each A2A server's capabilities by fetching its agent card from `/.well-known/agent-card.json`. The `OrchestratorAgent._connect_a2a()` method does this automatically, creating one delegation tool per server. The A2A agent descriptions are appended to the system prompt by `build_coordinator_prompt()`, so no explicit A2A section is needed in the prompt template.

### The Launch Script

Starting the distributed system requires launching nine MCP servers and three A2A servers. The launch script (`scripts/launch_infrastructure.sh`) starts all processes in the background with a trap to kill them on exit. MCP servers start first since A2A servers depend on them for tool discovery at import time.

### The Example

The notebook (`agentic_patterns/examples/the_complete_agent/example_agent_infrastructure.ipynb`) runs the same two prompts as the Full Agent to demonstrate equivalent capability. Turn 1 queries the bookstore database (routes to the `nl2sql` A2A server). Turn 2 asks for parallel work (routes to both `nl2sql` and `data_analysis` A2A servers). The agent uses its MCP-connected file tools to write the final report.

The full example is in `agentic_patterns/examples/the_complete_agent/example_agent_infrastructure.ipynb`.
