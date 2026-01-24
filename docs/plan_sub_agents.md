# Plan: Sub-Agents Library (`agentic_patterns/core/subagents/`)

## Core concept

A sub-agent inherits everything from the parent (tools, MCP, A2A, skills). What makes it a sub-agent is its own system_prompt and fresh conversation context.

## Implementation

A single function in `runner.py`:

```python
def run_subagent(system_prompt: str, user_prompt: str, instructions: str | None = None) -> str:
    """Run a sub-agent with isolated context."""
```

The parent provides:
- `system_prompt` - defines the sub-agent's role
- `user_prompt` - the task to perform
- `instructions` - additional context (optional)

The sub-agent inherits the parent's tools, MCP, A2A, and skills. It runs with fresh conversation context and returns only its result.
