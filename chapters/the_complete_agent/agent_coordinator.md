## Agent V4: The Coordinator

If we add data analysis operations, SQL queries, visualization tools, and vocabulary lookups directly to the Skilled agent, the tool list explodes. Worse, the agent must choose among all of them on every turn, even when a task clearly belongs to one domain. The Coordinator solves tool explosion by delegating to sub-agents instead of absorbing their tools.

### Delegation Over Accumulation

Instead of giving the coordinator SQL tools, it gets a sub-agent that has SQL tools. Instead of giving it data analysis operations, it gets a sub-agent that has those operations. The coordinator decides *who* should handle a task; the sub-agent decides *how*.

Each sub-agent is defined as an `AgentSpec` with its own name, description, system prompt, and tool list. The data analysis sub-agent has file, CSV, JSON, data analysis, data visualization, and REPL tools. The SQL sub-agent has file, CSV, and SQL tools. The vocabulary sub-agent has vocabulary resolution tools. Each runs in its own context with its own instructions, isolated from the coordinator's concerns.

### Tool Composition

The coordinator's config adds format conversion tools and declares sub-agents:

```yaml
agents:
  coordinator:
    system_prompt: the_complete_agent/agent_coordinator.md
    tools:
      - agentic_patterns.tools.file:get_all_tools
      - agentic_patterns.tools.sandbox:get_all_tools
      - agentic_patterns.tools.todo:get_all_tools
      - agentic_patterns.tools.format_conversion:get_all_tools
    sub_agents:
      - agentic_patterns.agents.data_analysis:get_spec
      - agentic_patterns.agents.sql:get_spec
      - agentic_patterns.agents.vocabulary:get_spec
```

Each `sub_agents` entry points to a `get_spec()` factory that returns an `AgentSpec` with its own name, description, system prompt, and tool list. The notebook loads everything with `AgentSpec.from_config("coordinator")`.

When `sub_agents` is non-empty, the `OrchestratorAgent` creates a `TaskBroker` internally and auto-generates a `delegate` tool. It also injects a sub-agent catalog into the system prompt via `{% include 'shared/sub_agents.md' %}`, listing each sub-agent's name and description so the agent knows who to call.

The coordinator's direct tools handle file I/O, sandbox execution, task management, skills, and format conversion (`convert_document` for transforming documents between PDF, DOCX, MD, CSV, and other formats). Domain-specific work routes through delegation. The coordinator has far more capabilities than the Skilled agent but fewer tools than it would need if every capability were a direct tool.

### Execution

The notebook demonstrates two turns against a bookstore database. Turn 1 asks the coordinator to query genre statistics and save results to CSV. The coordinator calls `delegate("sql_analyst", ...)` with a specific prompt. The broker creates a sub-agent from the SQL spec, runs it with SQL tools and schema context, and returns the result as a string. The coordinator then uses its own file tools to save the CSV.

Turn 2 asks for a markdown report with a bar chart, converted to PDF. This mixes delegation and direct work: the coordinator delegates chart generation to the data analyst sub-agent (which has visualization tools), writes the report itself (file tools), and converts it to PDF (format conversion tool). The planning pattern from V2 still applies -- the agent creates a todo list, tracks each step, and reports the final state.

### How Delegation Works

The `delegate` tool is synchronous from the agent's perspective: it submits a task to the broker, waits for the result, and returns it as a string. Under the hood, the broker dispatches the task to a `Worker`, which instantiates a fresh `OrchestratorAgent` from the sub-agent's `AgentSpec`, runs it, and collects the output. Each sub-agent gets its own context window, its own tool set, and its own reasoning trace. The coordinator never sees the sub-agent's intermediate steps -- only the final result.

This separation matters. The SQL sub-agent can reason about schemas, validate queries, and retry on syntax errors without those details leaking into the coordinator's context. The data analysis sub-agent can iterate on DataFrame operations without cluttering the coordinator's message history. Each agent stays focused on its domain.

The full example is in `agentic_patterns/examples/the_complete_agent/example_agent_coordinator.ipynb`.
