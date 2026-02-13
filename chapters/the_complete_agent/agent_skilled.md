## Agent V3: The Skilled

The Planner works well for tasks within its toolset, but what happens when the user asks it to review code for security issues? The agent has no security expertise in its prompt, so it improvises -- producing generic advice that misses real vulnerabilities. The Skilled agent solves this with progressive disclosure: specialized instructions loaded on demand rather than embedded upfront.

#### The Problem with Upfront Loading

One approach would be to paste every specialized instruction (code review, PDF processing, data formatting, etc.) into the system prompt. This fails for two reasons. First, a longer prompt means higher cost and slower responses on every turn, even when most instructions are irrelevant. Second, models perform worse when buried in irrelevant context -- the signal-to-noise ratio matters.

Progressive disclosure resolves this tension. At startup the agent receives only a catalog of skill names and one-line descriptions (cheap metadata). When the agent decides it needs a skill, it calls `activate_skill` to load the full instructions into its context. The system prompt stays lean until the agent actually needs a capability.

#### Skill Discovery

Skills live in directories under `data/skills/`. Each directory contains a `SKILL.md` file with YAML frontmatter (name, description) and a markdown body with full instructions. Optional subdirectories hold scripts, references, and assets.

The `OrchestratorAgent` scans these directories at startup, reading only the frontmatter. The result is a lightweight catalog injected into the system prompt via a shared template (`prompts/shared/skills.md`):

```
Available skills:
code-review: Review code for quality, bugs, and security issues.
pdf-processing: Extract text and tables from PDF files.
```

This is tier 1 of the disclosure hierarchy. The agent knows what skills exist but not how to use them.

#### Tool Composition

The Skilled agent uses `OrchestratorAgent` instead of the bare `get_agent()` / `run_agent()` pair from V1 and V2. The orchestrator handles skill discovery, prompt injection, and tool wiring automatically.

From this point on, agent definitions live in `config.yaml` rather than in Python code. Each entry declares a system prompt path, tool modules, and optional sub-agents or MCP servers:

```yaml
agents:
  skilled:
    system_prompt: the_complete_agent/agent_skilled.md
    tools:
      - agentic_patterns.tools.file:get_all_tools
      - agentic_patterns.tools.sandbox:get_all_tools
      - agentic_patterns.tools.todo:get_all_tools
```

The notebook loads this with a single call:

```python
spec = AgentSpec.from_config("skilled")
agent = OrchestratorAgent(spec, verbose=True)
```

`from_config()` resolves the prompt path relative to `PROMPTS_DIR`, imports each tool module, calls its `get_all_tools()`, and assembles the `AgentSpec`. The orchestrator then adds `activate_skill` behind the scenes. The agent code does not reference skills directly -- the prompt includes `{% include 'shared/skills.md' %}` and the orchestrator fills in the catalog and provides the tool.

#### Execution

The notebook demonstrates two turns. Turn 1 asks the agent to write a Python calculator script -- a normal coding task that requires no skills. The agent plans, writes, and executes as the Planner would.

Turn 2 asks: "review the script you just wrote for security issues." The agent sees `code-review` in its skill catalog, calls `activate_skill("code-review")`, and receives the full SKILL.md body -- a structured guide covering security vulnerabilities, error handling gaps, and output formatting. The agent then applies these instructions to the script from turn 1, producing a categorized review (CRITICAL, WARNING, INFO) instead of the generic advice a skill-less agent would give.

The `OrchestratorAgent` carries message history across turns automatically, so the agent remembers the script from turn 1 without the notebook managing any state.

#### Three Tiers of Disclosure

The skill system has three tiers. Tier 1 (always in prompt) is the name and description -- enough for the agent to decide whether a skill is relevant. Tier 2 (loaded via `activate_skill`) is the full SKILL.md body with instructions and examples. Tier 3 (optional) is scripts, references, and assets that live in subdirectories and can be executed in the sandbox or read by the agent when the skill instructions reference them.

Each tier is more expensive than the last, and each is loaded only when needed. This pattern recurs in many agent architectures: keep the common path cheap, pay for specialization only when the task demands it.

The full example is in `agentic_patterns/examples/the_complete_agent/example_agent_skilled.ipynb`.
