# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the repository for the book "Agentic Patterns". The book targets software engineers and ML practitioners who want to build agentic systems. It combines theoretical foundations with hands-on implementation, moving from foundational reasoning patterns (CoT, ReAct) through tool use, orchestration, and multi-agent protocols (MCP, A2A) to evaluation and production infrastructure. All code uses PydanticAI. The book is written in markdown with each chapter in its own directory.

**GOAL**: Build a proof-of-concept agentic platform using established patterns and best practices -- not a full enterprise system, but one that teaches the architectural principles needed to design, implement, test, and operate AI agent systems that can evolve into production-ready solutions.

## Repository Structure

```
book_agentic_patterns/
├── chapters/           # Book chapters (markdown files)
├── agentic_patterns/   # Python code examples and core library
│   ├── core/          # Reusable infrastructure
│   ├── examples/      # Code examples by chapter
│   └── testing/       # Testing utilities for agents
├── scripts/            # Build, validation, lint scripts
├── tests/              # Tests for code examples
│   ├── unit/          # Unit tests
│   └── integration/   # Integration tests
├── prompts/            # Prompt templates (markdown files)
├── data/               # Runtime data (db/, workspaces/)
├── docs/               # Design documents
└── output/             # Generated book output (book.md, PDF)
```

## Conventions

**Chapter directories**: All chapters under `chapters/` directory. Name them with descriptive names (e.g., `foundations`, `core_patterns`, `tools`). Each chapter directory contains a `chapter.md` index file that links to individual section markdown files. Images stored in `img/` subdirectory within each chapter.

**Code organization**: All code in `agentic_patterns/`. Code examples are organized under `agentic_patterns/examples/` in directories that correspond to chapters (e.g., `foundations`, `core_patterns`, `tools`). Code examples may be Python files (.py) or Jupyter notebooks (.ipynb). Core utilities shared across chapters go in `agentic_patterns/core/`. Follow global Python conventions (type hints, pathlib, etc.).

## Core Library (`agentic_patterns/core/`)

The core library provides reusable infrastructure for building AI agentic systems with PydanticAI.

### Module Structure

**agents/**: Agent instantiation and execution using PydanticAI. `get_agent()` creates agents from YAML-based model configurations with configurable timeout, parallel tool calls, and optional history compaction. `run_agent()` executes agents with step-by-step logging and MCP context integration. Supports five LLM providers via match/case dispatch: Azure OpenAI, AWS Bedrock (with 1M token context for Claude), Ollama, OpenAI, and OpenRouter. Provider-specific config classes in `config.py`, model creation in `models.py`, utilities in `utils.py`. Also contains domain-specific agents: `orchestrator.py` for agent orchestration, `db_catalog.py` for database selection, `vocabulary.py` for vocabulary operations, and `nl2sql/` sub-package for NL2SQL agents with database-bound tools via closure pattern.

**config/**: Environment and project configuration with smart discovery. `AGENTIC_PATTERNS_PROJECT_DIR` points to core library location while `MAIN_PROJECT_DIR` adapts when core is a package in another project. Provides derived paths: SCRIPTS_DIR, DATA_DIR, DATA_DB_DIR, LOGS_DIR, PROMPTS_DIR, WORKSPACE_DIR. Environment loading (`env.py`) searches multiple directories for `.env` files with fallback strategy.

**context/**: Multi-layered context management for handling large files, history compaction, and result truncation. `reader.py` detects file types (code, markdown, text, documents, spreadsheets, JSON, YAML, XML, CSV, images, audio, archives, PDF, PPTX, DOCX) and dispatches to specialized processors. `history.py` provides `HistoryCompactor` for conversation history management with token-based summarization when approaching context limits, maintaining tool call/return pairing constraint. `decorators.py` offers `@context_result()` for tools returning large results, saving full content to workspace while returning truncated previews. Processors in `processors/` handle type-specific truncation: text, code, JSON, CSV, XML, YAML, documents, spreadsheets, images. Configuration via `ContextConfig` with limits for file processing, structured data, tabular data, history compaction, and truncation presets (default, sql_query, log_search).

**vectordb/**: Embedding and vector database integration for semantic search. Supports four embedding providers (OpenAI, Ollama, SentenceTransformers, OpenRouter) with Chroma as the vector DB backend. `get_embedder()` and `get_vector_db()` use factory pattern with singleton caching. `PydanticAIEmbeddingFunction` wraps embedders for Chroma compatibility. Operations include `vdb_add()`, `vdb_query()` for similarity search, and `vdb_get_by_id()`. Configuration loaded from YAML with environment variable expansion.

**tools/**: Tool management with permissions and AI-driven selection. `ToolPermission` enum (READ, WRITE, CONNECT) with `@tool_permission()` decorator for metadata attachment. `filter_tools_by_permission()` and `enforce_tool_permission()` for runtime permission enforcement. `ToolSelector` uses an agent to select relevant tools based on user query. `func_to_description()` generates tool descriptions from function signatures and docstrings. `nl2sql.py` provides NL2SQL-specific tool utilities. `openapi.py` provides five OpenAPI connector tools (list_apis, list_endpoints, show_api_summary, show_endpoint_details, call_endpoint).

**evals/**: Evaluation framework for testing agent behavior. CLI via `python -m agentic_patterns.core.evals`. Auto-discovery of `eval_*.py` files with convention-based dataset/target/scorer detection. Custom evaluators: `OutputContainsJson` (validate JSON output), `ToolWasCalled` (verify tool execution), `NoToolErrors` (check for failures), `OutputMatchesSchema` (schema validation). `DiscoveredDataset` bundles dataset + target + scorers with filtering by module/file/dataset name.

**doctors/**: CLI tools for AI-powered analysis of prompts, tools, MCP servers, A2A agent cards, and Agent Skills. Run via `doctors` command (after `uv pip install -e .`) or `python -m agentic_patterns.core.doctors`. Subcommands: `prompt` (analyze prompt files), `tool` (analyze Python tool functions), `mcp` (analyze MCP server tools), `a2a` (analyze agent cards), `skill` (analyze agentskills.io format). Each doctor uses an LLM to evaluate quality and returns recommendations with issue levels.

**connectors/**: Data source connectors used by agents to interact with external data. Connectors are an abstraction layer independent from tools -- agents call connector methods, which are then exposed as tools. Connectors MUST manage context to prevent the agent's context window from filling up when operations return large results (e.g. a SQL query returning a big table); they use truncation, pagination, and the `@context_result()` decorator to keep responses within safe limits. Base class in `base.py`. `FileConnector` (file.py) provides read, write, append, delete, edit, find, head, tail, list operations. `CsvConnector` (csv.py) provides append, delete, query, read with auto-delimiter detection. `JsonConnector` (json.py) provides JSONPath-based read/write with structure truncation. All connectors use static methods, `@tool_permission()` decorators (READ/WRITE), and workspace sandbox isolation via `workspace_to_host_path()`. **Vocabulary sub-connector** (`connectors/vocabulary/`): `VocabularyConnector` provides term resolution across controlled vocabularies and ontologies. Three resolution strategies based on vocabulary size: `StrategyEnum` (< 100 terms), `StrategyTree` (< 1K terms, BFS/DFS traversal), `StrategyRag` (1K+ terms, vector DB semantic search). Supports multiple vocabulary formats via parsers: OBO, OWL, RF2, tabular. `registry.py` manages vocabulary registration and routing. Config reads from `vocabularies.yaml`. **SQL sub-connector** (`connectors/sql/`): Pydantic data models for schema metadata (`DbInfo`, `TableInfo`, `ColumnInfo`, `ForeignKeyInfo`, `IndexInfo`), abstract + SQLite implementations for connections and operations (`sqlite/` subdirectory), schema inspection (`inspection/` with abstract + SQLite implementations), schema extraction with JSON caching, query validation (SELECT-only, single statement), schema SQL formatting (`SchemaFormatter`), singleton registries (`DbConnectionConfigs`, `DbInfos`), factory functions with match/case dispatch on `DatabaseType`. Configuration reads from `dbs.yaml`. Schema annotation pipeline (`annotation/`) with AI-powered descriptions, enum detection, and example query generation. CLI tools in `cli/`. Prompt templates in `prompts/sql/`. Architecture supports adding Postgres via new subdirectories and factory match/case branches. Note: NL2SQL and db_catalog agents live in `agents/`, not here. **OpenAPI sub-connector** (`connectors/openapi/`): Allows agents to interact with REST APIs by ingesting OpenAPI 3.x specs. Layered architecture: Configuration (`apis.yaml` with `${VAR}` expansion, `ApiConnectionConfig` registry) -> Extraction (`ApiSpecExtractor` fetches specs from URL/file, `OpenApiV3Parser` parses endpoints with `$ref` resolution) -> Annotation (`ApiSpecAnnotator` uses LLM to generate descriptions, categorize endpoints, create example curls; prompts in `prompts/openapi/annotation/`) -> Connector (`OpenApiConnector` with `list_apis`, `list_endpoints`, `show_api_summary`, `show_endpoint_details`, `call_endpoint`; uses `@context_result()` for large responses) -> Tools (`tools/openapi.py` exposes five tools with READ/CONNECT permissions). Data models: `ApiInfo`, `EndpointInfo`, `ParameterInfo`, `RequestSchemaInfo`, `ResponseSchemaInfo` (dataclasses with serialization). HTTP client: `RequestsApiClient` with retry and timeout. `ApiInfos` singleton registry with lazy init from cached JSON. CLI: `python -m agentic_patterns.core.connectors.openapi.cli.ingest <api_id>`. Config `base_url` overrides spec servers for environment-specific deployments. Current limitations: OpenAPI 3.x only (no Swagger 2.0), no authentication, no rate limiting.

**auth.py**: JWT token generation and validation for cross-layer identity propagation. `create_token(user_id, session_id)` encodes claims with HS256 shared secret. `decode_token(token)` validates and returns claims. Secret and algorithm read from `JWT_SECRET` / `JWT_ALGORITHM` env vars in `config.py`.

**mcp.py**: MCP client/server configuration and auth integration. `MCPClientConfig` and `MCPServerConfig` with YAML-based settings loading and `${VAR}` environment variable expansion. Supports both HTTP and stdio transports. `get_mcp_client()` accepts optional `bearer_token` to inject Authorization headers. `create_process_tool_call(get_token)` factory returns a callback that injects Bearer tokens into MCP tool calls (bridges PydanticAI RunContext to MCP). `AuthSessionMiddleware` (FastMCP Middleware) reads access token claims on each request and calls `set_user_session()` so downstream code works unchanged.

**skills/**: Skill library for agent capabilities with progressive disclosure pattern. `models.py` defines `SkillMetadata` (lightweight info: name, description, path) and `Skill` (full skill with frontmatter, body, script/reference/asset paths). `registry.py` provides `SkillRegistry` with `discover()` to scan skill directories and cache metadata (cheap), `list_all()` to return cached metadata for system prompt injection, and `get()` to lazy-load full skill on activation (expensive). Skills are defined in directories containing a `SKILL.md` file with YAML frontmatter (name, description) and markdown body. Optional `scripts/`, `references/`, and `assets/` subdirectories hold supporting files. `tools.py` exposes `list_available_skills()` for compact one-liner listings and `get_skill_instructions()` for returning the SKILL.md body only (per spec, resources are tier 3 and loaded separately).

**a2a/**: Agent-to-Agent protocol integration. `client.py` provides `A2AClientExtended` with polling, retry, timeout, and cancellation support; `send_and_observe()` sends messages and polls until terminal state, returning `TaskStatus` (COMPLETED, FAILED, INPUT_REQUIRED, CANCELLED, TIMEOUT). `config.py` has `A2AClientConfig` (with optional `bearer_token` for injecting Authorization headers on the underlying httpx client) and YAML-based settings loading. `coordinator.py` provides `create_coordinator()` async factory that takes A2A clients, fetches their agent cards, creates delegation tools, and returns a configured coordinator agent. `tool.py` has `create_a2a_tool(client, card)` to create PydanticAI tools for delegation (returns formatted strings like `[COMPLETED] result` or `[INPUT_REQUIRED:task_id=X] question`), and `build_coordinator_prompt(cards)` to generate system prompts. `mock.py` provides `MockA2AServer` for testing without LLM calls: configure responses with `on_prompt(prompt, result=...)` or `on_pattern(regex, input_required=...)`, use `set_default(result)` for fallback responses, use `on_prompt_delayed(prompt, polls, result=...)` for delayed responses that return working state until N polls complete, and call `to_app()` to get a FastAPI instance. Check `received_prompts` and `cancelled_task_ids` for assertions.

**repl/**: REPL (Read-Eval-Print Loop) engine for executing Python code iteratively in a stateful, process-isolated environment. Jupyter-like notebook model where cells share a namespace across executions. `notebook.py` manages cell lifecycle, persistence (JSON), import/function tracking, and ipynb export. `cell.py` delegates execution to `sandbox.py`, which uses pickle-based IPC: writes input (code, namespace, imports, funcdefs) to a temp dir, runs `executor.py` inside the generic `core/sandbox.py`, reads back a `SubprocessResult`. `executor.py` is a standalone `__main__` script that restores workbook references, configures matplotlib, replays imports and function definitions, executes cell code, captures stdout/stderr/figures, filters namespace to picklable objects, and writes output. `cell_utils.py` provides `SubprocessResult`, picklability filtering with helpful hints for common unpicklable types, function definition extraction via AST, and last-expression capture. `openpyxl_handler.py` serializes openpyxl Workbook objects across process boundaries via temp files (`WorkbookReference`). `matplotlib_backend.py` configures non-interactive Agg backend and captures figures. `image.py` has `Image` (binary data) and `ImageReference` (resource URI) models. `cell_output.py` wraps outputs with type/timestamp/serialization. `api_models.py` provides `CellInfo`, `NotebookInfo`, `OperationResult` for API layers. `enums.py` has `CellState` and `OutputType`. `config.py` has `DEFAULT_CELL_TIMEOUT`, `MAX_CELLS`, `SERVICE_NAME`. Notebook persistence at `WORKSPACE_DIR / user_id / session_id / mcp_repl / cells.json`.

**sandbox.py**: Generic sandbox for running commands in isolated environments, independent of the REPL. `BindMount(source, target, readonly)` dataclass for filesystem mounts. `SandboxResult(exit_code, stdout, stderr, timed_out)` dataclass for command output. `Sandbox` ABC with `async run(command, timeout, bind_mounts, isolate_network, isolate_pid, cwd, env) -> SandboxResult`. Two implementations: `SandboxBubblewrap` (Linux production, builds bwrap command with read-only system mounts, user-specified bind mounts, optional `--unshare-net` and `--unshare-pid`, auto-binds Python prefix for package access) and `SandboxSubprocess` (macOS/dev fallback, runs command as plain subprocess with no isolation). `get_sandbox()` factory returns bwrap if available on PATH. Used by `repl/sandbox.py` for REPL execution; can be reused by any module needing process-isolated command execution (tool runners, script evaluators, etc.).

**prompt.py**: Template-based prompt loading from markdown files. `load_prompt()` extracts `{variable_name}` patterns, validates all required variables are provided, and raises ValueError for missing/unused variables. Helper functions: `get_system_prompt()`, `get_prompt()`, `get_instructions()`.

**user_session.py**: User and session context via contextvars. `set_user_session(user_id, session_id)` sets context at request boundary. `get_user_id()` / `get_session_id()` read from contextvars. `set_user_session_from_token(token)` decodes a JWT and calls `set_user_session()` -- convenience for A2A servers and non-FastMCP entry points receiving raw token strings.

**workspace.py**: Sandbox workspace isolation for multi-tenant scenarios. `workspace_to_host_path()` and `host_to_workspace_path()` translate between agent-visible paths (`/workspace/...`) and host filesystem paths with traversal protection. File operations: `read_from_workspace()`, `write_to_workspace()`, `store_result()`.

**utils.py**: General utilities shared across core modules.

### Key Patterns

The library uses async-first design with sync wrappers, Pydantic models for configuration validation, factory pattern with singleton caching for models/embedders/vector DBs, extensive match/case for provider dispatch, decorator-based composition for permissions and result truncation, and context-aware request handling (user_id, session_id) for multi-tenant isolation. Token counting via tiktoken with char-count fallback for graceful degradation.

## Testing Utilities (`agentic_patterns/testing/`)

Mock utilities for deterministic agent testing without API calls. `AgentMock` replays recorded agent nodes. `AgentRunMock` provides mock agent run iterator with `MockResult`. `ModelMock` for LLM model mocking with `MockFinishReason`. `ToolMockWrapper` and `tool_mock()` decorator for tool function mocking. `final_result_tool()` and `FINAL_RESULT_TOOL_NAME` for structured completion testing.

## Examples (`agentic_patterns/examples/`)

Code examples organized by chapter (Jupyter notebooks and Python scripts):

- `foundations/` - Basic agents, multi-turn conversations
- `core_patterns/` - ReAct, CoT, ToT, CodeAct, self-reflection, verification, planning, human-in-loop
- `tools/` - Tool use, permissions, workspace, structured outputs, tool selection
- `context_memory/` - Context result decorator, history compaction, prompts
- `orchestration/` - Delegation, workflows, graphs, hand-off
- `rag/` - Document loading, querying, embeddings
- `mcp/` - MCP client (HTTP/stdio), MCP servers, features
- `a2a/` - A2A servers and clients (v1, v2)
- `evals/` - Evaluation examples, doctors analysis, skills (skill-bad, skill-good subdirectories)
- `connectors/` - JSON connector, SQL connector, NL2SQL agent examples
- `sub_agents/` - Sub-agent examples
- `skills/` - Skills examples with SKILL.md definitions

## Chapters

Chapters in `chapters/`: foundations, core_patterns, tools, context_memory, orchestration, rag, mcp, a2a, skills_and_sub_agents, evals, execution_infrastructure, data_sources_and_connectors. Each contains `chapter.md` index linking to section files and hands-on exercises. Master index in `chapters.md` at root.

## Scripts

All scripts in `scripts/` follow the `config.sh` pattern (sets PROJECT_DIR, loads .env, activates .venv, sets PYTHONPATH):

- `config.sh` - Common setup for all scripts
- `make.sh` - Compiles chapters to output/book.md with optional PDF
- `test.sh` - Runs all tests (test_unit.sh + test_integration.sh)
- `test_unit.sh` - Runs pytest on tests/unit/
- `test_integration.sh` - Runs pytest on tests/integration/
- `evals.sh` - Runs evaluations
- `lint.sh` - Runs linter
- `db_ingest_bookstore_sqlite.sh` - Creates bookstore SQLite DB from SQL files in tests/data/sql/
- `annotate_schema.sh` - Runs AI schema annotation pipeline
- `download_vocabularies.sh` - Downloads vocabulary resources
- `make.py` - Python utility for book compilation
- `fix_references.py` - Reference fixing utility

## Configuration

**config.yaml**: Model configurations with named entries (default, fast, azure_gpt4, bedrock_claude, bedrock_claude_extended, ollama_local, openrouter_claude). Each model config includes model_family, model_name, provider-specific credentials, timeout, optional parallel_tool_calls.

**pyproject.toml**: Project metadata and dependencies. Key packages: pydantic-ai (>=1.39.0), chromadb (>=1.4.1), openai (>=2.14.0), fastmcp (>=2.14.2), fasta2a (>=0.6.0), pyjwt (>=2.9.0), requests (>=2.32.0), jsonpath-ng, pyyaml, dotenv, ipykernel. Console script: `doctors`.

**apis.yaml**: OpenAPI connector configuration. Defines API specs with `id`, `name`, `spec_url` (URL or file path), and optional `base_url` override. Supports `${VAR}` environment variable expansion.

## Reference Documentation (`docs/`)

The `docs/` directory contains reference documentation for the key technologies used in this project. Consult these when working on related topics.

`docs/pydantic-ai.md` -- PydanticAI framework: agents, dependencies, tools, model providers, graphs, evals, MCP integration. This is the primary AI framework used throughout the project.

`docs/mcp.md` -- Model Context Protocol (MCP) specification: architecture, clients/servers, SDKs, tools, prompts, resources, sampling, security, registry publishing.

`docs/fastmcp.md` -- FastMCP 3.0 (Python MCP library): server implementation, client usage, middleware, authentication, deployment, CLI, and service integrations.

`docs/a2a_specification.md` -- Agent-to-Agent (A2A) Protocol v1.0 RC: agent discovery, protocol operations, data models, JSON-RPC/gRPC/HTTP bindings, security, and relationship to MCP.

`docs/agui.md` -- AG-UI (Agent-User Interaction) Protocol: event-based protocol for connecting AI agents to user-facing applications. Covers concepts (agents, architecture, events, messages, middleware, serialization, state, tools), SDK references (JavaScript and Python), quickstart guides, and draft proposals.

`docs/mcp_template.md` -- Design guide for building production FastMCP servers: component architecture, tool registration, workspace/session isolation, large data handling, middleware, authentication, Docker setup.

`docs/mcp_sql.md` -- Design document for the NL2SQL MCP system: five-layer architecture, schema extraction, AI-powered enum detection, NL2SQL agents, database-agnostic design, security patterns.

`docs/mcp_repl.md` -- Design document for MCP REPL (Jupyter-like notebook as MCP server): process isolation, namespace serialization, state persistence, async execution, session management.

`docs/skills_specification.md` -- Agent Skills specification: overview, integration approaches, SKILL.md format, directory structure, progressive disclosure, validation.

Each index file (`*.md`) links to detailed section files in corresponding subdirectories (`a2a_specification/`, `agui/`, `fastmcp/`, `mcp/`, `pydantic-ai/`, `skills_specification/`). Original unprocessed source files are in `docs/original/`.

## Additional Conventions

**Tests**: In `tests/` directory at root with `unit/` and `integration/` subdirectories. Run via `scripts/test.sh` (uses pytest).

**Code imports**: When code in `agentic_patterns/examples/<chapter>/` imports from `agentic_patterns/core/`, ensure PYTHONPATH is set correctly (scripts/config.sh handles this).

**Prompts**: Store prompt templates in `prompts/` directory as markdown files. Use `load_prompt()` from `core/prompt.py` to load with variable substitution.

**Image optimization**: Use compressed PNGs or SVGs for diagrams. Large images bloat git history permanently.

**References**: All references and citations should be included in a `references.md` file.
