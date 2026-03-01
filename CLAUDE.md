# CLAUDE.md

Full documentation: `docs/agentic_patterns.md` (main file) and `docs/agentic_patterns/` (detail files). 

IMPORTANT: When checking or updating `CLAUDE.md`, you MUST check / update the `docs/agentic_patterns/` files. 

## Project Overview

Repository for the book "Agentic Patterns" -- a proof-of-concept agentic platform teaching architectural principles for AI agent systems. Targets software engineers and ML practitioners. All code uses PydanticAI. Book is written in markdown with each chapter in its own directory.

## Repository Structure

```
book_agentic_patterns/
├── chapters/          # Book chapters (markdown files)
├── agentic_patterns/  # Python code examples and core library
│   ├── core/          # Reusable infrastructure
│   │   ├── agents/    #   Agent creation; orchestrator/ subdir has OrchestratorAgent, AgentSpec, AgentRunner
│   │   ├── skills/    #   Skill registry and activation (SKILL.md format)
│   │   ├── tasks/     #   Task state machine, dependency tracking, task tools (TaskList, Task, TaskStatus)
│   │   ├── rubric/    #   Evidence-backed evaluation pipeline (build, refine, assess)
│   │   ├── a2a/       #   A2A client and server utilities
│   │   ├── mcp/       #   MCP configuration and server management
│   │   ├── connectors/#   Data source access (OpenAPI, SQL, vocabulary, etc.)
│   │   ├── config/    #   Configuration loading
│   │   ├── context/   #   Request context and processors
│   │   ├── repl/      #   REPL execution
│   │   ├── sandbox/   #   Sandbox environment management
│   │   ├── tools/     #   Tool utilities
│   │   ├── evals/     #   Evaluation framework
│   │   ├── ui/        #   UI implementations (Chainlit, AG-UI)
│   │   ├── compliance/#   Data sensitivity, private data tagging, permission enforcement
│   │   ├── doc_ingestion/#  Document parsing (PDF, DOCX, PPTX, HTML)
│   │   ├── feedback/  #   User feedback persistence
│   │   ├── doctors/   #   Code quality analysis
│   │   └── vectordb/  #   Vector database utilities
│   ├── toolkits/      # Business logic (pure Python, no framework dependency)
│   ├── tools/         # PydanticAI tool wrappers (each file exposes get_all_tools())
│   ├── mcp/           # MCP servers (each subdir: tools.py + server.py); servers: data_analysis, data_viz, file_ops, format_conversion, openapi, repl, sandbox, sql, template, todo, vocabulary
│   ├── agents/        # Domain-specific agents (coordinator, data_analysis, db_catalog, openapi, red_team, sql, vocabulary, debate/, nl2sql/, rag/, research/)
│   ├── a2a/           # A2A servers (wrap agents for inter-agent communication)
│   ├── examples/      # Code examples by chapter
│   └── testing/       # Testing utilities for agents
├── scripts/            # Build, validation, lint scripts
├── tests/              # Tests (unit/, integration/, notebooks/ subdirectories)
├── prompts/            # Prompt templates (markdown files)
├── data/               # Runtime data (db/, workspaces/, skills/)
├── docs/               # Design and reference documents
├── plans/              # Planning artifacts (rubric plans, etc.)
└── output/             # Generated book output (book.md, PDF)
```

## Book Conventions

**Chapters master index**: The file `chapters.md` at the root serves as the master index for all chapters. 

**Chapters**: All under `chapters/`. Each directory has a `chapter.md` index linking to section files. Images in `img/` subdirectory. Heading levels: `#` for chapter titles, `##` for section titles, `###` and below for sub-sections. Master index in `chapters.md` at root.

**Code organization**: All code in `agentic_patterns/`. Examples under `agentic_patterns/examples/` in directories matching chapters. Core utilities in `agentic_patterns/core/`.

**Notebooks**: These are hands-on examples for the reader. They are described in their respective "Hand-on" sections in their respective chapters. NEVER call `set_user_session()` in notebooks -- contextvars have defaults in `core/config/config.py`. `set_user_session()` is only called at real request boundaries (middleware, MCP handlers).

**References**: All citations in a `references.md` file for each chapter. Format: `1. Author(s). *Title*. Venue or source, year. URL (optional)`

## Code

How the code fits together

- `core/`: reusable infrastructure for agents, skills, tasks, A2A, MCP, connectors, configuration, context management, REPL execution, sandboxing, tools, evaluation framework, UI implementations, code quality analysis, vector database utilities.
- `toolkits/`: These are "tool" implementations that contain the actual business logic -- plain Python, no framework. They can be re-used as both direct agent tools and as MCP tools.
- `tools/` and `mcp/` are thin wrappers that make toolkit functions available to PydanticAI agents and MCP servers respectively. 
- `connectors/` are reusable data access layers (e.g. OpenAPI, SQL, vocabulary) that can be used by toolkits or directly by agents.
- `agents/` are the agents themselves; they use those tools. An agent can delegate work to other agents as sub-agents. `coordinator.py` is the top-level multi-agent coordinator. `rag/` handles retrieval-augmented generation (chunking, clustering, retrieval).
- `a2a/` exposes agents over the network so external agents can call them.
- Skills are defined in `data/skills/`, each as a directory with a `SKILL.md` file (YAML frontmatter + markdown instructions). The registry in `core/skills/` discovers and loads them. See `docs/skills_specification.md` for the specification.
- Prompts: Store in `prompts/` directory (root dir) as markdown files. Load via `load_prompt()` from `core/prompt.py` (supports `{% include %}` and `{variable}` substitution). Reusable blocks in `prompts/shared/`.

IMPORTANT: NEVER implement a tool / MCP tool directly. Use either a toolkit or a connector (if it's a data tool).

## Library Documentation

For detailed code documentation (`core/`, `agents/`, `mcp/`, `a2a/`, `toolkits/`, `tools/`, `testing/`, etc.) see `docs/agentic_patterns.md` and its linked detail files in `docs/agentic_patterns/`. The `docs/agentic_patterns.md` file serves as the main entry point for documentation, linking to detailed sections for each module and component.

IMPORTANT: Instead of updating `CLAUDE.md` file, ALWAYS update `docs/agentic_patterns.md` and its linked detail files when making changes to the codebase's documentation.

Derived files `llms.txt` / `llms-full.txt` at the project root are generated by `scripts/llms_txt.sh` (NEVER EDIT `llms*txt` FILES!).

## Scripts

All scripts source `config.sh` (sets PROJECT_DIR, loads .env, activates .venv, sets PYTHONPATH):

- `make.sh` -- compile book to output/
- `test.sh` / `test_unit.sh` / `test_integration.sh` -- run tests
- `test_notebooks.sh` -- execute Jupyter notebooks as smoke tests (on-demand, not part of regular suite); optional arg for specific notebook relative path
- `evals.sh` -- run agent evaluations
- `lint.sh` -- run ruff linter
- `llms_txt.sh` -- generate `llms.txt` and `llms-full.txt` from `docs/agentic_patterns*`
- `release.sh` -- lint, tests, llms_txt, clean notebooks; `--bump <version>` to update version
- `db_ingest_bookstore_sqlite.sh` -- create and populate the bookstore SQLite database
- `annotate_schema.sh` -- add AI-generated descriptions to database schema
- `download_vocabularies.sh` -- download vocabulary files to data/vocabularies/
- `ingest_openapi.sh` -- parse and store OpenAPI specs
- `launch_infrastructure.sh` -- start MCP + A2A servers
- `clean_notebooks.sh` -- strip notebook outputs
- `build_repl_image.sh` -- build Docker image for sandboxed REPL execution

## Configuration

**config.yaml**: Single source of truth for all configuration. Sections: `models` (named LLM configs with provider, credentials, timeout), `embeddings`, `vectordb`, `auth` (jwt_secret, jwt_algorithm), `sandbox` (docker_host, named profiles like default/repl), `openapi`, `mcp_servers`, `a2a` (clients), `agents` (system prompts, tools, sub_agents). Use `config_example.yaml` as reference when adding new sections -- keep both files in sync.

**.env**: Only things that must be in environment variables for framework compatibility (e.g. `CHAINLIT_AUTH_SECRET` for Chainlit). Everything else MUST be in `config.yaml`.

**pyproject.toml**: Dependencies and console scripts (`doctors`, `evals`, `manage-users`, `annotate-schema`, `ingest-openapi`, `build-repl-image`).

**apis.yaml**: OpenAPI specs with `${VAR}` env expansion.

## Reference Documentation (`docs/`)

Consult these when working on related topics: `pydantic-ai.md`, `mcp.md`, `fastmcp.md`, `a2a_specification.md`, `agui.md`, `skills_specification.md`, `tasks.md`, `mcp_requirements.md`, `a2a_requirements.md`. Each links to detailed sections in subdirectories. These are READ-ONLY reference documents. 