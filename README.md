# Agentic Patterns

A book on design patterns and best practices for building agentic systems with LLMs. It combines theoretical foundations with hands-on implementation, moving from foundational reasoning patterns (CoT, ReAct) through tool use, orchestration, and multi-agent protocols (MCP, A2A) to evaluation and production infrastructure. All code uses PydanticAI.

[Read the book (PDF)](output/book.pdf)

## Goal

Build a proof-of-concept agentic platform using established patterns and best practices -- not a full enterprise system, but one that teaches the architectural principles needed to design, implement, test, and operate AI agent systems that can evolve into production-ready solutions.

## Audience

Software engineers and ML practitioners who want to build agentic systems. Familiarity with Python and basic LLM concepts is assumed.

## Chapters

The book is organized in two sections. The first covers the building blocks: reasoning patterns, tool use, context management, orchestration, retrieval, and the two inter-agent protocols (MCP and A2A). The second section puts those blocks together into production systems: evaluation, data connectors, execution infrastructure, user interfaces, and a complete agent built incrementally from simple to fully distributed.

| # | Chapter | Topic |
|---|---------|-------|
| 1 | [Foundations](chapters/foundations/chapter.md) | What agentic systems are, how they differ from traditional software, modularity and design principles |
| 2 | [Core Patterns](chapters/core_patterns/chapter.md) | Zero-shot, few-shot, CoT, ToT, ReAct, CodeAct, self-reflection, verification, planning, human-in-the-loop |
| 3 | [Tools](chapters/tools/chapter.md) | Tool use, structured output, discovery, schemas, permissions, workspaces, intro to MCP |
| 4 | [Orchestration & Control Flow](chapters/orchestration/chapter.md) | Workflows, graphs, delegation, hand-off, long-running tasks, event-driven agents |
| 5 | [RAG](chapters/rag/chapter.md) | Embeddings, vector databases, document ingestion and retrieval, evaluation, attribution |
| 6 | [Context & Memory](chapters/context_memory/chapter.md) | Prompt layering, context engineering, compression, token budgeting, write-back patterns |
| 7 | [MCP](chapters/mcp/chapter.md) | Model Context Protocol: architecture, tools, prompts, resources, sampling, transport |
| 8 | [A2A](chapters/a2a/chapter.md) | Agent-to-Agent protocol: discovery, tasks, message exchange, security |
| 9 | [Skills, Sub-Agents & Tasks](chapters/skills_and_sub_agents/chapter.md) | Sub-agent delegation, skill packaging, task lifecycle, composition comparison |
| 10 | [Evals](chapters/evals/chapter.md) | Deterministic testing, eval frameworks, custom evaluators, AI-powered quality analyzers |
| 11 | [Data Sources & Connectors](chapters/data_sources_and_connectors/chapter.md) | SQL, OpenAPI, file, and vocabulary connectors; NL2SQL; private data guardrails |
| 12 | [User Interface](chapters/ui/chapter.md) | Chainlit, AG-UI protocol, error propagation, session identity, file uploads |
| 13 | [Execution Infrastructure](chapters/execution_infrastructure/chapter.md) | Sandbox, REPL, MCP server isolation, skill sandboxing |
| 14 | [The Complete Agent](chapters/the_complete_agent/chapter.md) | Five progressive agent variants, then decomposition into distributed MCP/A2A services |

Full table of contents with section-level detail: [chapters.md](chapters.md)

## Library Documentation

API and module documentation for the `agentic_patterns` library: [docs/agentic_patterns.md](docs/agentic_patterns.md)

## Repository Structure

```
chapters/              Book chapters (markdown)
agentic_patterns/      Python code
  core/                Reusable infrastructure
  agents/              Domain-specific agents
  toolkits/            Business logic (no framework dependency)
  tools/               PydanticAI tool wrappers
  mcp/                 MCP server wrappers
  examples/            Code examples by chapter
  testing/             Testing utilities
prompts/               Prompt templates
tests/                 Unit and integration tests
scripts/               Build, validation, lint scripts
docs/                  Reference documentation
output/                Generated book (book.md, book.pdf)
```

## Setup

```bash
uv pip install -e .
```

## Building the Book

```bash
scripts/make.sh        # generates output/book.md and output/book.pdf
```

## Running Tests

```bash
scripts/test.sh        # runs unit + integration tests
```

## CLI Tools

The `doctors` command provides AI-powered analysis for prompts, tools, MCP servers, A2A agent cards, and skills.

```bash
doctors prompt prompts/system.md
doctors tool my_module:my_tools
doctors mcp --url http://localhost:8000/mcp
doctors a2a http://localhost:8001/.well-known/agent.json
doctors skill path/to/skill/
```

Run `doctors --help` for all options.
