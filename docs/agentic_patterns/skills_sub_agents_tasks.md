# Skills, Sub-Agents & Tasks

Sub-agents decompose work within a single process by giving each child its own context, prompt, and tools. Skills package reusable agent capabilities as discoverable artifacts with progressive disclosure. Tasks wrap sub-agent execution with durable state, observation, and lifecycle control. These three patterns work together: `OrchestratorAgent` composes them declaratively via `AgentSpec`.

All infrastructure lives in `agentic_patterns.core.agents.orchestrator` (AgentSpec, OrchestratorAgent), `agentic_patterns.core.skills` (registry, models, tools), and `agentic_patterns.core.tasks` (broker, worker, store, models).


## Sub-Agents

A sub-agent is a PydanticAI `Agent` created and run by a parent agent to handle a scoped task. Each sub-agent has its own system prompt, tools, and context window. The parent delegates via tool calls and integrates results.

### Fixed sub-agents

Create specialized agents up front and expose them as tools on the coordinator:

```python
from pydantic import BaseModel, Field
from agentic_patterns.core.agents import get_agent, run_agent

class Summary(BaseModel):
    summary: str = Field(description="2-3 sentence summary")

summarizer = get_agent(
    output_type=Summary,
    system_prompt="You are a summarization specialist."
)

async def get_summary(ctx: RunContext[None], document: str) -> str:
    """Delegate to summarizer sub-agent."""
    agent_run, _ = await run_agent(summarizer, f"Summarize:\n\n{document}")
    ctx.usage.incr(agent_run.result.usage())
    return agent_run.result.output.summary

coordinator = get_agent(
    tools=[get_summary],
    system_prompt="You are a document analysis coordinator."
)
```

The `ctx.usage.incr()` call propagates the sub-agent's token usage to the coordinator's totals, so usage tracking remains accurate across delegation boundaries.

### Dynamic sub-agents

Let the coordinator create sub-agents at runtime with arbitrary system prompts:

```python
async def run_sub_agent(ctx: RunContext[None], system_prompt: str, task: str) -> str:
    """Create and run a sub-agent with the given system prompt."""
    sub_agent = get_agent(system_prompt=system_prompt)
    agent_run, _ = await run_agent(sub_agent, task)
    ctx.usage.incr(agent_run.result.usage())
    return agent_run.result.output

coordinator = get_agent(
    tools=[run_sub_agent],
    system_prompt="Break problems down and delegate to specialized sub-agents."
)
```

The coordinator decides what specialists to create and what system prompts to give them, adapting to any problem domain.


## Skills

Skills are packaged capability definitions that agents load on demand. A skill is a directory containing a `SKILL.md` file with YAML frontmatter and markdown instructions, plus optional supporting files.

### Directory structure

```
skills/
  code-review/
    SKILL.md              # Required: frontmatter + instructions
    scripts/              # Optional: executable scripts
    references/           # Optional: reference documents
    assets/               # Optional: static resources
```

### SKILL.md format

```yaml
---
name: code-review
description: Review code for quality, bugs, and security issues.
compatibility: Works with Python, JavaScript, and TypeScript files.
metadata:
  author: example-org
  version: "1.0"
---

# Code Review

## When to use this skill
Use when the task involves reviewing code for quality, bugs, or security.

## How to use
Analyze the provided code and return structured feedback.
```

Required frontmatter fields: `name` (1-64 chars, lowercase alphanumeric and hyphens) and `description` (1-1024 chars). Optional fields: `license`, `compatibility`, `metadata`, `allowed-tools`.

### Progressive disclosure

Skills use a three-tier loading strategy to minimize context consumption:

**Tier 1 -- Discovery (cheap).** `SkillRegistry.discover()` scans directories for `SKILL.md` files and extracts only the `name` and `description` from frontmatter. This produces `SkillMetadata` objects (~100 tokens each) that are injected into the system prompt as a catalog.

**Tier 2 -- Activation (expensive).** When the agent calls `activate_skill(name)`, the full `SKILL.md` body is loaded via `SkillRegistry.get()`. This returns a `Skill` object with the complete markdown instructions, frontmatter, and paths to scripts/references/assets.

**Tier 3 -- Resources (on demand).** Files in `scripts/`, `references/`, and `assets/` are only accessed when the agent explicitly reads or executes them.

### SkillRegistry

```python
from pathlib import Path
from agentic_patterns.core.skills.registry import SkillRegistry
from agentic_patterns.core.skills.tools import list_available_skills, get_skill_instructions

registry = SkillRegistry()
metadata = registry.discover([Path("skills/")])   # Tier 1: scan and cache
catalog = list_available_skills(registry)          # "name: description\n..."

skill = registry.get("code-review")               # Tier 2: load full skill
instructions = get_skill_instructions(registry, "code-review")  # skill.body
```

`SkillMetadata` holds `name`, `description`, and `path`. `Skill` adds `frontmatter` (full YAML dict), `body` (markdown string), and `script_paths`, `reference_paths`, `asset_paths` (lists of `Path`).

### Skill tools

`get_all_tools(registry)` returns an `activate_skill` function for use as a PydanticAI tool:

```python
from agentic_patterns.core.skills.tools import get_all_tools

tools = get_all_tools(registry)
agent = get_agent(tools=tools, system_prompt=f"Available skills:\n{catalog}")
```

When called, `activate_skill(skill_name)` returns the full SKILL.md body. If the skill is not found, it returns an error message.

### Skill sandbox

`create_skill_sandbox_manager(registry)` creates a `SandboxManager` with read-only mounts for all discovered skill script directories. Use `run_skill_script()` to execute a skill's bundled scripts inside the container:

```python
from agentic_patterns.core.skills.tools import create_skill_sandbox_manager, run_skill_script

manager = create_skill_sandbox_manager(registry)
exit_code, output = run_skill_script(
    manager, registry, user_id, session_id,
    skill_name="code-review", script_name="analyze.py", args="main.py"
)
```


## Tasks

The task system wraps sub-agent execution with durable state, background dispatch, and observation channels. It enables fire-and-forget delegation where the coordinator continues reasoning while sub-agents work in the background.

### State machine

```
pending --> running --> completed
               |-----> failed
               |-----> cancelled
         |---> cancelled
```

`TaskState` enum values: `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, `INPUT_REQUIRED`, `CANCELLED`. Terminal states: `COMPLETED`, `FAILED`, `CANCELLED`.

### Task model

```python
from agentic_patterns.core.tasks.models import Task, TaskEvent, EventType

task = Task(input="Analyze this dataset")
# task.id: auto-generated UUID
# task.state: TaskState.PENDING
# task.result: None (set on completion)
# task.error: None (set on failure)
# task.events: [] (state changes, progress, logs)
# task.metadata: {} (carries agent_name, system_prompt, config_name)
```

`TaskEvent` records state transitions and progress. `EventType` values: `STATE_CHANGE`, `PROGRESS`, `LOG`.

### Task storage

`TaskStore` is the abstract persistence interface with two implementations:

`TaskStoreMemory` -- in-memory dict-backed, no filesystem access. Ideal for notebooks and tests.

`TaskStoreJson` -- one JSON file per task in `DATA_DIR/tasks/`. Survives process restarts.

Both implement: `create()`, `get()`, `update_state()`, `list_by_state()`, `next_pending()`, `add_event()`.

### TaskBroker

`TaskBroker` coordinates task submission, dispatch, and observation. It runs a background dispatch loop that picks pending tasks and hands them to a `Worker` for execution.

```python
from agentic_patterns.core.tasks.broker import TaskBroker
from agentic_patterns.core.tasks.store import TaskStoreMemory

async with TaskBroker(store=TaskStoreMemory()) as broker:
    task_id = await broker.submit("Analyze revenue trends", agent_name="analyst")

    # Observation methods
    task = await broker.poll(task_id)         # Get current state
    task = await broker.wait(task_id)         # Block until terminal
    async for event in broker.stream(task_id): # Yield events as they arrive
        print(event.event_type, event.payload)

    await broker.cancel(task_id)              # Cancel a task
    await broker.cancel_all()                 # Cancel all non-terminal tasks

    # Callbacks
    await broker.notify(task_id, {TaskState.COMPLETED}, my_callback)
```

`register_agents(specs)` binds `AgentSpec` instances so the worker can resolve sub-agents by name. When `agent_name` is present in task metadata, the worker uses `OrchestratorAgent` with the registered spec. Otherwise it falls back to `get_agent()` with `system_prompt` and `config_name` from metadata.

### Worker

`Worker` executes tasks by running sub-agents. It transitions the task through `RUNNING` to `COMPLETED` or `FAILED`, emitting `STATE_CHANGE` events at each transition. During execution with an `AgentSpec`, it creates a node hook that emits `PROGRESS` events (tool calls) and `LOG` events (model reasoning) to the task's event stream.


## OrchestratorAgent

`OrchestratorAgent` composes all six capabilities into a single agent: direct tools, MCP servers, A2A clients, skills, sub-agents, and tasks. It takes an `AgentSpec` and wires everything up as an async context manager.

### AgentSpec

`AgentSpec` is the declarative specification for an orchestrator agent:

```python
from agentic_patterns.core.agents.orchestrator import AgentSpec

spec = AgentSpec(
    name="coordinator",
    description="Coordinates analysis tasks",
    system_prompt="You are an analysis coordinator.",
    tools=[my_tool],
    mcp_servers=[mcp_config],
    a2a_clients=[a2a_client],
    skills=[skill],
    sub_agents=[analyst_spec, researcher_spec],
)
```

Fields: `name` (required), `description`, `model` (defaults to config.yaml default), `system_prompt` or `system_prompt_path` (template with `{sub_agents_catalog}` and `{skills_catalog}` variables), `tools`, `mcp_servers` (list of `MCPClientConfig`), `a2a_clients` (list of `A2AClientExtended`), `skills` (list of `Skill`), `sub_agents` (list of `AgentSpec`).

### Loading from config.yaml

`AgentSpec.from_config()` resolves all components from configuration:

```python
spec = AgentSpec.from_config(
    "coordinator",
    model_name="azure_gpt4",
    system_prompt_path=Path("prompts/coordinator.md"),
    tool_names=["agentic_patterns.tools.file:get_all_tools"],
    mcp_server_names=["data_analysis", "sql"],
    a2a_client_names=["nl2sql"],
    skill_roots=[Path("skills/")],
    skill_names=["code-review"],  # None = load all discovered skills
)
```

If an `agents` section in `config.yaml` contains an entry matching the name, its values serve as defaults. Explicit parameters override YAML values.

### Running the orchestrator

```python
from agentic_patterns.core.agents.orchestrator import OrchestratorAgent

async with OrchestratorAgent(spec, verbose=True) as orchestrator:
    result = await orchestrator.run("Analyze Q4 revenue data")
    print(result.output)

    # Multi-turn: history accumulates across run() calls
    result = await orchestrator.run("Now compare with Q3")
```

On entry, `OrchestratorAgent` connects MCP servers, fetches A2A agent cards, discovers skills, creates the task broker (if sub-agents are present), builds the system prompt from templates and catalogs, and creates the underlying PydanticAI `Agent`.

### Auto-injected tools

When `sub_agents` are present in the spec, three tools are automatically added:

`delegate(agent_name, prompt)` -- submit a task to a sub-agent and block until it completes. Returns the result string or an error message. Propagates token usage to the coordinator.

`submit_task(agent_name, prompt)` -- submit a task for background execution. Returns immediately with the task ID.

`wait(timeout=120)` -- block until at least one background task finishes or the timeout fires. Returns status and results for all submitted tasks.

The coordinator decides which pattern to use based on its system prompt: `delegate` for synchronous delegation, `submit_task` + `wait` for parallel background work.

### Background task injection

Between `run()` calls, `OrchestratorAgent` checks for completed background tasks and prepends their results to the next prompt. This happens automatically -- the coordinator sees results from tasks it submitted earlier without explicitly polling.

### Node hooks

The `on_node` callback (or `verbose=True` for the built-in `_log_node` hook) observes the agent's execution graph. The hook receives each node as the agent processes it, enabling logging of model reasoning and tool calls.


## API Reference

### `agentic_patterns.core.agents.orchestrator`

| Name | Kind | Description |
|---|---|---|
| `AgentSpec` | Pydantic model | Declarative agent spec (name, model, prompt, tools, mcp, a2a, skills, sub_agents) |
| `AgentSpec.from_config(name, ...)` | Class method | Load and resolve all components from config.yaml |
| `OrchestratorAgent(spec, verbose, on_node)` | Class | Async context manager that composes and runs the agent |
| `OrchestratorAgent.run(prompt, ...)` | Method | Execute a turn, returns `AgentRunResult` |
| `OrchestratorAgent.runs` | Property | History of all (AgentRun, nodes) pairs |
| `OrchestratorAgent.system_prompt` | Property | Final composed system prompt |
| `NodeHook` | Type alias | `Callable[[Any], None]` for node observation |

### `agentic_patterns.core.skills`

| Name | Kind | Description |
|---|---|---|
| `SkillMetadata` | Pydantic model | Lightweight: name, description, path |
| `Skill` | Pydantic model | Full: name, description, path, frontmatter, body, script/reference/asset paths |
| `SkillRegistry` | Class | Discover (tier 1) and load (tier 2) skills |
| `SkillRegistry.discover(roots)` | Method | Scan directories, cache metadata, return `list[SkillMetadata]` |
| `SkillRegistry.get(name)` | Method | Load full `Skill` by name |
| `SkillRegistry.list_all()` | Method | Return cached metadata list |
| `list_available_skills(registry)` | Function | Compact catalog string for system prompts |
| `get_skill_instructions(registry, name)` | Function | Return SKILL.md body for activation |
| `get_all_tools(registry)` | Function | Return `[activate_skill]` tool list |
| `create_skill_sandbox_manager(registry)` | Function | SandboxManager with read-only skill mounts |
| `run_skill_script(manager, registry, ...)` | Function | Execute skill script in sandbox |

### `agentic_patterns.core.tasks`

| Name | Kind | Description |
|---|---|---|
| `TaskState` | Enum | PENDING, RUNNING, COMPLETED, FAILED, INPUT_REQUIRED, CANCELLED |
| `TERMINAL_STATES` | Set | {COMPLETED, FAILED, CANCELLED} |
| `EventType` | Enum | STATE_CHANGE, PROGRESS, LOG |
| `Task` | Pydantic model | Work unit: id, state, input, result, error, events, metadata |
| `TaskEvent` | Pydantic model | Event record: task_id, event_type, payload, timestamp |
| `TaskStore` | ABC | Persistence interface: create, get, update_state, list_by_state, next_pending, add_event |
| `TaskStoreMemory` | Class | In-memory implementation |
| `TaskStoreJson` | Class | JSON file-per-task implementation |
| `TaskBroker` | Class | Async context manager for task coordination and dispatch |
| `TaskBroker.submit(input, **metadata)` | Method | Create task, return task_id |
| `TaskBroker.poll(task_id)` | Method | Get current task state |
| `TaskBroker.wait(task_id)` | Method | Block until terminal state |
| `TaskBroker.stream(task_id)` | Method | Async iterator of TaskEvent |
| `TaskBroker.cancel(task_id)` | Method | Cancel a task |
| `TaskBroker.cancel_all()` | Method | Cancel all non-terminal tasks |
| `TaskBroker.notify(task_id, states, callback)` | Method | Register callback for state changes |
| `TaskBroker.register_agents(specs)` | Method | Bind AgentSpec dict for sub-agent resolution |
| `Worker` | Class | Executes tasks by running sub-agents |


## Examples

See the files in `agentic_patterns/examples/sub_agents/` and `agentic_patterns/examples/skills/`:

- `example_sub_agents_fixed.ipynb` -- fixed sub-agents with structured outputs and usage propagation
- `example_sub_agents_dynamic.ipynb` -- dynamic sub-agent creation at runtime
- `example_tasks.ipynb` -- task broker, background submission, streaming, cancellation
- `example_skills.ipynb` -- skill discovery, activation, progressive disclosure
