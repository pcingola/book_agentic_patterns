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
│   ├── agents/        # Domain-specific agents (db_catalog, vocabulary, nl2sql, etc.)
│   ├── toolkits/      # Business logic (no framework dependency)
│   ├── tools/         # PydanticAI agent tool wrappers
│   ├── mcp/           # MCP server thin wrappers
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

**agents/**: Agent infrastructure only -- instantiation and execution using PydanticAI. `get_agent()` creates agents from YAML-based model configurations with configurable timeout, parallel tool calls, and optional history compaction. `run_agent()` executes agents with step-by-step logging and MCP context integration. Supports five LLM providers via match/case dispatch: Azure OpenAI, AWS Bedrock (with 1M token context for Claude), Ollama, OpenAI, and OpenRouter. Provider-specific config classes in `config.py`, model creation in `models.py`, utilities in `utils.py`. `orchestrator.py` provides `OrchestratorAgent` and `AgentSpec` for full agent composition with tools, MCP, A2A, skills, sub-agents, and tasks. `AgentSpec` is a declarative dataclass with optional `model` (defaults to `None`, resolved to default config by `get_agent()`), optional `system_prompt_path` for template-based prompts with variable substitution, and `from_config()` class method to load everything from YAML. `OrchestratorAgent` is an async context manager that wires up six capabilities: tools (direct), MCP servers, A2A clients (delegation tools), skills (auto-discovery with `activate_skill` tool), sub-agents (via TaskBroker with `delegate`/`submit_task`/`wait` tools), and tasks (event-driven coordination). It owns the iteration loop, stores run history in `.runs`, accumulates message history across turns, injects completed background task results between turns via `_inject_completed_tasks()`, and `run()` returns `AgentRunResult` directly. Supports a `NodeHook` callback (`on_node`) for observing graph nodes during execution; `verbose=True` activates the default hook `_log_node` which prints model reasoning (dimmed) and tool calls (name + first arg). Domain-specific agents live in top-level `agentic_patterns/agents/`, not here.

**config/**: Environment and project configuration with smart discovery. `AGENTIC_PATTERNS_PROJECT_DIR` points to core library location while `MAIN_PROJECT_DIR` adapts when core is a package in another project. Provides derived paths: SCRIPTS_DIR, DATA_DIR, DATA_DB_DIR, LOGS_DIR, PROMPTS_DIR, WORKSPACE_DIR, PRIVATE_DATA_DIR, FEEDBACK_DIR, USER_DATABASE_FILE. Environment loading (`env.py`) searches multiple directories for `.env` files with fallback strategy.

**compliance/**: Private data management for agent sessions. `DataSensitivity` enum (PUBLIC, INTERNAL, CONFIDENTIAL, SECRET) defines sensitivity levels. `PrivateData` tracks private datasets per session, persisted as `.private_data` JSON in PRIVATE_DATA_DIR (outside the agent's workspace so the agent cannot tamper with it). When the flag is set, downstream guardrails can block tools that would leak data (external APIs, outbound MCP servers). Helper functions: `mark_session_private()`, `session_has_private_data()`. Integrates with `sandbox/` for network isolation enforcement.

**context/**: Multi-layered context management for handling large files, history compaction, and result truncation. `models.py` defines `FileType` enum (19 types), `TruncationInfo`, `FileMetadata`, `BinaryContent`, `FileExtractionResult` dataclasses. `reader.py` detects file types and dispatches to specialized processors. `history.py` provides `HistoryCompactor` for conversation history management with token-based summarization when approaching context limits, maintaining tool call/return pairing constraint. `decorators.py` offers `@context_result()` for tools returning large results, saving full content to workspace while returning truncated previews. Processors in `processors/` handle type-specific truncation: text, code, JSON, CSV, XML, YAML, documents, spreadsheets, images. Configuration via `ContextConfig` with limits for file processing, structured data, tabular data, history compaction, and truncation presets (default, sql_query, log_search).

**feedback/**: User feedback and session history persistence. `FeedbackType` enum (THUMBS_UP, THUMBS_DOWN, ERROR_REPORT, COMMENT). `FeedbackEntry` and `SessionFeedback` Pydantic models. Stores feedback and conversation history as JSON files per session at `FEEDBACK_DIR / user_id / session_id / {feedback.json, history.json}`. Uses PydanticAI's `ModelMessagesTypeAdapter` for history serialization.

**vectordb/**: Embedding and vector database integration for semantic search. Supports four embedding providers (OpenAI, Ollama, SentenceTransformers, OpenRouter) with Chroma as the vector DB backend. `get_embedder()` and `get_vector_db()` use factory pattern with singleton caching. `PydanticAIEmbeddingFunction` wraps embedders for Chroma compatibility. Operations include `vdb_add()`, `vdb_query()` for similarity search, and `vdb_get_by_id()`. Configuration loaded from YAML with environment variable expansion.

**tools/**: Tool infrastructure -- permissions and AI-driven selection. `ToolPermission` enum (READ, WRITE, CONNECT) with `@tool_permission()` decorator for metadata attachment. `filter_tools_by_permission()` and `enforce_tool_permission()` for runtime permission enforcement. `ToolSelector` uses an agent to select relevant tools based on user query. `func_to_description()` generates tool descriptions from function signatures and docstrings. PydanticAI tool wrappers live in top-level `agentic_patterns/tools/`, not here.

**evals/**: Evaluation framework for testing agent behavior. CLI via `python -m agentic_patterns.core.evals`. Auto-discovery of `eval_*.py` files with convention-based dataset/target/scorer detection. Custom evaluators: `OutputContainsJson` (validate JSON output), `ToolWasCalled` (verify tool execution), `NoToolErrors` (check for failures), `OutputMatchesSchema` (schema validation). `DiscoveredDataset` bundles dataset + target + scorers with filtering by module/file/dataset name.

**doctors/**: CLI tools for AI-powered analysis of prompts, tools, MCP servers, A2A agent cards, and Agent Skills. Run via `doctors` command (after `uv pip install -e .`) or `python -m agentic_patterns.core.doctors`. Subcommands: `prompt` (analyze prompt files), `tool` (analyze Python tool functions), `mcp` (analyze MCP server tools), `a2a` (analyze agent cards), `skill` (analyze agentskills.io format). Each doctor uses an LLM to evaluate quality and returns recommendations with issue levels.

**tasks/**: Async task system for background agent execution with event-driven coordination. `TaskState` enum (PENDING, RUNNING, COMPLETED, FAILED, INPUT_REQUIRED, CANCELLED) with TERMINAL_STATES set. `Task` model holds input, result, error, events, and metadata. `TaskStore` ABC with two implementations: `TaskStoreJson` (one JSON file per task in DATA_DIR/tasks) and `TaskStoreMemory` (in-memory dict-backed, ideal for notebooks). `TaskBroker` coordinates submission, observation (poll/stream/wait/cancel/notify callbacks), and dispatch via background loop; accepts optional `activity: asyncio.Event` for event-driven signaling when tasks reach terminal state, has `register_agents()` to bind `AgentSpec` instances for sub-agent resolution, and `cancel_all()` for cleanup. `Worker` executes tasks by running sub-agents: supports `agent_specs` dict for resolving sub-agents by name via `_execute_with_spec()` which runs OrchestratorAgent with the spec, emits PROGRESS/LOG events for background tracking via `_make_node_hook()`, and handles CancelledError for cancellation propagation. The event-driven wait pattern (replacing polling-based `check_tasks`) uses `wait(timeout)` that blocks on `asyncio.Event` until background work completes, with a clear-then-check pattern to prevent race conditions.

**connectors/**: Data source connectors used by agents to interact with external data. Connectors are an abstraction layer independent from tools -- agents call connector methods, which are then exposed as tools. Connectors MUST manage context to prevent the agent's context window from filling up when operations return large results (e.g. a SQL query returning a big table); they use truncation, pagination, and the `@context_result()` decorator to keep responses within safe limits. Base class in `base.py`. `FileConnector` (file.py) provides read, write, append, delete, edit, find, head, tail, list operations. `CsvConnector` (csv.py) provides append, delete, query, read with auto-delimiter detection. `JsonConnector` (json.py) provides JSONPath-based read/write with structure truncation. All connectors use static methods, `@tool_permission()` decorators (READ/WRITE), and workspace sandbox isolation via `workspace_to_host_path()`. **Vocabulary sub-connector** (`connectors/vocabulary/`): `VocabularyConnector` provides term resolution across controlled vocabularies and ontologies. Three resolution strategies based on vocabulary size: `StrategyEnum` (< 100 terms), `StrategyTree` (< 1K terms, BFS/DFS traversal), `StrategyRag` (1K+ terms, vector DB semantic search). Supports multiple vocabulary formats via parsers: OBO, OWL, RF2, tabular. `registry.py` manages vocabulary registration and routing. Config reads from `vocabularies.yaml`. **SQL sub-connector** (`connectors/sql/`): Pydantic data models for schema metadata (`DbInfo`, `TableInfo`, `ColumnInfo`, `ForeignKeyInfo`, `IndexInfo`), abstract + SQLite implementations for connections and operations (`sqlite/` subdirectory), schema inspection (`inspection/` with abstract + SQLite implementations), schema extraction with JSON caching, query validation (SELECT-only, single statement), schema SQL formatting (`SchemaFormatter`), singleton registries (`DbConnectionConfigs`, `DbInfos`), factory functions with match/case dispatch on `DatabaseType`. Configuration reads from `dbs.yaml`. Schema annotation pipeline (`annotation/`) with AI-powered descriptions, enum detection, and example query generation. CLI tools in `cli/`. Prompt templates in `prompts/sql/`. Architecture supports adding Postgres via new subdirectories and factory match/case branches. Note: NL2SQL and db_catalog agents live in `agentic_patterns/agents/`, not here. **OpenAPI sub-connector** (`connectors/openapi/`): Allows agents to interact with REST APIs by ingesting OpenAPI 3.x specs. Layered architecture: Configuration (`apis.yaml` with `${VAR}` expansion, `ApiConnectionConfig` registry) -> Extraction (`ApiSpecExtractor` fetches specs from URL/file, `OpenApiV3Parser` parses endpoints with `$ref` resolution) -> Annotation (`ApiSpecAnnotator` uses LLM to generate descriptions, categorize endpoints, create example curls; prompts in `prompts/openapi/annotation/`) -> Connector (`OpenApiConnector` with `list_apis`, `list_endpoints`, `show_api_summary`, `show_endpoint_details`, `call_endpoint`; uses `@context_result()` for large responses) -> Tools (`tools/openapi.py` exposes five tools with READ/CONNECT permissions). Data models: `ApiInfo`, `EndpointInfo`, `ParameterInfo`, `RequestSchemaInfo`, `ResponseSchemaInfo` (dataclasses with serialization). HTTP client: `RequestsApiClient` with retry and timeout. `ApiInfos` singleton registry with lazy init from cached JSON. CLI: `python -m agentic_patterns.core.connectors.openapi.cli.ingest <api_id>`. Config `base_url` overrides spec servers for environment-specific deployments. Current limitations: OpenAPI 3.x only (no Swagger 2.0), no authentication, no rate limiting.

**auth.py**: JWT token generation and validation for cross-layer identity propagation. `create_token(user_id, session_id)` encodes claims with HS256 shared secret. `decode_token(token)` validates and returns claims. Secret and algorithm read from `JWT_SECRET` / `JWT_ALGORITHM` env vars in `config.py`.

**mcp/**: MCP configuration, error classification, server toolsets, middleware, and factory functions. Refactored from a single file into a modular directory. `config.py` (`MCPClientConfig` with optional `url_isolated` field, `MCPServerConfig`, `MCPSettings`, `load_mcp_settings` with `${VAR}` env expansion from YAML). `errors.py` (`ToolRetryError` for LLM retries, `ToolFatalError` with `[FATAL]` prefix to abort runs). `servers.py` (`MCPServerStrict` extends `MCPServerStreamableHTTP` intercepting fatal errors; `MCPServerPrivateData` holds dual server instances -- normal and isolated -- and routes calls based on `session_has_private_data()` with one-way ratchet). `middleware.py` (`AuthSessionMiddleware` reads access token claims and calls `set_user_session()`). `factories.py` (`create_mcp_server()` with `AuthSessionMiddleware` pre-wired, `get_mcp_client()` returns `MCPServerPrivateData` when `url_isolated` is configured or `MCPServerStrict` otherwise, `get_mcp_clients()` for batch creation, `create_process_tool_call()` for Bearer token injection). `__init__.py` re-exports all public names for backward compatibility.

**skills/**: Skill library for agent capabilities with progressive disclosure pattern. `models.py` defines `SkillMetadata` (lightweight info: name, description, path) and `Skill` (full skill with frontmatter, body, script/reference/asset paths). `registry.py` provides `SkillRegistry` with `discover()` to scan skill directories and cache metadata (cheap), `list_all()` to return cached metadata for system prompt injection, and `get()` to lazy-load full skill on activation (expensive). Skills are defined in directories containing a `SKILL.md` file with YAML frontmatter (name, description) and markdown body. Optional `scripts/`, `references/`, and `assets/` subdirectories hold supporting files. `tools.py` exposes `list_available_skills()` for compact one-liner listings, `get_skill_instructions()` for returning the SKILL.md body only, and `get_all_tools(registry)` which returns an `activate_skill` function for on-demand skill loading. OrchestratorAgent auto-discovers skills from `SKILLS_DIR` and auto-adds the activation tool.

**a2a/**: Agent-to-Agent protocol integration. `client.py` provides `A2AClientExtended` with polling, retry, timeout, and cancellation support; `send_and_observe()` sends messages and polls until terminal state, returning `TaskStatus` (COMPLETED, FAILED, INPUT_REQUIRED, CANCELLED, TIMEOUT). `config.py` has `A2AClientConfig` (with optional `bearer_token` for injecting Authorization headers on the underlying httpx client) and YAML-based settings loading. `coordinator.py` provides `create_coordinator()` async factory that takes A2A clients, fetches their agent cards, creates delegation tools, and returns a configured coordinator agent. `tool.py` has `create_a2a_tool(client, card)` to create PydanticAI tools for delegation (returns formatted strings like `[COMPLETED] result` or `[INPUT_REQUIRED:task_id=X] question`), and `build_coordinator_prompt(cards)` to generate system prompts. `mock.py` provides `MockA2AServer` for testing without LLM calls: configure responses with `on_prompt(prompt, result=...)` or `on_pattern(regex, input_required=...)`, use `set_default(result)` for fallback responses, use `on_prompt_delayed(prompt, polls, result=...)` for delayed responses that return working state until N polls complete, and call `to_app()` to get a FastAPI instance. Check `received_prompts` and `cancelled_task_ids` for assertions. `utils.py` provides helpers: `create_message()`, `extract_text()`, `extract_question()`, `card_to_prompt()`, `slugify()`.

**repl/**: REPL (Read-Eval-Print Loop) engine for executing Python code iteratively in a stateful, process-isolated environment. Jupyter-like notebook model where cells share a namespace across executions. `notebook.py` manages cell lifecycle, persistence (JSON), import/function tracking, and ipynb export. `cell.py` delegates execution to `sandbox.py`, which uses pickle-based IPC: writes input (code, namespace, imports, funcdefs) to a temp dir, runs `executor.py` inside the generic `core/sandbox.py`, reads back a `SubprocessResult`. `executor.py` is a standalone `__main__` script that restores workbook references, configures matplotlib, replays imports and function definitions, executes cell code, captures stdout/stderr/figures, filters namespace to picklable objects, and writes output. `cell_utils.py` provides `SubprocessResult`, picklability filtering with helpful hints for common unpicklable types, function definition extraction via AST, and last-expression capture. `openpyxl_handler.py` serializes openpyxl Workbook objects across process boundaries via temp files (`WorkbookReference`). `matplotlib_backend.py` configures non-interactive Agg backend and captures figures. `image.py` has `Image` (binary data) and `ImageReference` (resource URI) models. `cell_output.py` wraps outputs with type/timestamp/serialization. `api_models.py` provides `CellInfo`, `NotebookInfo`, `OperationResult` for API layers. `enums.py` has `CellState` and `OutputType`. `config.py` has `DEFAULT_CELL_TIMEOUT`, `MAX_CELLS`, `SERVICE_NAME`. Notebook persistence at `WORKSPACE_DIR / user_id / session_id / mcp_repl / cells.json`.

**process_sandbox.py**: Generic sandbox for running commands in isolated environments, independent of the REPL. `BindMount(source, target, readonly)` dataclass for filesystem mounts. `SandboxResult(exit_code, stdout, stderr, timed_out)` dataclass for command output. `Sandbox` ABC with `async run(command, timeout, bind_mounts, isolate_network, isolate_pid, cwd, env) -> SandboxResult`. Two implementations: `SandboxBubblewrap` (Linux production, builds bwrap command with read-only system mounts, user-specified bind mounts, optional `--unshare-net` and `--unshare-pid`, auto-binds Python prefix for package access) and `SandboxSubprocess` (macOS/dev fallback, runs command as plain subprocess with no isolation). `get_sandbox()` factory returns bwrap if available on PATH. Used by `repl/sandbox.py` for REPL execution (imports from `core.process_sandbox`); can be reused by any module needing process-isolated command execution.

**sandbox/** (directory): Docker-based sandbox for production code execution with network isolation. `SandboxManager` manages Docker containers per session with destroy-by-default lifecycle: `execute_command(persistent=False)` creates a container, runs the command, and destroys the container (via `ephemeral_session()` context manager guaranteeing cleanup). `persistent=True` preserves the old behavior of caching sessions across commands. `_run_command()` holds the shared exec_run logic for both paths. `NetworkMode` enum (FULL="bridge", NONE="none") with `get_network_mode()` that checks `PrivateData` -- sessions containing private data get `network_mode="none"` (no network access). `ContainerConfig` defines image, resource limits (CPU, memory), environment, mounts. `SandboxSession` tracks container lifecycle per (user_id, session_id). The manager automatically recreates containers if network mode changes (e.g., when private data is loaded mid-session). The book's kill switch chapter also describes a PROXIED mode using an Envoy sidecar for CONFIDENTIAL data (whitelist-only connectivity), but this is not yet implemented in code.

**ui/**: User interface integrations. `auth.py` provides `UserDatabase` (JSON-backed) with SHA-256 password hashing and `User` model. `cli.py` exposes `manage-users` console script for user CRUD. **agui/**: AG-UI protocol integration via PydanticAI's `AGUIApp`. `create_agui_app()` factory creates AG-UI apps from config, `create_agui_app_from_agent()` wraps existing agents. Supports `StateDeps` for shared state. `events.py` for event handling. **chainlit/**: Chainlit chat UI integration. `handlers.py` provides `register_all()` to set up auth (password callback via `UserDatabase`), SQLite data layer for chat persistence, and chat resume with history restoration. `setup_user_session()` bridges Chainlit's user/thread context to core `set_user_session()`. `data_layer.py` provides SQLite-backed data layer. `storage.py` for file storage.

**prompt.py**: Template-based prompt loading from markdown files with include support. `load_prompt()` resolves `{% include 'relative/path.md' %}` directives (relative to `PROMPTS_DIR`), then extracts `{variable_name}` patterns and validates all required variables are provided (raises ValueError for missing/unused). Helper functions: `get_system_prompt()`, `get_prompt()`, `get_instructions()`.

**user_session.py**: User and session context via contextvars. `set_user_session(user_id, session_id)` sets context at request boundary. `get_user_id()` / `get_session_id()` read from contextvars. `set_user_session_from_token(token)` decodes a JWT and calls `set_user_session()` -- convenience for A2A servers and non-FastMCP entry points receiving raw token strings.

**workspace.py**: Sandbox workspace isolation for multi-tenant scenarios. `workspace_to_host_path()` and `host_to_workspace_path()` translate between agent-visible paths (`/workspace/...`) and host filesystem paths with traversal protection. File operations: `read_from_workspace()`, `write_to_workspace()`, `store_result()`. `clean_up_session()` resets workspace and compliance flags for development/testing.

**utils.py**: General utilities shared across core modules.

## Toolkits (`agentic_patterns/toolkits/`)

Pure Python business logic with no framework dependency. Each toolkit is a domain-specific module that can be used directly by PydanticAI agents (via `tools/`) or exposed through MCP servers (via `mcp/*/tools.py`). Three-layer architecture:

```
toolkits/*          Business logic. Pure Python: models, operations, I/O.
    |
    +-> tools/*             PydanticAI agent tool wrappers (get_all_tools()).
    +-> mcp/*/tools.py      MCP server thin wrappers (ctx, @mcp.tool(), error conversion).
```

Connectors (`core/connectors/`) are for data source access. Toolkits are for everything else: domain logic, operations, services.

**todo/**: Todo management business logic. `models.py` defines `TodoItem`, `TodoList`, `TodoState` enum with hierarchical item IDs and workspace persistence. `operations.py` exposes plain functions (`todo_add`, `todo_add_many`, `todo_create_list`, `todo_delete`, `todo_show`, `todo_update_status`) with in-memory cache keyed by (user_id, session_id). Raises `ValueError`/`KeyError` on errors.

**data_analysis/**: DataFrame analysis operations. `config.py`, `enums.py`, `models.py` for configuration and `OperationConfig` registry model. `io.py` for loading/saving DataFrames (CSV/pickle). `display.py` for DataFrame-to-string formatting. `ml_helpers.py` for ML utilities. `executor.py` provides `execute_operation()` and `get_all_operations()` -- loads DataFrames, runs operations, saves results, returns formatted strings. Raises `ValueError` for retryable errors, `RuntimeError` for fatal errors. Operation registries: `ops_eda.py`, `ops_stats.py`, `ops_transform.py`, `ops_classification.py`, `ops_regression.py`, `ops_feature_importance.py`.

**data_viz/**: Plot generation operations. Same pattern as data_analysis. `executor.py` provides `execute_plot()` and `get_all_operations()`. Operation registries: `ops_basic.py`, `ops_distribution.py`, `ops_categorical.py`, `ops_matrix.py`. Uses matplotlib with Agg backend.

**format_conversion/**: Document format conversion. `enums.py` defines `InputFormat` (CSV, DOCX, MD, PDF, PPTX, XLSX) and `OutputFormat` (CSV, DOCX, HTML, MD, PDF). `ingest.py` converts documents to Markdown/CSV using pymupdf, python-docx, python-pptx, openpyxl. `export.py` converts Markdown to PDF (via pypandoc to HTML then weasyprint to PDF), DOCX, and HTML (via pypandoc). `converter.py` provides `convert()` dispatch function routing by input extension and output format.

## Domain Agents (`agentic_patterns/agents/`)

All domain-specific agents live here, separate from the infrastructure in `core/agents/`. Each module exposes a `create_*()` factory returning a PydanticAI `Agent` and optionally a `run_*()` async helper.

`db_catalog.py` selects the appropriate database for a query using `DatabaseSelection` structured output. `vocabulary.py` creates agents with vocabulary tools for term resolution across controlled vocabularies. `nl2sql/` sub-package (`agent.py`, `prompts.py`) creates NL2SQL agents bound to a specific database via closure-based tools. `data_analysis.py` creates a data analysis agent with DataFrame tools. `sql.py` creates a general SQL agent with schema-agnostic SQL tools. `coordinator.py` creates an `OrchestratorAgent` that delegates to `data_analysis` and `sql` sub-agents via delegation tools. Domain agents also provide `get_spec()` factory methods returning `AgentSpec` instances for composition into higher-level agents via OrchestratorAgent.

## Tools (`agentic_patterns/tools/`)

PydanticAI agent tool wrappers -- top-level peer of `toolkits/` and `mcp/`. Each file exposes `get_all_tools()` returning plain functions passed to `Agent(tools=[...])`. Connector wrappers: `file.py`, `csv.py`, `json.py`, `sql.py`, `nl2sql.py`, `openapi.py` wrap `core/connectors/`. Toolkit wrappers: `todo.py`, `data_analysis.py`, `data_viz.py`, `format_conversion.py` wrap `toolkits/`. Core infrastructure wrappers: `repl.py` (7 tools wrapping `core/repl/` -- execute_cell, rerun_cell, show_notebook, show_cell, delete_cell, clear_notebook, export_ipynb), `sandbox.py` (1 tool wrapping `core/sandbox/` -- sandbox_execute; uses `asyncio.to_thread()` to avoid blocking the event loop). `dynamic.py` provides shared helpers (`get_param_signature()`, `generate_param_docs()`) for dynamically generating tool functions from operation registries, used by both PydanticAI and MCP wrappers.

## MCP Servers (`agentic_patterns/mcp/`)

**template/**: Reference implementation of a production MCP server demonstrating requirements 1-9 and 11 from `docs/mcp_requirements.md`. `server.py` uses `create_mcp_server()` with `AuthSessionMiddleware` pre-wired. `tools.py` registers four tools showing `@tool_permission`, `@context_result()`, workspace path translation, `ToolRetryError`/`ToolFatalError`, `PrivateData` flagging, and `ctx.info()` logging. The interactive client example is in `agentic_patterns/examples/execution_infrastructure/example_mcp_isolation.ipynb`.

**todo/**: Thin MCP wrapper for todo management. `server.py` + `tools.py` only. Delegates to `toolkits/todo/operations`, adds `ctx: Context`, converts exceptions to `ToolRetryError`. Six tools: todo_add, todo_add_many, todo_create_list, todo_delete, todo_show, todo_update_status.

**data_analysis/**: Thin MCP wrapper for DataFrame analysis. `server.py` + `tools.py` only. Delegates to `toolkits/data_analysis/executor`. Dynamically generates tools from the operation registry using `tools/dynamic` helpers. Converts `ValueError` to `ToolRetryError`, `RuntimeError` to `ToolFatalError`.

**data_viz/**: Thin MCP wrapper for plot generation. Same pattern as data_analysis. Delegates to `toolkits/data_viz/executor`.

**format_conversion/**: Thin MCP wrapper for document conversion. Delegates to `toolkits/format_conversion/converter`. Single tool: `convert_document`.

**file_ops/**: Thin MCP wrapper for file operations. Delegates to `core/connectors/file`.

**sql/**: Thin MCP wrapper for SQL operations. Delegates to `core/connectors/sql/`.

**repl/**: Thin MCP wrapper for REPL notebook execution. Delegates to `core/repl/`. Seven tools: execute_cell, rerun_cell, show_notebook, show_cell, delete_cell, clear_notebook, export_ipynb. Converts `ValueError`/`IndexError` to `ToolRetryError`.

**sandbox/**: Thin MCP wrapper for Docker sandbox execution. Delegates to `core/sandbox/`. Single tool: execute (uses `asyncio.to_thread()` to avoid blocking the event loop). Converts `DockerException`/`NotFound` to `ToolFatalError`.

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
- `execution_infrastructure/` - MCP isolation notebook
- `a2a/` - A2A servers and clients (v1, v2)
- `evals/` - Evaluation examples, doctors analysis, skills (skill-bad, skill-good subdirectories)
- `connectors/` - JSON connector, SQL connector, NL2SQL agent examples
- `sub_agents/` - Sub-agent examples (notebooks; domain agents live in `agentic_patterns/agents/`)
- `skills/` - Skills examples with SKILL.md definitions
- `the_complete_agent/` - Five-step agent progression (coder, planner, skilled, coordinator, full)
- `ui/` - AG-UI and Chainlit apps, frontend

## Chapters

Chapters in `chapters/`: foundations, core_patterns, tools, context_memory, orchestration, rag, mcp, a2a, skills_and_sub_agents, evals, execution_infrastructure, data_sources_and_connectors, ui, the_complete_agent. Each contains `chapter.md` index linking to section files and hands-on exercises. Master index in `chapters.md` at root. The execution_infrastructure chapter covers: Sandbox, REPL, MCP Server Isolation, Skill Sandbox, and Hands-On MCP Server Isolation. The the_complete_agent chapter progressively builds five agent variants from simple to complex: V1 Coder (file + sandbox tools), V2 Planner (adds todo tools), V3 Skilled (progressive skill disclosure), V4 Coordinator (sub-agent delegation), V5 Full Agent (unified async task orchestration with event-driven wait).

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
- `ingest_openapi.sh` - Ingests OpenAPI specs
- `make.py` - Python utility for book compilation
- `fix_references.py` - Reference fixing utility

## Configuration

**config.yaml**: Model configurations with named entries (default, fast, azure_gpt4, bedrock_claude, bedrock_claude_extended, ollama_local, openrouter_claude). Each model config includes model_family, model_name, provider-specific credentials, timeout, optional parallel_tool_calls.

**pyproject.toml**: Project metadata and dependencies. Key packages: pydantic-ai[ag-ui] (>=1.39.0), chromadb (>=1.4.1), openai (>=2.14.0), fastmcp (>=2.14.2), fasta2a (>=0.6.0), pyjwt (>=2.9.0), requests (>=2.32.0), chainlit (>=2.9.6), docker (>=7.0.0), sqlalchemy (>=2.0.0), aiosqlite (>=0.21.0), pandas (>=3.0.0), fastapi (>=0.128.0), weasyprint (>=68.1), jsonpath-ng, pyyaml, dotenv, ipykernel. Console scripts: `doctors`, `evals`, `manage-users`, `annotate-schema`, `ingest-openapi`.

**users.json**: JSON-based user database for authentication (used by `UserDatabase` in `ui/auth.py`).

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

`docs/skills_specification.md` -- Agent Skills specification: overview, integration approaches, SKILL.md format, directory structure, progressive disclosure, validation.

`docs/tasks.md` -- Task system design document: async task submission, observation (poll/stream/wait), worker execution, state machine.

`docs/mcp_requirements.md` -- Checklist of requirements for production MCP servers: auth, workspace, context, permissions, compliance, connectors, config, errors, Docker, testing.

`docs/a2a_requirements.md` -- Requirements for A2A servers: server creation via `get_agent()`/`to_a2a()`, auth with Bearer token propagation, client config, coordination with delegation tools, resilience (retry/timeout/cancel), prompt management, testing with `MockA2AServer`. Includes template implementation plan.

`docs/refactor_mcp_connectors.md` -- Design document for the toolkits refactoring: extracting business logic from MCP servers into `toolkits/`, creating PydanticAI tool wrappers in `tools/`, and simplifying MCP wrappers to thin delegation layers. Fully implemented.

`docs/plan_monolithic_agents.md` -- Design for the five-agent progression (V1-V5) in the_complete_agent chapter: tool sets, library changes, prompt composition strategy.

`docs/plan_event_driven_wait.md` -- Design for event-driven task waiting: unified `asyncio.Event` replaces polling-based `check_tasks`, timeout control, race condition safety via clear-then-check pattern.

Each index file (`*.md`) links to detailed section files in corresponding subdirectories (`a2a_specification/`, `agui/`, `fastmcp/`, `mcp/`, `pydantic-ai/`, `skills_specification/`). Original unprocessed source files are in `docs/original/`.

## Notebooks

**Session identity**: NEVER call `set_user_session()` in notebooks. The contextvars have defaults (`DEFAULT_USER_ID`, `DEFAULT_SESSION_ID`) configured in `core/config/config.py`. Notebooks rely on these defaults. `set_user_session()` is only called at real request boundaries (middleware, MCP handlers, etc.), never in example code.

## Additional Conventions

**Tests**: In `tests/` directory at root with `unit/` and `integration/` subdirectories. Run via `scripts/test.sh` (uses pytest).

**Code imports**: When code in `agentic_patterns/examples/<chapter>/` imports from `agentic_patterns/core/`, ensure PYTHONPATH is set correctly (scripts/config.sh handles this).

**Prompts**: Store prompt templates in `prompts/` directory as markdown files. Use `load_prompt()` from `core/prompt.py` to load with variable substitution and `{% include %}` support. Reusable prompt blocks go in `prompts/shared/` (workspace, sandbox, skills, sub_agents, file_tools, data_analysis_tools, data_viz_tools, repl). Agent-specific prompts compose shared blocks via includes.

**Image optimization**: Use compressed PNGs or SVGs for diagrams. Large images bloat git history permanently.

**References**: All references and citations should be included in a `references.md` file.
