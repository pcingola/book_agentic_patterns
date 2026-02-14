# Domain Agents

Domain agents (`agentic_patterns.agents`) are pre-configured agents for specific tasks. Each module exposes a `create_agent()` factory returning a PydanticAI `Agent` and optionally a `get_spec()` factory returning an `AgentSpec` for composition via `OrchestratorAgent`.

## db_catalog

`create_agent()` returns an agent with `output_type=DatabaseSelection` (a Pydantic model with `database` and `reasoning` fields). Given a natural language query, the agent inspects all available database schemas and selects the most appropriate one. Used as a routing step before NL2SQL.

## data_analysis

`create_agent()` returns an agent with file, CSV, JSON, data analysis, data visualization, and REPL tools directly attached.

`get_spec()` returns an `AgentSpec` with `name="data_analyst"`, a system prompt, and the same tool set. This spec can be registered as a sub-agent in an `OrchestratorAgent`.

## sql

`create_agent()` returns an agent with file, CSV, and SQL tools.

`get_spec()` returns an `AgentSpec` with `name="sql_analyst"` for sub-agent composition.

## openapi

`create_agent()` returns an agent with OpenAPI tools for discovering and calling REST APIs.

`get_spec()` returns an `AgentSpec` with `name="api_specialist"`.

## coordinator

`create_agent(tools=None)` returns an `OrchestratorAgent` that delegates work to sub-agents (data_analysis, sql, vocabulary). It uses `AgentSpec` with `name="coordinator"`, a system prompt loaded from a template, optional direct tools, and sub-agent specs registered for delegation via `TaskBroker`.
