## First Steps

The introduction laid out a three-step progression: monolithic agent, distributed system, user interface. This section covers the first step -- two simple monolithic agents, each built by composing tools that already exist in the library.

A monolithic agent is a single `Agent` instance with all tools registered directly. There is no MCP, no A2A, no orchestration layer. The agent runs in a Jupyter notebook, receives a prompt, calls tools, and produces a result. This is deliberately minimal. The goal is to validate that the reasoning loop works, that the tools compose correctly, and that the agent can accomplish real tasks before introducing any infrastructure.

The building blocks come from three tool modules. The file tools (`agentic_patterns/tools/file.py`) provide nine operations for reading, writing, editing, searching, and listing files in the agent's workspace. The sandbox tools (`agentic_patterns/tools/sandbox.py`) provide one operation for executing shell commands inside a Docker container. The todo tools (`agentic_patterns/tools/todo.py`) provide six operations for creating, tracking, and updating task lists. All three modules follow the same pattern: a `get_all_tools()` function returns a list of plain functions that can be passed directly to PydanticAI's `Agent(tools=[...])`.

The two agents differ in which tools they receive and what their system prompt instructs:

**Agent V1 -- The Coder** combines file tools and sandbox tools (10 tools total). Its system prompt describes a workflow: write code to files, execute in the sandbox, inspect output. This is the CodeAct pattern from the core patterns chapter, but now with a persistent workspace and Docker isolation instead of an in-memory sandbox.

**Agent V2 -- The Planner** adds todo tools to the Coder's toolset (16 tools total). Its system prompt adds a planning step: before doing any work, break the task into steps using the task list. For each step, update the status as work progresses. This is the planning pattern composed with CodeAct -- the agent reasons about task decomposition before executing.

The progression from Coder to Planner demonstrates a principle that recurs throughout this chapter: adding capabilities to an agent is primarily a matter of adding tools and updating the system prompt. The reasoning loop, the model, the execution infrastructure -- all remain the same. The agent's behavior changes because it has new tools available and new instructions for when to use them.

Both agents use the same workspace and sandbox infrastructure. Files written by file tools land in a directory on the host filesystem (`WORKSPACE_DIR/user_id/session_id/`). The Docker sandbox mounts this same directory at `/workspace`, so a file written with `file_write("/workspace/script.py", ...)` is immediately available for execution with `sandbox_execute("python /workspace/script.py")`. This shared filesystem is the bridge between the agent's file manipulation and its code execution capabilities.
