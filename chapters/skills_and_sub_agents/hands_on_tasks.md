## Hands-On: Tasks

This hands-on explores `example_tasks.ipynb`, which demonstrates how `OrchestratorAgent` uses tasks to coordinate parallel sub-agent execution. The orchestrator creates tasks with dependencies forming a DAG, runs independent tasks concurrently, and enforces that dependent tasks wait for their prerequisites.

### Agents and Roles

Three agents are defined using `AgentSpec`:

```python
researcher = AgentSpec(
    name="researcher",
    description="Researches a scientific topic and returns a concise summary of key findings.",
    system_prompt="You are a scientist. Answer concisely with key facts only.",
)

writer = AgentSpec(
    name="writer",
    description="Writes a short scientific article synthesizing research findings.",
    system_prompt="You are a science writer. Write concise, accurate prose.",
)

coordinator = AgentSpec(
    name="coordinator",
    system_prompt=(
        "You are a research coordinator. When given a topic, plan the work as tasks "
        "with dependencies, then execute by delegating to sub-agents."
    ),
    sub_agents=[researcher, writer],
)
```

The coordinator lists `researcher` and `writer` as its sub-agents. `OrchestratorAgent` wires these into the coordinator alongside task management tools (`task_create`, `task_get`, `task_list_all`, `task_update`) and agent runner tools (`task_launch`, `task_output`, `task_stop`).

### Running the Orchestrator

`OrchestratorAgent` is used as an async context manager:

```python
async with OrchestratorAgent(coordinator, verbose=True) as agent:
    result = await agent.run(
        "Research recent discoveries in particle physics and in cosmology, "
        "then write a short article connecting the two fields."
    )
    print(result.output)
```

Inside the context, the orchestrator builds the full system prompt and creates a `TaskList` backed by file storage. The coordinator agent receives both task tools and agent runner tools; it never touches the `TaskList` or `AgentRunner` directly — only through the exposed tool interface.

### What the Coordinator Does

Given the task, the coordinator reasons that it needs two independent research tasks and one writing task that depends on both. It creates them with explicit blocking relationships:

- Task 1: Research particle physics (no blockers)
- Task 2: Research cosmology (no blockers)
- Task 3: Write the article (blocked by tasks 1 and 2)

Tasks 1 and 2 have no blockers, so the coordinator launches them in parallel via `task_launch`. Task 3 remains `pending` until both reach `completed`. Once both research tasks finish, task 3 becomes available and the coordinator delegates it to the writer.

### Task Lifecycle in the Output

With `verbose=True`, the task list is printed after every state change. You can follow each transition:

```
pending --> in_progress --> completed
```

`[BACKGROUND AGENT COMPLETED]` markers show when parallel sub-agents finish and their results are injected into the coordinator's next turn. The coordinator then picks up the next available task automatically.

### Task System and Sub-Agent System Are Separate

Tasks track what needs to be done and in what order. The `AgentRunner` handles execution. `OrchestratorAgent` wires both together: the coordinator uses task tools to plan and track work, and agent runner tools to launch and observe sub-agents. The underlying `core/tasks/` module — `TaskStatus`, `Task`, `TaskList`, `get_task_tools()` — is what the orchestrator builds on, but the coordinator interacts with it only through tool calls, not directly.
