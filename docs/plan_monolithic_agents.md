# Plan: Monolithic Section (Agents V3-V5)

The previous section ended with Agent V2 (The Planner): 16 tools (file + sandbox + todo). The Planner text explicitly says "This is also the limit of what a monolithic agent can do well" and promises the next sections will address this. We now build three more agents, each adding a capability layer while remaining monolithic (single `OrchestratorAgent`, no MCP, no A2A, runnable from a notebook).

All three agents use `OrchestratorAgent` from `core/agents/orchestrator.py`. V1 and V2 used bare `get_agent()` + `run_agent()` because they had no skills, sub-agents, or tasks. Starting with V3 the agents need composition (skills injected into prompts, delegation tools, task tools), which is exactly what `OrchestratorAgent` provides. The notebooks use `OrchestratorAgent.run()` for each turn, passing `message_history` for multi-turn conversations.

Skills are loaded from `SKILLS_DIR` (configured in `core/config/config.py`, defaults to `data/skills/`). The demo skills (code-review, pdf-processing) live there.

## Library changes

**`core/skills/tools.py`**: Add `get_all_tools(registry)` returning `[activate_skill]`. The `activate_skill` tool is a closure over the registry that calls `get_skill_instructions()` and prints `[SKILL ACTIVATED: name]`. This eliminates the boilerplate that was previously copy-pasted into every notebook.

**`core/config/config.py`**: Add `SKILLS_DIR` (defaults to `DATA_DIR / "skills"`).

**`OrchestratorAgent`**: When skills are present, auto-add skill tools (from `core/skills/tools.get_all_tools()`) to the agent's tool list in `__aenter__`. The orchestrator already injects the skill catalog into the system prompt; now it also provides the activation tool.

## Agent V3: The Skilled

**What it adds:** Progressive disclosure via skills. Instead of loading all specialized instructions into the system prompt upfront, the agent discovers skills at startup (metadata only -- name + description) and activates them on demand (loading full SKILL.md body). This keeps the system prompt lean until the agent actually needs a capability.

**Tools:** Planner's 16 + `activate_skill` = 17 tools. The skill catalog (one-liner per skill) is injected into the system prompt by `OrchestratorAgent`. When the agent calls `activate_skill("code-review")`, it receives the full instructions as the tool return value, which then enters its context.

**Key concept:** Progressive disclosure solves the tension between capability breadth and prompt bloat. Metadata is cheap (always in prompt). Full instructions are expensive (loaded on demand).

**Files to create:**
- `prompts/the_complete_agent/agent_skilled.md` -- extends planner prompt with skills section
- `agentic_patterns/examples/the_complete_agent/example_agent_skilled.ipynb` -- notebook demo

**Implementation:** The notebook creates an `OrchestratorAgent` via `AgentSpec` with `skill_roots=[SKILLS_DIR]`. The orchestrator discovers skills, injects the catalog, and adds `activate_skill` automatically. The demo is a multi-turn conversation: turn 1 writes a script, turn 2 asks for a security review (the agent should activate the code-review skill on its own).

## Agent V4: The Coordinator

**What it adds:** Sub-agent delegation. Instead of giving the agent 40+ specialized tools (data analysis operations, SQL tools, etc.), it gets delegation tools: `ask_data_analyst(prompt)` and `ask_sql_analyst(prompt)`. Each delegation tool creates a specialist sub-agent internally, runs it with the prompt, propagates usage, and returns the result string. The coordinator agent decides *who* to delegate to; the sub-agent decides *how* to accomplish it.

**Tools:** Skilled's 17 + `ask_data_analyst` + `ask_sql_analyst` + `convert_document` = 20 tools. Format conversion is added as a direct tool (it's just one tool, not worth a sub-agent).

**Key concept:** Delegation as the solution to tool explosion. Each sub-agent has its own context window, its own system prompt with domain-specific instructions, and its own tool set. The coordinator stays focused on routing and synthesis.

**Files to create:**
- `prompts/the_complete_agent/agent_coordinator.md` -- extends skilled prompt with delegation section
- `agentic_patterns/examples/the_complete_agent/example_agent_coordinator.ipynb` -- notebook demo

**Implementation:** Delegation tools follow the exact pattern from `agents/coordinator.py`: async function taking `RunContext` + `prompt`, creating sub-agent, running it, propagating `ctx.usage.incr()`. Reuse `agents/data_analysis.py` and `agents/sql.py` directly. These tools are passed via `AgentSpec.tools`.

## Agent V5: The Full Agent (with Tasks)

**What it adds:** The async task system (`core/tasks/`) for background execution. The agent can submit long-running work to the `TaskBroker`, check status, and wait for completion. This is useful when delegations may take significant time -- instead of blocking the conversation, the agent submits a task and can do other work while waiting.

**Tools:** Coordinator's 20 + `submit_task` + `check_task` + `wait_for_task` = 23 tools.

**Key concept:** Async task submission decouples the agent's conversation loop from long-running work. This is the bridge to the distributed version later -- in the infrastructure section, the TaskBroker becomes a real server, but the agent's interface (submit/check/wait) stays the same.

**Files to create:**
- `prompts/the_complete_agent/agent_full.md` -- extends coordinator prompt with tasks section
- `agentic_patterns/examples/the_complete_agent/example_agent_full.ipynb` -- notebook demo

**Implementation:** Task tools wrap the `TaskBroker` API as agent-callable functions. The broker and dispatch loop run in the notebook's event loop. Task tools are passed via `AgentSpec.tools`.

## Chapter text

After all notebooks are working, write:
- `chapters/the_complete_agent/agent_skilled.md`
- `chapters/the_complete_agent/agent_coordinator.md`
- `chapters/the_complete_agent/agent_full.md`

Update `chapters/the_complete_agent/chapter.md` to add the three new links.

## Summary of progression

| Agent | Tools | Key Addition |
|-------|-------|-------------|
| V1: Coder | 10 | file + sandbox |
| V2: Planner | 16 | + todo (planning) |
| V3: Skilled | 17 | + skills (progressive disclosure) |
| V4: Coordinator | 20 | + sub-agents + format conversion |
| V5: Full Agent | 23 | + async tasks |
