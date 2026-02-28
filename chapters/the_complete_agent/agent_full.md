## Agent V5: The Full Agent

The Coordinator delegates work but always waits for the result before continuing. When two sub-agent tasks are independent -- say, querying a database and generating a chart -- running them sequentially wastes time. The Full Agent adds asynchronous delegation, allowing the coordinator to fire off multiple agents in parallel and collect results when they complete.

#### Foreground and Background Delegation

The Full Agent uses the same three delegation tools as V4 (`task_launch`, `task_output`, `task_stop`), but its prompt instructs the agent to use both foreground and background modes.

Foreground delegation via `task_launch(agent_name, prompt, description)` works exactly as in V4: launch the agent, wait for the result, return it as a string. This is the right choice when each step depends on the previous result.

Background delegation via `task_launch(agent_name, prompt, description, run_in_background=True)` returns immediately with an agent ID. The agent can launch multiple background agents, continue with other work, and then call `task_output(agent_id)` to retrieve results. By default `task_output` blocks until the agent completes, but it accepts `block=False` for non-blocking checks and a configurable `timeout`. The `task_stop(agent_id)` tool cancels a running background agent.

Between turns, the `OrchestratorAgent` automatically checks for completed background agents and prepends their results to the next prompt. The agent sees these as `[BACKGROUND AGENT COMPLETED: agent_name (id=...)]` messages, allowing it to reason about results even if it did not explicitly call `task_output`.

#### Tool Composition

The config is identical to V4 -- same tools, same sub-agents, different prompt:

```yaml
agents:
  full_agent:
    system_prompt: the_complete_agent/agent_full.md
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

The `OrchestratorAgent` generates `task_launch`, `task_output`, and `task_stop` tools whenever sub-agents are present -- the same tools as V4. The difference is that the Full Agent's prompt instructs the agent when to use background mode, while the Coordinator's prompt only mentions foreground delegation. The capability was always there; the prompt unlocks it.

#### Execution

The notebook demonstrates both modes. Turn 1 uses foreground delegation to query the bookstore database -- a single task where the agent needs the result immediately. This works identically to V4.

Turn 2 asks for two independent tasks: query the top five most expensive books, and generate a bar chart of average prices by genre. The agent calls `task_launch` with `run_in_background=True` for both, receiving agent IDs for each. Both agents start running concurrently. The agent then calls `task_output` for each to collect the results. Once results arrive, it writes a markdown report combining the findings.

#### The AgentRunner

All delegation -- both foreground and background -- flows through a single `AgentRunner`. The runner manages agent state, dispatches to local sub-agents as asyncio tasks or to remote A2A agents via HTTP, and provides a unified interface for launching, querying, and stopping agents. For local sub-agents, each execution instantiates a fresh `OrchestratorAgent` from the sub-agent's `AgentSpec`, runs it against the input, and stores the result. On `__aexit__`, the orchestrator calls `runner.cancel_all()` to clean up any still-running background agents.

The `AgentRunner` also handles the task coordination layer: it inherits the parent's `TaskList`, so child agents can see and manage the same set of tasks. This means a sub-agent can create tasks, update their status, and declare dependencies, all visible to the parent and to sibling agents.

#### The Monolithic Limit

The Full Agent is the most capable monolithic agent in this progression: direct tools for file I/O, sandbox execution, task management, and format conversion; delegation tools for sub-agents; skills loaded on demand; and concurrent agent execution. It remains a single `OrchestratorAgent` running from a notebook -- no MCP servers, no A2A protocol, no network calls.

This is deliberate. Everything built so far -- planning, skills, delegation, async agents -- works within a single process. The patterns are the same ones that will later drive the distributed system, but here they are validated without infrastructure complexity.

The full example is in `agentic_patterns/examples/the_complete_agent/example_agent_full.ipynb`.
