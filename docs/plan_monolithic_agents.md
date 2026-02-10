# Plan: Monolithic Section (Agents V3-V5)

The previous section ended with Agent V2 (The Planner): 16 tools (file + sandbox + todo). The Planner text explicitly says "This is also the limit of what a monolithic agent can do well" and promises the next sections will address this. We now build three more agents, each adding a capability layer while remaining monolithic (single `Agent`, no MCP, no A2A, runnable from a notebook).

## Agent V3: The Skilled

**What it adds:** Progressive disclosure via skills. Instead of loading all specialized instructions into the system prompt upfront, the agent discovers skills at startup (metadata only -- name + description) and activates them on demand (loading full SKILL.md body). This keeps the system prompt lean until the agent actually needs a capability.

**Tools:** Planner's 16 + `activate_skill` = 17 tools. The skill catalog (one-liner per skill) is injected into the system prompt. When the agent calls `activate_skill("code-review")`, it receives the full instructions as the tool return value, which then enters its context.

**Key concept:** Progressive disclosure solves the tension between capability breadth and prompt bloat. Metadata is cheap (always in prompt). Full instructions are expensive (loaded on demand).

**Files to create:**
- `prompts/the_complete_agent/agent_skilled.md` -- extends planner prompt with skills section
- `agentic_patterns/examples/the_complete_agent/example_agent_skilled.ipynb` -- notebook demo
- Reuse existing demo skills from `agentic_patterns/examples/skills/skills-demo/` (code-review, pdf-processing)

**Implementation:** The `activate_skill` tool is defined inline in the notebook as a closure over the `SkillRegistry` (same pattern as `examples/skills/example_skills.ipynb`). No new library code needed.

## Agent V4: The Coordinator

**What it adds:** Sub-agent delegation. Instead of giving the agent 40+ specialized tools (data analysis operations, SQL tools, etc.), it gets delegation tools: `ask_data_analyst(prompt)` and `ask_sql_analyst(prompt)`. Each delegation tool creates a specialist sub-agent internally, runs it with the prompt, propagates usage, and returns the result string. The coordinator agent decides *who* to delegate to; the sub-agent decides *how* to accomplish it.

**Tools:** Skilled's 17 + `ask_data_analyst` + `ask_sql_analyst` + `convert_document` = 20 tools. Format conversion is added as a direct tool (it's just one tool, not worth a sub-agent).

**Key concept:** Delegation as the solution to tool explosion. Each sub-agent has its own context window, its own system prompt with domain-specific instructions, and its own tool set. The coordinator stays focused on routing and synthesis.

**Files to create:**
- `prompts/the_complete_agent/agent_coordinator.md` -- extends skilled prompt with delegation section
- `agentic_patterns/examples/the_complete_agent/example_agent_coordinator.ipynb` -- notebook demo

**Implementation:** Delegation tools follow the exact pattern from `agents/coordinator.py`: async function taking `RunContext` + `prompt`, creating sub-agent, running it, propagating `ctx.usage.incr()`. Reuse `agents/data_analysis.py` and `agents/sql.py` directly.

## Agent V5: The Full Agent (with Tasks)

**What it adds:** The async task system (`core/tasks/`) for background execution. The agent can submit long-running work to the `TaskBroker`, check status, and wait for completion. This is useful when delegations may take significant time -- instead of blocking the conversation, the agent submits a task and can do other work while waiting.

**Tools:** Coordinator's 20 + `submit_task` + `check_task` + `wait_for_task` = 23 tools.

**Key concept:** Async task submission decouples the agent's conversation loop from long-running work. This is the bridge to the distributed version later -- in the infrastructure section, the TaskBroker becomes a real server, but the agent's interface (submit/check/wait) stays the same.

**Files to create:**
- `prompts/the_complete_agent/agent_full.md` -- extends coordinator prompt with tasks section
- `agentic_patterns/examples/the_complete_agent/example_agent_full.ipynb` -- notebook demo

**Implementation:** Task tools wrap the `TaskBroker` API as agent-callable functions. The broker and dispatch loop run in the notebook's event loop.

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
