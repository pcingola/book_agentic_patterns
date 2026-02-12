# Plan: Infrastructure Section (The Complete Agent)

Decompose the V5 monolithic agent into a distributed architecture using MCP servers for tool access and A2A servers for agent delegation.

## Architecture

The distributed agent replaces direct Python tool imports and in-process sub-agents with network services. The `OrchestratorAgent` already supports all six capabilities simultaneously (tools, MCP, A2A, skills, sub-agents, tasks); the change is which fields of `AgentSpec` are populated.

| Monolithic (V5)                          | Distributed (Infrastructure)              |
|------------------------------------------|-------------------------------------------|
| Direct Python tool imports (file, sandbox, todo, format_conversion) | MCP server connections (file_ops, sandbox, todo, format_conversion) |
| In-process sub-agents via TaskBroker (data_analyst, sql_analyst, vocabulary_expert) | Remote A2A servers (data_analysis, nl2sql, vocabulary) |
| Skills auto-discovered locally | Skills auto-discovered locally (unchanged) |
| TaskBroker with delegate/submit_task/wait | TaskBroker stays intact alongside A2A delegation |

The data_analysis A2A server connects to multiple MCP servers (data_analysis, data_viz, file_ops, repl), matching the monolithic data_analyst sub-agent's full tool set.

## Steps

### 1. Fix OrchestratorAgent MCP support

**File:** `agentic_patterns/core/agents/orchestrator.py`

The current `_connect_mcp_and_a2a` enters MCP server contexts via exit stack but never passes them to the PydanticAI Agent. The tools from MCP servers are not surfaced.

Fix: create `MCPServerStreamableHTTP` objects, pass as `toolsets` to `get_agent()`, enter the agent's async context via exit stack so connections stay alive across `run()` calls. Separate MCP connection logic from A2A so each is clear.

```python
# In __aenter__:
mcp_toolsets = self._create_mcp_toolsets()
a2a_cards = await self._connect_a2a(tools)
...
agent_kwargs = {}
if mcp_toolsets:
    agent_kwargs["toolsets"] = mcp_toolsets
self._agent = await asyncio.to_thread(
    get_agent, model=self.spec.model, system_prompt=self._system_prompt,
    tools=tools, **agent_kwargs,
)
if mcp_toolsets:
    await self._exit_stack.enter_async_context(self._agent)
```

### 2. Update data_analysis A2A server

**File:** `agentic_patterns/a2a/data_analysis/server.py`

Currently connects to only the `data_analysis` MCP. The prompt (`prompts/a2a/data_analysis/system_prompt.md`) already describes five tool sets: file ops, CSV/JSON, data analysis, visualization, and REPL.

Fix: connect to all matching MCP servers. The `get_agent(toolsets=[...])` parameter accepts a list.

```python
MCP_NAMES = ["file_ops", "data_analysis", "data_viz", "repl"]
mcp_clients = [get_mcp_client(name) for name in MCP_NAMES]
skills = []
for name in MCP_NAMES:
    skills += asyncio.run(mcp_to_skills(name))
agent = get_agent(toolsets=mcp_clients, instructions=system_prompt)
```

### 3. Create vocabulary MCP server

**New files:**
- `agentic_patterns/mcp/vocabulary/__init__.py` (empty)
- `agentic_patterns/mcp/vocabulary/server.py`
- `agentic_patterns/mcp/vocabulary/tools.py`

Wraps `VocabularyConnector` methods as MCP tools. Follows the established pattern: `create_mcp_server()`, `register_tools()`, `@tool_permission()`, `ToolRetryError` for bad input.

Tools to expose (from VocabularyConnector): `vocab_list`, `vocab_info`, `vocab_lookup`, `vocab_search`, `vocab_validate`, `vocab_suggest`, `vocab_parent`, `vocab_children`, `vocab_ancestors`, `vocab_descendants`, `vocab_relationships`, `vocab_related`.

### 4. Create vocabulary A2A server

**New files:**
- `agentic_patterns/a2a/vocabulary/__init__.py` (empty)
- `agentic_patterns/a2a/vocabulary/server.py`
- `prompts/a2a/vocabulary/system_prompt.md`

Follows the same pattern as nl2sql and data_analysis A2A servers. Connects to the vocabulary MCP server. The prompt reuses content from `agents/vocabulary.py`'s SYSTEM_PROMPT.

```python
mcp_client = get_mcp_client("vocabulary")
skills = asyncio.run(mcp_to_skills("vocabulary"))
agent = get_agent(toolsets=[mcp_client], instructions=system_prompt)
app = agent.to_a2a(name="VocabularyExpert", description="...", skills=skills)
app.add_middleware(AuthSessionMiddleware)
```

### 5. Update config.yaml

**MCP client entries** (new, ports 8100+):
- `file_ops`: http://localhost:8100/mcp (read_timeout: 300)
- `sandbox`: http://localhost:8101/mcp (read_timeout: 300)
- `todo`: http://localhost:8102/mcp (read_timeout: 60)
- `format_conversion`: http://localhost:8103/mcp (read_timeout: 120)
- `data_viz`: http://localhost:8104/mcp (read_timeout: 300)
- `repl`: http://localhost:8105/mcp (read_timeout: 300)
- `vocabulary`: http://localhost:8106/mcp (read_timeout: 60)

**Existing entries kept as-is** (used by A2A servers internally):
- `data_analysis`: http://localhost:8010/mcp
- `sql`: http://localhost:8011/mcp

**A2A client section** (new):
```yaml
a2a:
  clients:
    nl2sql:
      url: http://localhost:8200
      timeout: 300
    data_analysis:
      url: http://localhost:8201
      timeout: 300
    vocabulary:
      url: http://localhost:8202
      timeout: 300
```

### 6. Create agent prompt

**New file:** `prompts/the_complete_agent/agent_infrastructure.md`

Same structure as `agent_full.md`. Includes shared blocks (workspace, sandbox, skills, sub_agents). Keeps task management and background tasks sections -- the TaskBroker works alongside A2A delegation. Format conversion section. Workflow section.

The A2A agent descriptions are auto-appended by `OrchestratorAgent._build_system_prompt()` via `build_coordinator_prompt(a2a_cards)`, so no explicit A2A section is needed in the prompt template.

### 7. Create launch script

**New file:** `scripts/launch_infrastructure.sh`

Starts all servers as background processes with a trap to kill all children on EXIT.

**MCP servers** (fastmcp run ... --transport http --port N):
- file_ops (8100), sandbox (8101), todo (8102), format_conversion (8103)
- data_analysis (8010), data_viz (8104), sql (8011), repl (8105), vocabulary (8106)

**A2A servers** (uvicorn ... --port N):
- nl2sql (8200), data_analysis (8201), vocabulary (8202)

Note: A2A data_analysis connects to MCP servers at 8010 (data_analysis), 8104 (data_viz), 8100 (file_ops), 8105 (repl). These must start before the A2A server.

### 8. Create example notebook

**New file:** `agentic_patterns/examples/the_complete_agent/example_agent_infrastructure.ipynb`

Builds `AgentSpec` with:
- `mcp_servers` loaded from config (file_ops, sandbox, todo, format_conversion)
- `a2a_clients` loaded from config (nl2sql, data_analysis, vocabulary)
- Skills auto-discovered from SKILLS_DIR
- No `sub_agents` (delegation via A2A), but broker pattern available if needed

Runs the same two prompts as V5 to demonstrate equivalent capability:
- Turn 1: Synchronous -- query bookstore database (routes to nl2sql A2A)
- Turn 2: Parallel-capable -- query + chart (routes to nl2sql and data_analysis A2A)

### 9. Write chapter section

**New file:** `chapters/the_complete_agent/infrastructure.md`

Topics:
- One-line intro: deploying the monolithic agent as distributed services
- From monolith to services: what changes (tool source, delegation target) and what stays (prompt structure, skills, broker)
- MCP servers as tool providers: the coordinator's `mcp_servers` field, config, launch
- A2A servers as delegation targets: the coordinator's `a2a_clients` field, agent cards, auto-generated delegation tools
- The data_analysis A2A as a multi-MCP agent (connects to 4 MCP servers)
- The launch script: starting the infrastructure
- The example: same prompts, distributed execution
- Code snippets from the notebook showing the AgentSpec

### 10. Update chapter index

**File:** `chapters/the_complete_agent/chapter.md`

Add: `[Infrastructure](./infrastructure.md)` after Server Requirements.

## Port Summary

| Service | Type | Port | Config Name |
|---------|------|------|-------------|
| file_ops | MCP | 8100 | file_ops |
| sandbox | MCP | 8101 | sandbox |
| todo | MCP | 8102 | todo |
| format_conversion | MCP | 8103 | format_conversion |
| data_viz | MCP | 8104 | data_viz |
| repl | MCP | 8105 | repl |
| vocabulary | MCP | 8106 | vocabulary |
| data_analysis | MCP | 8010 | data_analysis |
| sql | MCP | 8011 | sql |
| nl2sql | A2A | 8200 | nl2sql |
| data_analysis | A2A | 8201 | data_analysis |
| vocabulary | A2A | 8202 | vocabulary |

## Dependencies

A2A servers depend on MCP servers being available:
- A2A nl2sql (8200) -> MCP sql (8011)
- A2A data_analysis (8201) -> MCP data_analysis (8010), data_viz (8104), file_ops (8100), repl (8105)
- A2A vocabulary (8202) -> MCP vocabulary (8106)
