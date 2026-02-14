# Documentation

We'll write documentation of our "agentic_patterns" library (including tools, MCPs, A2As, etc.).

Audience: The documentation is for engineers who want to use our library to build agents.
Style: Technical, detailed but succinct. No fluff, no bullshit. Never use emojis. Use simple markdown formatting.
Paths: The documentation entry point is `docs/agentic_patterns.md`, and each topic is covered in `docs/agentic_patterns/*.md`
Reference: You can use the respective chapters (see `chapters.md`) to cover the specific topics.

Methodology: IMPLEMENT ONLY ONE TOPIC AT A TIME, AFTER FINISHING THE DOCUMENTATION FOR ONE TOPIC, YOU ARE DONE!
1. Check that the documentation doesn't already exist for the topic (in `docs/agentic_patterns/*.md`).
2. Read the chapter
3. Read the hands-on sections and the related code / notebooks. Pay attention to which part of the "agents patterns" library is being used in each section.
4. Write the documentation for that part of the library
5. Update `docs/agentic_patterns.md` to include the new documentation

IMPORTANT: If the chapter does NOT introduce any new code or library concepts, then we do NOT need to write documentation for it. For example, if the chapter is just about how to use the patterns together, then we can skip writing documentation for it.

## Getting Started

- [x] Foundations: `foundations.md` (from chapters/foundations and chapters/core_patterns)

## Core

- [x] Tools: `tools.md` (from chapters/tools)
- [x] Context & Memory: `context_memory.md` (from chapters/context_memory)
- [x] RAG: `rag.md` (from chapters/rag)

## Data Access

- [x] Connectors: `connectors.md` (file, CSV, JSON)
- [x] SQL: `sql.md` (SQL connector, NL2SQL, schema annotation)
- [x] OpenAPI: `openapi.md` (OpenAPI connector)
- [x] Vocabulary: `vocabulary.md` (vocabulary connector)
- [x] Toolkits: `toolkits.md` (todo, data analysis, data viz, format conversion)

## Agent Capabilities

- [x] MCP: `mcp.md` (from chapters/mcp)
- [x] A2A: `a2a.md` (from chapters/a2a)

## Composition

- [x] Skills, Sub-Agents & Tasks: `skills_sub_agents_tasks.md` (from chapters/skills_and_sub_agents, chapters/orchestration)
- [x] Domain Agents: `domain_agents.md`

## Quality & Testing

- [x] Evals: `evals.md` (from chapters/evals)

## Production

- [x] Execution Infrastructure: `execution_infrastructure.md` (from chapters/execution_infrastructure)
- [x] Compliance: `compliance.md` (private data, data sensitivity)
- [x] User Interface: `ui.md` (from chapters/ui)

Skipped (no new library concepts):
- Core Patterns: chapters/core_patterns -- reasoning patterns only, no new library code
- Orchestration: chapters/orchestration -- uses patterns documented in skills_sub_agents_tasks.md and a2a.md
- The Complete Agent: chapters/the_complete_agent -- uses existing patterns together

We'll mark as done each item once the documentation for that topic is complete.

Note: Some details might be in docs/CLAUDE.md

READ FILES MANUALLY, DO NOT IMPLEMENT ANY CODE OR RUN ANY COMMANDS.
