# Plan: OpenAPI -- MCP Server, A2A Server, Sub-Agent, Complete Agent Integration

## Context

The OpenAPI connector (`core/connectors/openapi/`) and PydanticAI tool wrappers (`tools/openapi.py`) already exist. They provide five operations: list_apis, list_endpoints, show_api_summary, show_endpoint_details, call_endpoint. What's missing is the MCP server, A2A server, and sub-agent layers -- plus wiring them into The Complete Agent (monolithic and infrastructure variants).

## Step 1: MCP Server -- `agentic_patterns/mcp/openapi/`

Follow the SQL MCP server pattern (`mcp/sql/`).

**`server.py`** (~10 lines):
- `create_mcp_server("openapi", instructions="...")`
- `register_tools(mcp)`

**`tools.py`** (~60 lines):
- Instantiate `OpenApiConnector()` once at module level
- `_RETRYABLE = (ValueError, KeyError)` for user-correctable errors
- `_call(coro)` async helper converting exceptions to `ToolRetryError` / `ToolFatalError`
- Register 5 tools via `register_tools(mcp)`:
  - `openapi_list_apis` -- CONNECT permission
  - `openapi_list_endpoints(api_id, category)` -- READ permission
  - `openapi_show_api_summary(api_id)` -- READ permission
  - `openapi_show_endpoint_details(api_id, method, path)` -- READ permission
  - `openapi_call_endpoint(api_id, method, path, parameters, body, output_file)` -- CONNECT permission
- Each tool logs via `await ctx.info()`
- No `__init__.py` needed (matches existing MCP servers)

Reference files:
- `agentic_patterns/mcp/sql/server.py` (server pattern)
- `agentic_patterns/mcp/sql/tools.py` (tools pattern with `_call()` helper)
- `agentic_patterns/core/connectors/openapi/connector.py` (connector methods to wrap)

## Step 2: System Prompt -- `prompts/a2a/openapi/system_prompt.md`

Create a prompt for both the A2A server and the sub-agent (they share the same prompt, following the nl2sql/data_analysis pattern).

Content: describe the agent as an API integration specialist, list the 5 available tools, provide a workflow (list APIs -> inspect endpoints -> call endpoints), mention that results are saved to workspace.

Reference files:
- `prompts/a2a/nl2sql/system_prompt.md` (structure and length)
- `prompts/a2a/vocabulary/system_prompt.md` (single-domain pattern)

## Step 3: Sub-Agent -- `agentic_patterns/agents/openapi.py`

Follow the `agents/sql.py` pattern (simplest: single connector, one tool set).

- `DESCRIPTION = "Delegates API exploration and execution tasks across configured REST APIs."`
- `create_agent()` creates agent from spec
- `get_spec()` returns `AgentSpec(name="api_specialist", description=DESCRIPTION, system_prompt=prompt, tools=openapi.get_all_tools())`
- Load prompt from `prompts/a2a/openapi/system_prompt.md` via `load_prompt()`

Reference files:
- `agentic_patterns/agents/sql.py` (exact same pattern)
- `agentic_patterns/tools/openapi.py` (existing tools to use)

## Step 4: A2A Server -- `agentic_patterns/a2a/openapi/server.py`

Follow the vocabulary A2A pattern (single MCP server, simple delegation).

- Load prompt from `prompts/a2a/openapi/system_prompt.md`
- `get_mcp_client("openapi")` for the MCP toolset
- `mcp_to_skills_sync("openapi")` for skills
- `get_agent(toolsets=[mcp_client], instructions=system_prompt)`
- `agent.to_a2a(name="ApiSpecialist", description="...", skills=skills)`
- `app.add_middleware(AuthSessionMiddleware)`

Reference files:
- `agentic_patterns/a2a/vocabulary/server.py` (exact same pattern)
- `agentic_patterns/a2a/nl2sql/server.py` (same pattern)

## Step 5: Config -- `config.yaml`

Add three entries:

**MCP server client** (in `mcp_servers` section):
```yaml
openapi:
  type: client
  url: http://localhost:8107/mcp
  read_timeout: 120
```

**A2A client** (in `a2a.clients` section):
```yaml
openapi:
  url: http://localhost:8203
  timeout: 300
```

**Agent specs** -- add OpenAPI sub-agent to `coordinator`, `full_agent`, and `infrastructure_agent`:
- `coordinator.sub_agents` and `full_agent.sub_agents`: append `agentic_patterns.agents.openapi:get_spec`
- `infrastructure_agent.a2a_clients`: append `openapi`

## Step 6: Launch Script -- `scripts/launch_infrastructure.sh`

Add:
- `start_mcp openapi 8107` (after vocabulary, port 8106)
- Add port 8107 to `MCP_PORTS` array
- `start_a2a openapi 8203` (after vocabulary, port 8202)

## Step 7: Prompts -- Update Complete Agent Prompts

**`prompts/the_complete_agent/agent_full.md`**: Add mention of the new "api_specialist" sub-agent for REST API tasks alongside the existing mentions of data analysis, SQL, and vocabulary delegation.

**`prompts/the_complete_agent/agent_infrastructure.md`**: Same -- mention that API exploration/execution should be delegated to the OpenAPI A2A agent.

**`prompts/the_complete_agent/agent_coordinator.md`**: Same update (coordinator also uses sub-agents).

## Files to Create (5)

1. `agentic_patterns/mcp/openapi/server.py`
2. `agentic_patterns/mcp/openapi/tools.py`
3. `agentic_patterns/a2a/openapi/server.py`
4. `agentic_patterns/agents/openapi.py`
5. `prompts/a2a/openapi/system_prompt.md`

## Files to Edit (5)

1. `config.yaml` -- add MCP client, A2A client, update agent specs
2. `scripts/launch_infrastructure.sh` -- add MCP + A2A startup
3. `prompts/the_complete_agent/agent_full.md` -- mention API sub-agent
4. `prompts/the_complete_agent/agent_infrastructure.md` -- mention API A2A agent
5. `prompts/the_complete_agent/agent_coordinator.md` -- mention API sub-agent

## Verification

1. Syntax check: `python -c "from agentic_patterns.mcp.openapi.server import mcp"`
2. Syntax check: `python -c "from agentic_patterns.a2a.openapi.server import app"`
3. Syntax check: `python -c "from agentic_patterns.agents.openapi import get_spec; print(get_spec())"`
4. Config validation: verify `config.yaml` parses correctly
5. Lint: `scripts/lint.sh`
