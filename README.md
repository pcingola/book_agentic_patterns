# Book "Agentic Patterns"

This is a repository for the book "Agentic Patterns", which explores design patterns and best practices for building agentic systems using AI technologies.

- [Chapters](./chapters.md)
- [Topics](./topics.md)
- [References](./references.md)

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

