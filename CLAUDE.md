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

**agents/**: Agent instantiation and execution using PydanticAI. `get_agent()` creates agents from YAML-based model configurations with configurable timeout, parallel tool calls, and optional history compaction. `run_agent()` executes agents with step-by-step logging and MCP context integration. Supports five LLM providers via match/case dispatch: Azure OpenAI, AWS Bedrock (with 1M token context for Claude), Ollama, OpenAI, and OpenRouter. Provider-specific config classes (AzureConfig, BedrockConfig, OllamaConfig, OpenAIConfig, OpenRouterConfig) are defined in `config.py`, model creation in `models.py`, and utilities like `get_usage()`, `has_tool_calls()`, and `nodes_to_message_history()` in `utils.py`.

**config/**: Environment and project configuration with smart discovery. `AGENTIC_PATTERNS_PROJECT_DIR` points to core library location while `MAIN_PROJECT_DIR` adapts when core is a package in another project. Provides derived paths: SCRIPTS_DIR, DATA_DIR, DATA_DB_DIR, LOGS_DIR, PROMPTS_DIR, WORKSPACE_DIR. Environment loading (`env.py`) searches multiple directories for `.env` files with fallback strategy.

**context/**: Multi-layered context management for handling large files, history compaction, and result truncation. `reader.py` detects file types (code, markdown, text, documents, spreadsheets, JSON, YAML, XML, CSV, images, audio, archives, PDF, PPTX, DOCX) and dispatches to specialized processors. `history.py` provides `HistoryCompactor` for conversation history management with token-based summarization when approaching context limits, maintaining tool call/return pairing constraint. `decorators.py` offers `@context_result()` for tools returning large results, saving full content to workspace while returning truncated previews. Processors in `processors/` handle type-specific truncation: text, code, JSON, CSV, XML, YAML, documents, spreadsheets, images. Configuration via `ContextConfig` with limits for file processing, structured data, tabular data, history compaction, and truncation presets (default, sql_query, log_search).

**vectordb/**: Embedding and vector database integration for semantic search. Supports four embedding providers (OpenAI, Ollama, SentenceTransformers, OpenRouter) with Chroma as the vector DB backend. `get_embedder()` and `get_vector_db()` use factory pattern with singleton caching. `PydanticAIEmbeddingFunction` wraps embedders for Chroma compatibility. Operations include `vdb_add()`, `vdb_query()` for similarity search, and `vdb_get_by_id()`. Configuration loaded from YAML with environment variable expansion.

**tools/**: Tool management with permissions and AI-driven selection. `ToolPermission` enum (READ, WRITE, CONNECT) with `@tool_permission()` decorator for metadata attachment. `filter_tools_by_permission()` and `enforce_tool_permission()` for runtime permission enforcement. `ToolSelector` uses an agent to select relevant tools based on user query. `func_to_description()` generates tool descriptions from function signatures and docstrings.

**evals/**: Evaluation framework for testing agent behavior. CLI via `python -m agentic_patterns.core.evals`. Auto-discovery of `eval_*.py` files with convention-based dataset/target/scorer detection. Custom evaluators: `OutputContainsJson` (validate JSON output), `ToolWasCalled` (verify tool execution), `NoToolErrors` (check for failures), `OutputMatchesSchema` (schema validation). `DiscoveredDataset` bundles dataset + target + scorers with filtering by module/file/dataset name.

**doctors/**: CLI tools for AI-powered analysis of prompts, tools, MCP servers, A2A agent cards, and Agent Skills. Run via `doctors` command (after `uv pip install -e .`) or `python -m agentic_patterns.core.doctors`. Subcommands: `prompt` (analyze prompt files), `tool` (analyze Python tool functions), `mcp` (analyze MCP server tools), `a2a` (analyze agent cards), `skill` (analyze agentskills.io format). Each doctor uses an LLM to evaluate quality and returns recommendations with issue levels.

**skills/**: Skill library for agent capabilities with progressive disclosure pattern. `models.py` defines `SkillMetadata` (lightweight info: name, description, path) and `Skill` (full skill with frontmatter, body, script/reference paths). `registry.py` provides `SkillRegistry` with `discover()` to scan skill directories and cache metadata (cheap), `list_all()` to return cached metadata for system prompt injection, and `get()` to lazy-load full skill on activation (expensive). Skills are defined in directories containing a `SKILL.md` file with YAML frontmatter (name, description) and markdown body. Optional `scripts/` and `references/` subdirectories hold supporting files. `tools.py` exposes `list_available_skills()` for compact one-liner listings and `get_skill_instructions()` for full body and file paths.

**a2a/**: Agent-to-Agent protocol integration. `client.py` provides `A2AClientExtended` with polling, retry, timeout, and cancellation support; `send_and_observe()` sends messages and polls until terminal state, returning `TaskStatus` (COMPLETED, FAILED, INPUT_REQUIRED, CANCELLED, TIMEOUT). `config.py` has `A2AClientConfig` and YAML-based settings loading. `coordinator.py` provides `create_coordinator()` async factory that takes A2A clients, fetches their agent cards, creates delegation tools, and returns a configured coordinator agent. `tool.py` has `create_a2a_tool(client, card)` to create PydanticAI tools for delegation (returns formatted strings like `[COMPLETED] result` or `[INPUT_REQUIRED:task_id=X] question`), and `build_coordinator_prompt(cards)` to generate system prompts. `mock.py` provides `MockA2AServer` for testing without LLM calls: configure responses with `on_prompt(prompt, result=...)` or `on_pattern(regex, input_required=...)`, use `set_default(result)` for fallback responses, use `on_prompt_delayed(prompt, polls, result=...)` for delayed responses that return working state until N polls complete, and call `to_app()` to get a FastAPI instance. Check `received_prompts` and `cancelled_task_ids` for assertions.

**prompt.py**: Template-based prompt loading from markdown files. `load_prompt()` extracts `{variable_name}` patterns, validates all required variables are provided, and raises ValueError for missing/unused variables. Helper functions: `get_system_prompt()`, `get_prompt()`, `get_instructions()`.

**workspace.py**: Sandbox workspace isolation for multi-tenant scenarios. `container_to_host_path()` and `host_to_container_path()` translate between agent-visible paths (`/workspace/...`) and host filesystem paths with traversal protection. User/session isolation via `get_user_id_from_request()` and `get_session_id_from_request()` from RunContext. File operations: `read_from_workspace()`, `write_to_workspace()`, `store_result()`.

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

## Chapters

Chapters in `chapters/`: foundations, core_patterns, tools, context_memory, orchestration, rag, mcp, a2a, skills, sub_agents, evals, execution_infrastructure, connectors. Each contains `chapter.md` index linking to section files and hands-on exercises. Master index in `chapters.md` at root.

## Scripts

All scripts in `scripts/` follow the `config.sh` pattern (sets PROJECT_DIR, loads .env, activates .venv, sets PYTHONPATH):

- `config.sh` - Common setup for all scripts
- `make.sh` - Compiles chapters to output/book.md with optional PDF
- `test.sh` - Runs all tests (test_unit.sh + test_integration.sh)
- `test_unit.sh` - Runs pytest on tests/unit/
- `test_integration.sh` - Runs pytest on tests/integration/
- `evals.sh` - Runs evaluations
- `lint.sh` - Runs linter

## Configuration

**config.yaml**: Model configurations with named entries (default, fast, azure_gpt4, bedrock_claude, bedrock_claude_extended, ollama_local, openrouter_claude). Each model config includes model_family, model_name, provider-specific credentials, timeout, optional parallel_tool_calls.

**pyproject.toml**: Project metadata and dependencies. Key packages: pydantic-ai (>=1.39.0), chromadb (>=1.4.1), openai (>=2.14.0), fastmcp (>=2.14.2), fasta2a (>=0.6.0), pyyaml, dotenv, ipykernel. Console script: `doctors`.

## Additional Conventions

**Tests**: In `tests/` directory at root with `unit/` and `integration/` subdirectories. Run via `scripts/test.sh` (uses pytest).

**Code imports**: When code in `agentic_patterns/examples/<chapter>/` imports from `agentic_patterns/core/`, ensure PYTHONPATH is set correctly (scripts/config.sh handles this).

**Prompts**: Store prompt templates in `prompts/` directory as markdown files. Use `load_prompt()` from `core/prompt.py` to load with variable substitution.

**Image optimization**: Use compressed PNGs or SVGs for diagrams. Large images bloat git history permanently.

**References**: All references and citations should be included in a `references.md` file.
