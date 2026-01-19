# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a repository for the book "Agentic Patterns", which explores design patterns and best practices for building agentic systems using AI technologies. The book is written in markdown with each chapter in its own directory.

## Repository Structure

```
book_agentic_patterns/
├── chapters/           # Book chapters (markdown files)
├── agentic_patterns/   # Python code examples
├── scripts/            # Build, validation, lint scripts
├── tests/              # Tests for code examples
└── docs/               # Generated documentation
```

## Conventions

**Chapter directories**: All chapters under `chapters/` directory. Name them `XX_descriptive_name` where XX is zero-padded (01, 02, etc.). Each chapter directory contains a `chapter.md` index file that links to individual section markdown files.

**Code organization**: All code in `agentic_patterns/`. Code examples are organized in numbered directories that loosely correspond to chapters. Code examples may be Python files (.py) or Jupyter notebooks (.ipynb). Core utilities shared across chapters go in `agentic_patterns/core/`. Follow global Python conventions (type hints, pathlib, etc.).

## Core Library (`agentic_patterns/core/`)

The core library provides reusable infrastructure for building AI agentic systems with PydanticAI.

### Module Structure

**agents/**: Agent instantiation and execution using PydanticAI. `get_agent()` creates agents from YAML-based model configurations. `run_agent()` executes agents with step-by-step logging. Supports multiple LLM providers: Azure OpenAI, AWS Bedrock, Ollama, OpenAI, and OpenRouter.

**config/**: Environment and project configuration. Discovers `.env` files across directory tree, manages project paths (WORKSPACE_DIR, PROMPTS_DIR, etc.), and provides smart defaults. Configuration adapts when core is used as a package in another project.

**tools/**: Tool management with permissions and AI-driven selection. `ToolPermission` enum (READ, WRITE, CONNECT) with `@tool_permission()` decorator. `ToolSelector` uses an agent to select relevant tools from a list based on user query. `func_to_description()` generates tool descriptions from function metadata.

**prompt.py**: Template-based prompt loading from markdown files. Supports variable substitution with `{variable_name}` syntax and validates required/extra variables.

**workspace.py**: Sandbox workspace isolation for multi-tenant scenarios. Translates between agent-visible paths (`/workspace/...`) to actual host filesystem paths per user/session. Includes path traversal protection.

### Key Patterns

The library uses async-first design, Pydantic models for configuration, functional composition via decorators, and context-aware request handling for user/session isolation.

**Images**: Stored within each chapter directory in an `img/` subdirectory. Reference from markdown using relative paths: `![Description](img/diagram.png)`. This keeps images co-located with their corresponding chapter content.

**Tests**: In `tests/` directory at root. Name test files to match chapters (`test_01.py`, `test_02.py`). Use standard Python unittest framework. Run via `scripts/test.sh`.

**Dependencies**: Single `pyproject.toml` or `requirements.txt` at root for all code examples. All chapters share the same dependency environment.

**Code imports**: When code in `agentic_patterns/XX/` imports from `agentic_patterns/core/`, ensure PYTHONPATH is set correctly or use relative imports. Consider adding `agentic_patterns/` to PYTHONPATH in scripts.

**Chapter numbering**: Using sequential numbers (01, 02, 03) makes reordering hard. If you plan to insert chapters later, consider leaving gaps (01, 05, 10, etc.) or non-sequential numbering.

**Image optimization**: Use compressed PNGs or SVGs for diagrams to keep repository size manageable. Large images bloat git history permanently.

**References**: All references and citations should be included in a `references.md` file