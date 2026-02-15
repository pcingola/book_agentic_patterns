# Domain Agents

Domain agents (`agentic_patterns.agents`) are pre-configured agents for specific tasks. Each module exposes a `create_agent()` factory returning a PydanticAI `Agent` and optionally a `get_spec()` factory returning an `AgentSpec` for composition via `OrchestratorAgent`.

## db_catalog

`create_agent()` returns an agent with `output_type=DatabaseSelection` (a Pydantic model with `database` and `reasoning` fields). Given a natural language query, the agent inspects all available database schemas and selects the most appropriate one. Used as a routing step before NL2SQL.

## data_analysis

`create_agent()` returns an agent with file, CSV, JSON, data analysis, data visualization, and REPL tools directly attached.

`get_spec()` returns an `AgentSpec` with `name="data_analyst"`, a system prompt, and the same tool set. This spec can be registered as a sub-agent in an `OrchestratorAgent`.

## nl2sql

`create_agent(db_id: str)` returns an agent bound to a specific database. It loads a system prompt and database-specific instructions (schema, example queries, dialect-specific rules) via `get_system_prompt()` and `get_instructions()`. Tools are created with `get_all_tools(db_id)`, which binds a `SqlConnector` to the given database via closure, exposing `db_execute_sql_tool` and `db_get_row_by_id_tool`. Both tools raise `ModelRetry` on validation errors so the agent can self-correct.

## openapi

`create_agent()` returns an agent with OpenAPI tools for discovering and calling REST APIs.

`get_spec()` returns an `AgentSpec` with `name="api_specialist"`.

## sql

`create_agent()` returns an agent with file, CSV, and SQL tools.

`get_spec()` returns an `AgentSpec` with `name="sql_analyst"` for sub-agent composition.

## vocabulary

`create_agent(vocab_names: list[str] | None = None)` returns an agent for resolving terms across controlled vocabularies (biomedical, scientific). The optional `vocab_names` parameter filters which vocabularies are available.

`get_spec(vocab_names)` returns an `AgentSpec` with `name="vocabulary_expert"`, a system prompt listing available vocabularies with their strategies and term counts, and vocabulary tools: `vocab_lookup`, `vocab_search`, `vocab_validate`, `vocab_suggest`, `vocab_parent`, `vocab_children`, `vocab_ancestors`, `vocab_descendants`, `vocab_relationships`, `vocab_related`, `vocab_info`, `vocab_list`.

## coordinator

`create_agent(tools=None)` returns an `OrchestratorAgent` that delegates work to sub-agents (data_analysis, sql, vocabulary). It uses `AgentSpec` with `name="coordinator"`, a system prompt loaded from a template, optional direct tools, and sub-agent specs registered for delegation via `TaskBroker`.
