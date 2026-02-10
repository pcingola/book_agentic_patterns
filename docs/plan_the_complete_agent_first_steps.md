# Plan: "First Steps" Section of The Complete Agent Chapter

## Context

The Complete Agent chapter builds a full agent progressively. The introduction (already written) establishes a three-step progression: monolithic -> distributed -> UI. This plan covers the "First Steps" sub-section: two simple monolithic agents, each composing existing tools. Each agent gets its own notebook and markdown file.

Since the entire chapter is hands-on, files follow the `{topic}.md` / `example_{topic}.ipynb` convention (no `hands_on_` prefix).

All building blocks already exist. No new library code needed.

## Deliverables

### 1. `agentic_patterns/examples/the_complete_agent/example_agent_coder.ipynb`

Agent V1 -- "The Coder": File tools + Sandbox tools.

- System prompt: coding assistant that writes files to workspace and executes them in Docker sandbox
- Tools: `get_file_tools() + get_sandbox_tools()` (11 tools)
- Task: Write a Python script, save to workspace, execute via `sandbox_execute("python /workspace/script.py")`, verify output
- Demonstrates: CodeAct pattern with workspace persistence and Docker isolation

### 2. `agentic_patterns/examples/the_complete_agent/example_agent_planner.ipynb`

Agent V2 -- "The Planner": File tools + Sandbox tools + Todo tools.

- System prompt: updated to instruct planning before execution
- Tools: V1 tools + `get_todo_tools()` (17 tools)
- Task: Multi-step task requiring planning (create CSV, write processing script, execute, verify)
- Demonstrates: Planning pattern combined with CodeAct

### 3. `chapters/the_complete_agent/first_steps.md`

Short conceptual section introducing the "first steps" approach: why start monolithic, what tools we compose, the progression from coder to planner.

### 4. `chapters/the_complete_agent/agent_coder.md`

Narrative explaining Agent V1, with code snippets. References `example_agent_coder.ipynb`.

### 5. `chapters/the_complete_agent/agent_planner.md`

Narrative explaining Agent V2, with code snippets. References `example_agent_planner.ipynb`.

### 6. `chapters/the_complete_agent/chapter.md`

Create the chapter index linking: introduction.md, first_steps.md, agent_coder.md, agent_planner.md.

## Key Files (existing, reused as-is)

- `agentic_patterns/tools/file.py` -- 9 file tools
- `agentic_patterns/tools/sandbox.py` -- 2 sandbox tools (Docker)
- `agentic_patterns/tools/todo.py` -- 6 todo tools
- `agentic_patterns/core/agents/agents.py` -- `get_agent()`, `run_agent()`
- `agentic_patterns/core/user_session.py` -- `set_user_session()`

## Important Details

- Docker sandbox mounts `WORKSPACE_DIR/user_id/session_id` at `/workspace` inside the container
- Files written by file tools are accessible inside the sandbox at the same `/workspace/...` path
- Docker must be running (prerequisite)

## Order of Work

1. Create `example_agent_coder.ipynb`, verify it runs
2. Create `example_agent_planner.ipynb`, verify it runs
3. Write `first_steps.md` (conceptual intro)
4. Write `agent_coder.md`
5. Write `agent_planner.md`
6. Create `chapter.md`

## Verification

1. Ensure Docker is running
2. Run `example_agent_coder.ipynb` -- agent writes a file, executes it in sandbox, reports output
3. Run `example_agent_planner.ipynb` -- agent creates task list, executes tasks, updates status
