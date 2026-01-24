# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a repository for the book "Agentic Patterns", which explores design patterns and best practices for building agentic systems using AI technologies. The book is written in markdown with each chapter in its own directory.

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
├── data/               # Runtime data (vectordb, workspaces)
└── docs/               # Generated documentation
```

## Conventions

**Chapter directories**: All chapters under `chapters/` directory. Name them with descriptive names (e.g., `foundations`, `core_patterns`, `tools`). Each chapter directory contains a `chapter.md` index file that links to individual section markdown files. Images stored in `img/` subdirectory within each chapter.

**Code organization**: All code in `agentic_patterns/`. Code examples are organized under `agentic_patterns/examples/` in directories that correspond to chapters (e.g., `foundations`, `core_patterns`, `tools`). Code examples may be Python files (.py) or Jupyter notebooks (.ipynb). Core utilities shared across chapters go in `agentic_patterns/core/`. Follow global Python conventions (type hints, pathlib, etc.).

## Core Library (`agentic_patterns/core/`)

The core library provides reusable infrastructure for building AI agentic systems with PydanticAI.

### Module Structure

**agents/**: Agent instantiation and execution using PydanticAI. `get_agent()` creates agents from YAML-based model configurations with configurable timeout, parallel tool calls, and optional history compaction. `run_agent()` executes agents with step-by-step logging and MCP context integration. Supports five LLM providers via match/case dispatch: Azure OpenAI, AWS Bedrock (with 1M token context for Claude), Ollama, OpenAI, and OpenRouter. Provider-specific config classes (AzureConfig, BedrockConfig, etc.) are defined in `config.py`, model creation in `models.py`, and utilities like `get_usage()` and `nodes_to_message_history()` in `utils.py`.

**config/**: Environment and project configuration with smart discovery. `AGENTIC_PATTERNS_PROJECT_DIR` points to core library location while `MAIN_PROJECT_DIR` adapts when core is a package in another project. Provides derived paths: SCRIPTS_DIR, DATA_DIR, LOGS_DIR, PROMPTS_DIR, WORKSPACE_DIR. Environment loading (`env.py`) searches multiple directories for `.env` files with fallback strategy.

**context/**: Multi-layered context management for handling large files, history compaction, and result truncation. `reader.py` detects 14 file types and dispatches to specialized processors (text, JSON, CSV, XML, YAML, documents, spreadsheets, images). `history.py` provides `HistoryCompactor` for conversation history management with token-based summarization when approaching context limits. `decorators.py` offers `@context_result()` for tools returning large results, saving full content to workspace while returning truncated previews. Processors in `processors/` handle type-specific truncation with configurable limits via `ContextConfig`.

**vectordb/**: Embedding and vector database integration for semantic search. Supports four embedding providers (OpenAI, Ollama, SentenceTransformers, OpenRouter) and two vector DB backends (Chroma, PgVector). `get_embedder()` and `get_vector_db()` use factory pattern with singleton caching. Operations include `vdb_add()`, `vdb_query()` for similarity search, and `vdb_get_by_id()`. Configuration loaded from YAML with environment variable expansion.

**tools/**: Tool management with permissions and AI-driven selection. `ToolPermission` enum (READ, WRITE, CONNECT) with `@tool_permission()` decorator for metadata attachment. `filter_tools_by_permission()` and `enforce_tools_permissions()` for runtime permission enforcement. `ToolSelector` uses an agent to select relevant tools based on user query. `func_to_description()` generates tool descriptions from function signatures and docstrings.

**evals/**: Evaluation framework for testing agent behavior. CLI via `python -m agentic_patterns.core.evals`. Auto-discovery of `eval_*.py` files with convention-based dataset/target/scorer detection. Custom evaluators: `OutputContainsJson` (validate JSON output), `ToolWasCalled` (verify tool execution), `NoToolErrors` (check for failures), `OutputMatchesSchema` (schema validation). `DiscoveredDataset` bundles dataset + target + scorers with filtering by module/file/dataset name.

**doctors/**: CLI tools for AI-powered analysis of prompts, tools, MCP servers, and A2A agent cards. Run via `doctors` command (after `uv pip install -e .`) or `python -m agentic_patterns.core.doctors`. Subcommands: `prompt` (analyze prompt files), `tool` (analyze Python tool functions), `mcp` (analyze MCP server tools), `a2a` (analyze agent cards). Each doctor uses an LLM to evaluate quality and returns recommendations with issue levels.

**prompt.py**: Template-based prompt loading from markdown files. `load_prompt()` extracts `{variable_name}` patterns, validates all required variables are provided, and raises ValueError for missing/unused variables. Helper functions: `get_system_prompt()`, `get_prompt()`, `get_instructions()`.

**workspace.py**: Sandbox workspace isolation for multi-tenant scenarios. `container_to_host_path()` and `host_to_container_path()` translate between agent-visible paths (`/workspace/...`) and host filesystem paths with traversal protection. User/session isolation via `get_user_id_from_request()` and `get_session_id_from_request()` from RunContext. File operations: `read_from_workspace()`, `write_to_workspace()`, `store_result()`.

### Key Patterns

The library uses async-first design with sync wrappers, Pydantic models for configuration validation, factory pattern with singleton caching for models/embedders/vector DBs, extensive match/case for provider dispatch, decorator-based composition for permissions and result truncation, and context-aware request handling (user_id, session_id) for multi-tenant isolation. Token counting via tiktoken with char-count fallback for graceful degradation.

## Testing Utilities (`agentic_patterns/testing/`)

Mock utilities for deterministic agent testing without API calls. `AgentMock` replays recorded agent nodes. `AgentRunMock` provides mock agent run iterator. `ModelMock` for LLM model mocking. `ToolMockWrapper` and `tool_mock()` decorator for tool function mocking. `final_result_tool()` for structured completion.

## Examples (`agentic_patterns/examples/`)

Code examples organized by chapter: `foundations/` (basic agents, multi-turn), `tools/` (tool use, permissions, workspace), `core_patterns/` (ReAct, CoT, ToT, self-reflection), `context_memory/` (history compaction), `orchestration/` (delegation, workflows), `rag/` (embeddings, vector search), `mcp/` (stdio/HTTP clients), `a2a/` (agent cards, servers), `evals/` (evaluation setup).

## Chapters

Twelve chapters: foundations, tools, core_patterns, context_memory, orchestration, rag, evals, execution_infrastructure, mcp, a2a, connectors, skills. Each contains `chapter.md` index linking to section files.

## Additional Conventions

**Tests**: In `tests/` directory at root with `unit/` and `integration/` subdirectories. Name test files to match chapters. Use standard Python unittest framework. Run via `scripts/test.sh`.

**Dependencies**: Single `pyproject.toml` at root. Key packages: pydantic-ai, chromadb, openai, fastmcp, pyyaml. Console script: `doctors` for CLI tools.

**Code imports**: When code in `agentic_patterns/examples/<chapter>/` imports from `agentic_patterns/core/`, ensure PYTHONPATH is set correctly or use relative imports.

**Prompts**: Store prompt templates in `prompts/` directory as markdown files. Use `load_prompt()` from `core/prompt.py` to load with variable substitution.

**Image optimization**: Use compressed PNGs or SVGs for diagrams. Large images bloat git history permanently.

**References**: All references and citations should be included in a `references.md` file.
