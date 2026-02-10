## Agent V1: The Coder

The Coder is the simplest useful agent: it writes files and executes them. Its ten tools come from two modules -- file operations for workspace I/O and a sandbox for Docker execution.

### System Prompt

The prompt (`prompts/the_complete_agent/agent_coder.md`) establishes three things: where files live, how execution works, and what workflow to follow.

The workspace section tells the agent that `/workspace/` is its persistent storage and that all paths are relative to it. The sandbox section explains that files written with file tools are immediately available for execution because the Docker container mounts the same directory. The workflow section gives a simple loop: write code, execute, inspect output, fix errors.

This prompt is intentionally short. The agent does not need detailed instructions about each tool because PydanticAI injects tool descriptions automatically from the function docstrings. The prompt's job is to explain the environment and the workflow -- the tools explain themselves.

### Tool Composition

Building the agent requires loading the prompt, collecting tools from both modules, and passing them to `get_agent()`:

```python
system_prompt = load_prompt(PROMPTS_DIR / "the_complete_agent" / "agent_coder.md")

tools = get_file_tools() + get_sandbox_tools()
agent = get_agent(system_prompt=system_prompt, tools=tools)
```

The `get_file_tools()` call returns nine functions (file_read, file_head, file_tail, file_find, file_list, file_write, file_append, file_edit, file_delete). The `get_sandbox_tools()` call returns one function (sandbox_execute). Plain list concatenation produces the full tool list. No registration, no configuration -- just functions.

### Execution

Running the agent is a single call:

```python
agent_run, nodes = await run_agent(agent, prompt, verbose=True)
```

The `verbose=True` flag logs each step of the agent's execution: tool calls, tool results, and the final output. The `nodes` list captures the full execution trace for inspection.

When given a task like "write a Fibonacci script, save it, and run it", the agent typically follows a predictable pattern. It calls `file_write` to create the script in `/workspace/`, then calls `sandbox_execute` to run it inside Docker, and finally reports the output. If the script fails (syntax error, runtime error), the agent sees the error in the sandbox output and can iterate -- reading the file, fixing the issue, and re-executing.

### What This Demonstrates

The Coder implements the CodeAct pattern from the core patterns chapter, but with real infrastructure instead of an in-memory sandbox. The workspace persists across tool calls, the sandbox provides Docker isolation, and the file tools give the agent fine-grained control over its files. The agent can write, read, edit, search, and delete files -- not just create them.

The full example is in `agentic_patterns/examples/the_complete_agent/example_agent_coder.ipynb`.
