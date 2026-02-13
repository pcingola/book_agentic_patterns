## Agent V5: The Full Agent

The Coordinator delegates work but always waits for the result before continuing. When two sub-agent tasks are independent -- say, querying a database and generating a chart -- running them sequentially wastes time. The Full Agent adds asynchronous task submission, allowing the coordinator to fire off multiple tasks in parallel and collect results when they complete.

#### Two Modes of Delegation

The Full Agent's prompt (`prompts/the_complete_agent/agent_full.md`) describes two delegation modes. Synchronous delegation via `delegate(agent_name, prompt)` works exactly as in V4: submit a task, block until the result arrives, return it as a string. This is the right choice when each step depends on the previous result.

Asynchronous delegation via `submit_task(agent_name, prompt)` returns immediately with a task ID. The agent can submit multiple tasks, continue with other work, and then call `wait(timeout)` to block until background tasks complete. The `wait` tool is event-driven -- it does not poll. It sleeps until the broker signals that a task has finished or the timeout fires, avoiding unnecessary round-trips.

Between turns, the `OrchestratorAgent` automatically checks for completed background tasks and prepends their results to the next prompt. The agent sees these as `[BACKGROUND TASK COMPLETED: agent_name]` messages, allowing it to reason about results even if it did not explicitly call `wait`.

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

The `OrchestratorAgent` generates `delegate`, `submit_task`, and `wait` tools whenever sub-agents are present. The difference is that the Full Agent's prompt instructs the agent when to use each mode, while the Coordinator's prompt only mentions `delegate`. The capability was always there; the prompt unlocks it.

#### Execution

The notebook demonstrates both modes. Turn 1 uses synchronous delegation to query the bookstore database -- a single task where the agent needs the result immediately. This works identically to V4.

Turn 2 asks for two independent tasks: query the top five most expensive books, and generate a bar chart of average prices by genre. The agent calls `submit_task("sql_analyst", ...)` and `submit_task("data_analyst", ...)` in sequence, receiving task IDs for each. Both tasks start running concurrently through the broker. The agent then calls `wait` to block until both complete. Once results arrive, it writes a markdown report combining the findings.

#### The Task Broker

All delegation -- both synchronous and asynchronous -- flows through a single `TaskBroker` backed by an in-memory `TaskStoreMemory`. The broker manages task state (pending, running, completed, failed, cancelled), dispatches tasks to workers as background coroutines, and signals completion via an `asyncio.Event`. The `delegate` tool is simply `submit_task` followed by `wait` for that single task -- there is no separate code path.

Each worker instantiates a fresh `OrchestratorAgent` from the sub-agent's `AgentSpec`, runs it against the task input, and stores the result. Workers emit progress events (tool calls) and log events (reasoning) that accumulate on the task object, providing a full execution trace for debugging. On `__aexit__`, the orchestrator calls `broker.cancel_all()` to clean up any still-running background tasks.

#### The Monolithic Limit

The Full Agent is the most capable monolithic agent in this progression: direct tools for file I/O, sandbox execution, task management, and format conversion; delegation tools for sub-agents; skills loaded on demand; and concurrent task execution. It remains a single `OrchestratorAgent` running from a notebook -- no MCP servers, no A2A protocol, no network calls.

This is deliberate. Everything built so far -- planning, skills, delegation, async tasks -- works within a single process. The patterns are the same ones that will later drive the distributed system, but here they are validated without infrastructure complexity.

The full example is in `agentic_patterns/examples/the_complete_agent/example_agent_full.ipynb`.
