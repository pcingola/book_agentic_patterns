# Agentic Patterns

A comprehensive book on design patterns and best practices for building agentic systems using Large Language Models (LLMs) and related AI technologies.

## What This Book Is About

This book provides both theoretical foundations and practical guidance for building AI agents that can reason, use tools, and collaborate to accomplish complex tasks. It covers the full spectrum of agentic development, from foundational reasoning patterns like Chain-of-Thought and ReAct, through tool use and orchestration, to advanced topics like multi-agent coordination protocols (MCP, A2A), evaluation frameworks, and production infrastructure.

Each chapter combines conceptual explanations with hands-on exercises, allowing readers to immediately apply what they learn. The accompanying code library provides reusable infrastructure for building real-world agentic applications.

## Goal

Build a proof-of-concept agentic platform using established patterns and best practices. While we won't build a full enterprise system, readers will learn the architectural principles and implementation techniques needed to design, implement, test, and operate AI agent systems that can evolve into production-ready solutions.

## Target Audience

Software engineers and ML practitioners with experience in AI/ML and software development who want to build agentic systems. Familiarity with Python and basic LLM concepts is assumed.

## Contents

- [Chapters](./chapters.md)

## CLI Tools

The `doctors` command provides AI-powered analysis for prompts, tools, MCP servers, and A2A agent cards.

```bash
uv pip install -e .
doctors prompt prompts/system.md
doctors tool my_module:my_tools
doctors mcp --url http://localhost:8000/mcp
doctors a2a http://localhost:8001/.well-known/agent.json
```

Run `doctors --help` for all options.

