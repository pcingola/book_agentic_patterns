# Plan: Local Sub-Agents (A2A-equivalent, no network)

## Problem

The A2A servers (`a2a/data_analysis/`, `a2a/nl2sql/`) are designed for distributed deployment: each agent runs as a separate HTTP service, tools are exposed via MCP servers, and coordination happens over the network via A2A protocol. This is overkill for local development on a laptop -- you need to start multiple MCP servers and A2A servers just to run a multi-agent workflow.

## Goal

Create sub-agents that provide the same functionality as the A2A servers but with tools connected directly (via `tools/` wrappers), so everything runs in a single process with no HTTP, no MCP, no A2A overhead.

## Current Architecture (distributed)

```
Coordinator  --A2A-->  A2A Server (data_analysis)  --MCP-->  MCP Server  -->  toolkits/
             --A2A-->  A2A Server (nl2sql)          --MCP-->  MCP Server  -->  connectors/sql/
```

Each hop is an HTTP round-trip. Three processes minimum.

## Target Architecture (local)

```
Coordinator agent
    |
    +-- delegation tool --> Data Analysis sub-agent (tools from tools/data_analysis.py)
    +-- delegation tool --> NL2SQL sub-agent         (tools from tools/sql.py)
```

Single process. No servers. Same prompts, same tools, same behavior.

## Design

### Sub-agent factory

A single function that creates a PydanticAI agent with tools connected directly:

```python
# agentic_patterns/sub_agents/data_analysis.py

from agentic_patterns.core.agents import get_agent
from agentic_patterns.core.prompt import load_prompt
from agentic_patterns.tools.data_analysis import get_all_tools

def create_agent() -> Agent:
    prompt = load_prompt(PROMPTS_DIR / "a2a" / "data_analysis" / "system_prompt.md")
    return get_agent(tools=get_all_tools(), instructions=prompt)
```

Same pattern for NL2SQL. Each file is tiny -- just wires together an existing prompt with existing direct tools.

### Delegation tools for the coordinator

Following the fixed sub-agents pattern from `examples/sub_agents/`, each sub-agent gets a delegation tool:

```python
async def ask_data_analyst(ctx: RunContext, prompt: str) -> str:
    """Delegate a data analysis task to the Data Analysis sub-agent."""
    agent = create_data_analysis_agent()
    agent_run, _ = await run_agent(agent, prompt)
    ctx.usage.incr(agent_run.result.usage())
    return agent_run.result.output
```

### Coordinator

A coordinator agent that has delegation tools as its tools. Reuses `build_coordinator_prompt()` style or a dedicated system prompt that describes what each sub-agent can do.

### Reusing existing prompts

The A2A system prompts (`prompts/a2a/data_analysis/system_prompt.md`, `prompts/a2a/nl2sql/system_prompt.md`) work as-is. They describe the agent's capabilities and workflow -- nothing in them is A2A-specific. The sub-agents reuse them directly.

## Directory Layout

```
agentic_patterns/
+-- sub_agents/
    +-- data_analysis.py      create_agent() using tools/data_analysis.py + existing prompt
    +-- nl2sql.py             create_agent() using tools/sql.py + existing prompt
    +-- coordinator.py        create_coordinator() with delegation tools for both sub-agents
```

Three small files. No new abstractions.

## What Gets Reused

| Component | Source | Used by both A2A and sub-agent |
|-----------|--------|-------------------------------|
| Business logic | `toolkits/data_analysis/`, `connectors/sql/` | Yes (unchanged) |
| Direct tool wrappers | `tools/data_analysis.py`, `tools/sql.py` | Sub-agents only |
| MCP tool wrappers | `mcp/data_analysis/tools.py`, `mcp/sql/tools.py` | A2A servers only |
| System prompts | `prompts/a2a/*/system_prompt.md` | Yes (shared) |
| Agent creation | `core/agents/agents.py` | Yes (unchanged) |

## Execution Order

1. Create `sub_agents/data_analysis.py` -- `create_agent()` function
2. Create `sub_agents/nl2sql.py` -- `create_agent()` function
3. Create `sub_agents/coordinator.py` -- `create_coordinator()` with delegation tools
4. Add an example notebook showing the coordinator running locally
