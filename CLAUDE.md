# CLAUDE.md

Full documentation: `docs/agentic_patterns.md` (main file) and `docs/agentic_patterns/` (detail files).

## Project Overview

Repository for the book "Agentic Patterns" -- a proof-of-concept agentic platform teaching architectural principles for AI agent systems. Targets software engineers and ML practitioners. All code uses PydanticAI. Book is written in markdown with each chapter in its own directory.

## Repository Structure

```
book_agentic_patterns/
├── chapters/           # Book chapters (markdown files)
├── agentic_patterns/   # Python code examples and core library
│   ├── core/          # Reusable infrastructure
│   ├── agents/        # Domain-specific agents (db_catalog, vocabulary, nl2sql, openapi, etc.)
│   ├── a2a/           # A2A server implementations (thin wrappers over agents + MCP)
│   ├── toolkits/      # Business logic (no framework dependency)
│   ├── tools/         # PydanticAI agent tool wrappers
│   ├── mcp/           # MCP server thin wrappers
│   ├── examples/      # Code examples by chapter
│   └── testing/       # Testing utilities for agents
├── scripts/            # Build, validation, lint scripts
├── tests/              # Tests (unit/ and integration/ subdirectories)
├── prompts/            # Prompt templates (markdown files)
├── data/               # Runtime data (db/, workspaces/)
├── docs/               # Design and reference documents
└── output/             # Generated book output (book.md, PDF)
```

## Conventions

**Chapters**: All under `chapters/`. Each directory has a `chapter.md` index linking to section files. Images in `img/` subdirectory. Heading levels: `#` for chapter titles, `##` for section titles, `###` and below for sub-sections. Master index in `chapters.md` at root.

**Code organization**: All code in `agentic_patterns/`. Examples under `agentic_patterns/examples/` in directories matching chapters. Core utilities in `agentic_patterns/core/`.

**Notebooks**: NEVER call `set_user_session()` in notebooks -- contextvars have defaults in `core/config/config.py`. `set_user_session()` is only called at real request boundaries (middleware, MCP handlers).

**Prompts**: Store in `prompts/` as markdown files. Load via `load_prompt()` from `core/prompt.py` (supports `{% include %}` and `{variable}` substitution). Reusable blocks in `prompts/shared/`.

**Images**: Use compressed PNGs or SVGs. Large images bloat git history.

**References**: All citations in a `references.md` file.

## Three-Layer Architecture

```
toolkits/*          Business logic. Pure Python: models, operations, I/O.
    |
    +-> tools/*             PydanticAI agent tool wrappers (get_all_tools()).
    +-> mcp/*/tools.py      MCP server thin wrappers (ctx, @mcp.tool(), error conversion).
```

Connectors (`core/connectors/`) are for data source access. Toolkits are for domain logic, operations, services. Each tool file exposes `get_all_tools()` returning plain functions for `Agent(tools=[...])`.

## Core Library (`agentic_patterns/core/`)

| Module | Purpose |
|---|---|
| `agents/` | Agent instantiation (`get_agent()` from YAML config), execution (`run_agent()`), `OrchestratorAgent` + `AgentSpec` for composition with tools/MCP/A2A/skills/sub-agents/tasks. Five providers: Azure OpenAI, Bedrock, Ollama, OpenAI, OpenRouter. |
| `config/` | Environment/project config. Key paths: DATA_DIR, PROMPTS_DIR, WORKSPACE_DIR, PRIVATE_DATA_DIR. `.env` loading with fallback. |
| `connectors/` | Data source connectors (file, csv, json, sql, vocabulary, openapi). Use `@context_result()` for large results. SQL supports SQLite (Postgres via new subdirs + factory branches). OpenAPI ingests 3.x specs. Vocabulary has three strategies by size (enum/tree/rag). |
| `context/` | Large file handling, history compaction (`HistoryCompactor`), result truncation (`@context_result()` decorator). Type-specific processors. |
| `compliance/` | Private data management. `DataSensitivity` enum, `mark_session_private()`. Drives network isolation in sandbox. |
| `mcp/` | MCP config, errors (`ToolRetryError`/`ToolFatalError`), server factories (`create_mcp_server()`), client factories (`get_mcp_client()`), `AuthSessionMiddleware`. |
| `a2a/` | A2A client (`A2AClientExtended`), coordinator factory, delegation tools, `MockA2AServer` for testing, skill conversion helpers. |
| `tasks/` | Async task system: `TaskBroker` for submission/observation, `Worker` for execution, event-driven wait. `TaskStoreJson` and `TaskStoreMemory`. |
| `skills/` | Skill registry with progressive disclosure. Skills defined via `SKILL.md` with YAML frontmatter. `activate_skill` tool for on-demand loading. |
| `tools/` | Tool permissions (`@tool_permission()`), AI-driven tool selection (`ToolSelector`). |
| `evals/` | Eval framework with auto-discovery. Custom evaluators: `OutputContainsJson`, `ToolWasCalled`, `NoToolErrors`, `OutputMatchesSchema`. |
| `doctors/` | CLI for AI-powered analysis of prompts, tools, MCP servers, A2A cards, skills. |
| `repl/` | Stateful Python REPL with process isolation, pickle-based IPC, notebook persistence. |
| `sandbox/` | Docker-based sandbox with network isolation driven by compliance flags. |
| `process_sandbox.py` | Generic command sandbox: `SandboxBubblewrap` (Linux) / `SandboxSubprocess` (macOS fallback). |
| `feedback/` | User feedback and session history persistence (JSON per session). |
| `vectordb/` | Embedding + Chroma integration. Four providers (OpenAI, Ollama, SentenceTransformers, OpenRouter). |
| `ui/` | `UserDatabase` (JSON-backed auth), AG-UI integration (`AGUIApp`), Chainlit chat UI. |
| `auth.py` | JWT token generation/validation (HS256). |
| `prompt.py` | Template loading with `{% include %}` and variable substitution. |
| `user_session.py` | User/session context via contextvars. `set_user_session()` at request boundaries only. |
| `workspace.py` | Sandbox workspace isolation. Path translation between `/workspace/...` and host paths. |

Key patterns: async-first with sync wrappers, Pydantic config validation, factory + singleton caching, match/case provider dispatch, decorator-based permissions/truncation, multi-tenant isolation via (user_id, session_id).

## Domain Agents (`agentic_patterns/agents/`)

Each module exposes `create_*()` factory returning a PydanticAI `Agent` and optionally `get_spec()` returning `AgentSpec` for composition. Agents: `db_catalog`, `vocabulary`, `nl2sql/`, `data_analysis`, `sql`, `openapi`, `coordinator`.

## MCP Servers (`agentic_patterns/mcp/`)

All follow the same thin-wrapper pattern: `server.py` + `tools.py`, delegate to toolkits/connectors, convert exceptions to `ToolRetryError`/`ToolFatalError`. Servers: `template/` (reference impl), `todo/`, `data_analysis/`, `data_viz/`, `format_conversion/`, `file_ops/`, `sql/`, `repl/`, `sandbox/`, `vocabulary/`, `openapi/`.

## A2A Servers (`agentic_patterns/a2a/`)

Each server: loads prompt, connects MCP via `get_mcp_client()`, builds skills list, creates agent with `get_agent()`, exposes via `agent.to_a2a()` + `AuthSessionMiddleware`. Servers: `template/`, `nl2sql/` (port 8002), `data_analysis/` (8201), `vocabulary/` (8202), `openapi/` (8203).

## Scripts

All scripts source `config.sh` (sets PROJECT_DIR, loads .env, activates .venv, sets PYTHONPATH):

`make.sh` (book compilation), `test.sh` / `test_unit.sh` / `test_integration.sh`, `evals.sh`, `lint.sh`, `db_ingest_bookstore_sqlite.sh`, `annotate_schema.sh`, `download_vocabularies.sh`, `ingest_openapi.sh`, `launch_infrastructure.sh` (MCP + A2A servers), `clean_notebooks.sh`.

## Configuration

**config.yaml**: Named model configs (default, fast, azure_gpt4, bedrock_claude, etc.) with provider, credentials, timeout.

**pyproject.toml**: Dependencies and console scripts (`doctors`, `evals`, `manage-users`, `annotate-schema`, `ingest-openapi`).

**apis.yaml**: OpenAPI specs with `${VAR}` env expansion.

## Reference Documentation (`docs/`)

Consult these when working on related topics: `pydantic-ai.md`, `mcp.md`, `fastmcp.md`, `a2a_specification.md`, `agui.md`, `skills_specification.md`, `tasks.md`, `mcp_requirements.md`, `a2a_requirements.md`. Each links to detailed sections in subdirectories.
