## Agent V2: The Planner

The Planner extends the Coder with task management. It receives the same file and sandbox tools, plus todo tools for creating and tracking a task list. The important change is in the system prompt: the agent is now instructed to plan before executing.

### System Prompt

The prompt (`prompts/the_complete_agent/agent_planner.md`) adds two sections to the Coder's prompt. The task management section explains the todo tools and instructs the agent to break work into steps before starting. The workflow section is reordered: plan first, then for each step update its status, do the work, and mark it completed.

This is a small change in prompt text but a significant change in agent behavior. The Coder dives straight into writing code. The Planner stops, decomposes the task, creates a visible plan, and then executes against it. The plan serves two purposes: it gives the agent a structure to follow (reducing the chance of forgetting steps in a complex task), and it gives the user visibility into what the agent intends to do.

### Tool Composition

The only code difference from the Coder is the addition of todo tools:

```python
system_prompt = load_prompt(PROMPTS_DIR / "the_complete_agent" / "agent_planner.md")

tools = get_file_tools() + get_sandbox_tools() + get_todo_tools()
agent = get_agent(system_prompt=system_prompt, tools=tools)
```

`get_todo_tools()` provides functions for creating lists, adding items, updating status, and displaying the plan. Items have hierarchical IDs (e.g., "1", "1.1", "1.2") and four possible states: pending, in_progress, completed, and failed.

### Execution

When given a multi-step task -- for example, "create a CSV file with sales data, write a processing script, execute it, and verify the results" -- the Planner's execution trace shows a different structure than the Coder's.

The agent first calls `todo_create_list` with descriptions for each step. It then iterates through the list: calling `todo_update_status` to mark each step as in_progress, performing the work (file writes, sandbox execution), and marking the step as completed. At the end, it calls `todo_show` to display the final state. The result is a checklist showing all steps completed.

This pattern scales better to complex tasks. The Coder might lose track of subtasks in a long execution, especially if errors require backtracking. The Planner maintains an explicit record of what has been done and what remains.

### From Coder to Planner

The two agents illustrate a pattern: the same reasoning loop, given more tools and a revised prompt, produces qualitatively different behavior. The Coder is reactive (write, execute, check). The Planner is proactive (plan, then execute against the plan). Neither required changes to the agent infrastructure, the model configuration, or the execution pipeline. The difference is entirely in the tools and the prompt.

This is also the limit of what a flat tool list can handle well. As we add more capabilities -- data analysis, document conversion, API access, vocabulary resolution -- the tool list grows, the system prompt becomes longer, and the agent must choose from an increasingly large set of options on every turn. The next sections address this with progressive disclosure and delegation.

The full example is in `agentic_patterns/examples/the_complete_agent/example_agent_planner.ipynb`.
