# Skills, Sub-Agents & Tasks

Sub-agents decompose work within a single process by giving each child its own context, prompt, and tools. Skills package reusable agent capabilities as discoverable artifacts with progressive disclosure. Tasks provide dependency-aware work tracking that agents use to coordinate multi-step work. These three patterns work together: `OrchestratorAgent` composes them declaratively via `AgentSpec`.

All infrastructure lives in `agentic_patterns.core.agents.orchestrator` (AgentSpec, OrchestratorAgent), `agentic_patterns.core.agents.agent_runner` (AgentRunner, AgentResult), `agentic_patterns.core.agents.agent_status` (AgentStatus), `agentic_patterns.core.skills` (registry, models, tools), and `agentic_patterns.core.tasks` (Task, TaskList, task tools).


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

`registry.get_all_tools(sandbox=...)` returns an `activate_skill` function for use as a PydanticAI tool:

```python
tools = registry.get_all_tools(sandbox=sandbox)
agent = get_agent(tools=tools, system_prompt=f"Available skills:\n{catalog}")
```

When called, `activate_skill(skill_name)` returns the full SKILL.md body. If the skill is not found, it returns an error message.

### Skill sandbox

`create_skill_sandbox_manager(registry)` creates a `SandboxManager` with read-only mounts for all discovered skill script directories. Use `run_skill_script_sandboxed()` to execute a skill's bundled scripts inside the container:

```python
from agentic_patterns.core.skills.tools import create_skill_sandbox_manager, run_skill_script_sandboxed

manager = create_skill_sandbox_manager(registry)
exit_code, output = run_skill_script_sandboxed(
    manager, registry, user_id, session_id,
    skill_name="code-review", script_name="analyze.py", args="main.py"
)
```


## Tasks

The task system provides dependency-aware work tracking. It has two distinct layers: **task management** (structured storage, status tracking, dependency enforcement via four tools) and **agent spawning** (launching agents to do work, getting results, stopping agents via three tools). See [docs/tasks.md](../tasks.md) for the full specification.

### State machine

```
pending  -->  in_progress  -->  completed
```

`TaskStatus` enum values: `PENDING`, `IN_PROGRESS`, `COMPLETED`, `DELETED`. A blocked task (one with non-empty `blockedBy` where at least one blocker is not completed) cannot transition to `in_progress`.

### Task model

```python
from agentic_patterns.core.tasks import Task, TaskStatus

task = Task(id="1", subject="Set up database", description="Configure connection pool")
# task.status: TaskStatus.PENDING
# task.active_form: None (present-continuous label for UI, e.g. "Setting up database")
# task.owner: None (agent name for filtering)
# task.blocks: [] (task IDs that cannot start until this completes)
# task.blocked_by: [] (task IDs that must complete before this can start)
# task.metadata: {} (arbitrary key/value data)
```

JSON serialization uses camelCase (`activeForm`, `blockedBy`) to match the specification. The `blocks` and `blockedBy` fields are kept in sync bidirectionally.

### TaskList

`TaskList` manages tasks persisted as individual JSON files in a directory. Each task is a separate `{id}.json` file.

```python
from pathlib import Path
from agentic_patterns.core.tasks import TaskList

task_list = TaskList(Path("data/workspaces/.tasks/my-list"))

task = await task_list.create("Build feature", "Implement the widget", active_form="Building feature")
task = await task_list.get("1")
all_tasks = await task_list.list_all()  # Returns summaries (no metadata)
task = await task_list.update("1", status=TaskStatus.IN_PROGRESS)
task = await task_list.update("2", add_blocked_by=["1"])  # Bidirectional sync
task = await task_list.update("1", metadata={"priority": None})  # Delete key
next_task = await task_list.next_available()  # First pending + unblocked, lowest ID
next_task = await task_list.next_available(owner="backend")  # Filter by owner
```

Dependencies are bidirectional: adding task 1 to task 3's `blockedBy` also adds task 3 to task 1's `blocks`. A blocked task raises `ValueError` if you try to set it to `in_progress`. `next_available()` returns the first task that is pending and unblocked (lowest ID first), optionally filtered by owner.

### Task tools

`get_task_tools(task_list)` returns four PydanticAI tool functions bound to a `TaskList`: `task_create`, `task_get`, `task_list_all`, `task_update`. These are thin wrappers that return formatted strings for agent consumption.

### AgentRunner

`AgentRunner` is the unified launcher for both local sub-agents and remote A2A agents. It replaces the old `SubAgentRunner` by handling both agent types through one interface.

```python
from agentic_patterns.core.agents.orchestrator import AgentRunner

# Local agents are AgentSpec instances; remote agents are (A2AClientExtended, card) tuples
runner = AgentRunner(
    local_agents={"analyst": analyst_spec, "writer": writer_spec},
    remote_agents={"researcher": (a2a_client, agent_card)},
)

result = await runner.launch("analyst", "Analyze Q4 data")  # Foreground
result = await runner.launch("researcher", "Find papers", run_in_background=True)  # Background
output = runner.get_output(result.agent_id)
runner.stop(result.agent_id)
await runner.cancel_all()
```

`AgentStatus` enum: `RUNNING`, `COMPLETED`, `FAILED`, `INPUT_REQUIRED`, `CANCELLED`, `TIMEOUT`.

For local agents, `AgentRunner` wraps `OrchestratorAgent(spec).run(prompt)` in an `asyncio.Task`. For remote agents, it calls `client.send_message_only(prompt)` and stores the remote task ID for later polling. The parent's `TaskList` is automatically shared with child agents via the `task_list` parameter on `OrchestratorAgent`.

`get_agent_runner_tools(runner)` returns three PydanticAI tools: `task_launch`, `task_output`, `task_stop`.


## OrchestratorAgent

`OrchestratorAgent` composes all capabilities into a single agent: direct tools, MCP servers, skills, and agents (local sub-agents and remote A2A agents via unified `AgentRunner`) with tasks (via `TaskList`). It takes an `AgentSpec` and wires everything up as an async context manager.

### AgentSpec

`AgentSpec` is the declarative specification for an orchestrator agent:

```python
from agentic_patterns.core.agents.orchestrator import AgentSpec  # or from ...agents import AgentSpec

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

Fields: `name` (required), `description`, `model` (defaults to config.yaml default), `system_prompt` or `system_prompt_path` (template with `{agents_catalog}` and `{skills_catalog}` variables), `tools`, `mcp_servers` (list of `MCPClientConfig`), `a2a_clients` (list of `A2AClientExtended`), `skills` (list of `Skill`), `sub_agents` (list of `AgentSpec`).

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
from agentic_patterns.core.agents.orchestrator import OrchestratorAgent  # or from ...agents import OrchestratorAgent

async with OrchestratorAgent(spec, verbose=True) as orchestrator:
    result = await orchestrator.run("Analyze Q4 revenue data")
    print(result.output)

    # Multi-turn: history accumulates across run() calls
    result = await orchestrator.run("Now compare with Q3")
```

On entry, `OrchestratorAgent` connects MCP servers, discovers skills, creates an `AgentRunner` (if sub-agents or A2A clients are present) that fetches A2A agent cards and builds a unified catalog, creates a shared `TaskList`, builds the system prompt from templates and catalogs, and creates the underlying PydanticAI `Agent`.

### Auto-injected tools

When `sub_agents` or `a2a_clients` are present in the spec, seven tools are automatically added:

**Task management tools** (from `get_task_tools`): `task_create`, `task_get`, `task_list_all`, `task_update` -- for creating, reading, listing, and updating tasks with dependency tracking.

**Agent spawning tools** (from `get_agent_runner_tools`): `task_launch` (launch a local or remote agent, foreground or background), `task_output` (retrieve results from a background agent), `task_stop` (cancel a running agent).

The agent decides how to use these tools based on its system prompt. Both local sub-agents and remote A2A agents are accessed through the same `task_launch` tool -- the `AgentRunner` routes to the correct backend based on the agent name.

### Background agent injection

Between `run()` calls, `OrchestratorAgent` checks for completed background agents (local via asyncio.Task, remote via one `get_task` call per pending agent) and prepends their results to the next prompt. This happens automatically -- the coordinator sees results from agents it launched earlier without explicitly polling.

### Shared TaskList

When `OrchestratorAgent` creates a child agent via `AgentRunner`, the parent's `TaskList` is passed to the child. This means all agents in the hierarchy share the same task state, enabling coordinated work tracking across delegation boundaries. A parent can also receive an external `TaskList` via the `task_list` constructor parameter.

### Node hooks

The `on_node` callback (or `verbose=True` for the built-in `_log_node` hook) observes the agent's execution graph. The hook receives each node as the agent processes it, enabling logging of model reasoning and tool calls.


## API Reference

### `agentic_patterns.core.agents.orchestrator`

| Name | Kind | Description |
|---|---|---|
| `AgentSpec` | Pydantic model | Declarative agent spec (name, model, prompt, tools, mcp, a2a, skills, sub_agents) |
| `AgentSpec.from_config(name, ...)` | Class method | Load and resolve all components from config.yaml |
| `OrchestratorAgent(spec, verbose, on_node, task_list)` | Class | Async context manager that composes and runs the agent |
| `OrchestratorAgent.run(prompt, ...)` | Method | Execute a turn, returns `AgentRunResult` |
| `OrchestratorAgent.runs` | Property | History of all (AgentRun, nodes) pairs |
| `OrchestratorAgent.system_prompt` | Property | Final composed system prompt |
| `OrchestratorAgent.agent_runner` | Property | The `AgentRunner` instance (or None) |
| `OrchestratorAgent.task_list` | Property | The `TaskList` instance (or None) |
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
| `SkillRegistry.get_all_tools(sandbox)` | Method | Return `[activate_skill]` tool list |
| `create_skill_sandbox_manager(registry)` | Function | SandboxManager with read-only skill mounts |
| `run_skill_script_sandboxed(manager, registry, ...)` | Function | Execute skill script in sandbox |

### `agentic_patterns.core.tasks`

| Name | Kind | Description |
|---|---|---|
| `TaskStatus` | Enum | PENDING, IN_PROGRESS, COMPLETED, DELETED |
| `Task` | Pydantic model | Work unit: id, subject, description, status, active_form, owner, blocks, blocked_by, metadata |
| `TaskList(base_dir)` | Class | File-backed task storage with dependency management |
| `TaskList.create(subject, description, ...)` | Method | Create task, assign next ID, return Task |
| `TaskList.get(task_id)` | Method | Read single task by ID |
| `TaskList.list_all()` | Method | List all tasks (summaries, no metadata) |
| `TaskList.update(task_id, ...)` | Method | Update task fields, handle bidirectional deps |
| `TaskList.next_available(owner=None)` | Method | First pending + unblocked task (lowest ID), optional owner filter |
| `get_task_tools(task_list)` | Function | Return four PydanticAI tool functions bound to a TaskList |

### `agentic_patterns.core.agents.agent_runner`

| Name | Kind | Description |
|---|---|---|
| `AgentStatus` | Enum | RUNNING, COMPLETED, FAILED, INPUT_REQUIRED, CANCELLED, TIMEOUT |
| `AgentResult` | Dataclass | Result holder: agent_id, agent_name, status, output, error, usage |
| `AgentRunner(local_agents, remote_agents)` | Class | Unified launcher for local and remote agents |
| `AgentRunner.launch(name, prompt, ...)` | Method | Launch agent (foreground or background) |
| `AgentRunner.get_output(agent_id)` | Method | Get result of a running/completed agent |
| `AgentRunner.stop(agent_id)` | Method | Cancel a running agent |
| `AgentRunner.cancel_all()` | Method | Cancel all running agents |
| `AgentRunner.catalog()` | Method | Return `{name: description}` for all agents |
| `AgentRunner.check_remote(agent_id)` | Method | Poll a remote agent once and update result |
| `get_agent_runner_tools(runner)` | Function | Return three PydanticAI tools: task_launch, task_output, task_stop |


## Examples

See the files in `agentic_patterns/examples/sub_agents/` and `agentic_patterns/examples/skills/`:

- `example_sub_agents_fixed.ipynb` -- fixed sub-agents with structured outputs and usage propagation
- `example_sub_agents_dynamic.ipynb` -- dynamic sub-agent creation at runtime
- `example_tasks.ipynb` -- task management, dependency tracking, agent coordination
- `example_skills.ipynb` -- skill discovery, activation, progressive disclosure
