# agentic_patterns

Documentation for the `agentic_patterns` library -- a Python library for building AI agents using PydanticAI.

## Getting Started

[Foundations](agentic_patterns/foundations.md) -- Agent creation, model configuration, execution, multi-turn conversations, system prompts, environment setup, authentication, and user sessions.

## Core

[Tools](agentic_patterns/tools.md) -- Tool definition, structured outputs, tool selection, permissions, workspace isolation, context result decorator, built-in tool wrappers, and dynamic tool generation.

[Context & Memory](agentic_patterns/context_memory.md) -- Prompt templates with includes and variable substitution, context processing pipeline (file type detection, truncation, processors), and history compaction.

[RAG](agentic_patterns/rag.md) -- Embeddings, vector database, document ingestion, similarity search, and advanced retrieval techniques.

## Data Access

[Connectors](agentic_patterns/connectors.md) -- FileConnector, CsvConnector, JsonConnector, connector base, and connector chaining through the workspace.

[SQL](agentic_patterns/sql.md) -- SQL connector, schema discovery, query validation, schema annotation pipeline, and NL2SQL agent.

[OpenAPI](agentic_patterns/openapi.md) -- OpenAPI 3.x connector, spec ingestion, endpoint discovery, and HTTP request execution.

[Vocabulary](agentic_patterns/vocabulary.md) -- Vocabulary connector with three resolution strategies (enum, tree, RAG), term validation, and hierarchy navigation.

[Toolkits](agentic_patterns/toolkits.md) -- Pure Python business logic: todo management, data analysis, data visualization, and format conversion.

## Agent Capabilities

[MCP](agentic_patterns/mcp.md) -- MCP server creation, client configuration, error classification, authentication middleware, and network isolation.

[A2A](agentic_patterns/a2a.md) -- A2A server exposure, client configuration, coordinator pattern, delegation tools, skill conversion, and testing with MockA2AServer.

## Composition

[Skills, Sub-Agents & Tasks](agentic_patterns/skills_sub_agents_tasks.md) -- Sub-agent delegation (fixed and dynamic), skill registry with progressive disclosure, task broker for background execution, OrchestratorAgent, and AgentSpec.

[Domain Agents](agentic_patterns/domain_agents.md) -- Pre-configured agents: db_catalog, data_analysis, sql, openapi, and coordinator.

## Quality & Testing

[Evals](agentic_patterns/evals.md) -- Deterministic testing (ModelMock, tool_mock), evaluation framework with custom evaluators and auto-discovery, and doctors CLI for artifact quality analysis.

## Production

[Execution Infrastructure](agentic_patterns/execution_infrastructure.md) -- Process sandbox, Docker container sandbox, stateful REPL, MCP server isolation, and skill sandboxing.

[Compliance](agentic_patterns/compliance.md) -- Data sensitivity levels, private data tagging, permission enforcement, and network isolation driven by compliance flags.

[User Interface](agentic_patterns/ui.md) -- Authentication, Chainlit integration, AG-UI protocol, state management, feedback persistence, and file uploads.
