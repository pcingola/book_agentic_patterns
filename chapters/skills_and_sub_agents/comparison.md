## Comparison: Sub-agents, Skills, MCP, and A2A

Four patterns help manage complexity in agentic systems. Each solves a different problem; understanding when to use which prevents over-engineering and misapplication.

#### The four patterns at a glance

**Sub-agents** are agent instances created by a parent agent to handle scoped tasks. They exist within the same process, share the same runtime, and communicate through function calls. Use sub-agents when you need context isolation without network overhead.

**Skills** are packaged capability definitions stored as directories with a `SKILL.md` file. They standardize how capabilities are described, discovered, and activated. Use skills when you want reusable, shareable capability bundles that agents can load on demand.

**MCP (Model Context Protocol)** defines a client-server protocol where servers expose tools, resources, and prompts. MCP tools are discrete, schema'd operations like file reads, API calls, or database queries. Use MCP when you need to expose tools across processes, languages, or machines.

**A2A (Agent-to-Agent Protocol)** defines how agents communicate over a network, including discovery, task lifecycles, and streaming results. A2A agents are autonomous systems that reason, plan, and maintain state. Use A2A when you need stateful collaboration across organizational or trust boundaries.

#### Decision criteria

| Question | Pattern |
|----------|---------|
| Need context isolation within one process? | Sub-agents |
| Want reusable capability packages? | Skills |
| Need to expose tools to other processes? | MCP |
| Need collaboration with external agents? | A2A |

#### How they combine

These patterns are not mutually exclusive. A typical production system uses several together.

**Sub-agent activates a skill.** A coordinator delegates document analysis to a sub-agent. The sub-agent activates the `pdf-processing` skill to get instructions, then uses the skill's tools to extract text. The sub-agent provides context isolation; the skill provides packaged instructions.

**Skill uses MCP tools.** A skill's instructions tell the agent to use a database-query MCP tool. The skill defines the workflow ("query the cohort, compute metrics, generate chart"); the MCP tool handles the mechanical database access. The same MCP tool serves multiple skills.

**A2A wraps a sub-agent.** An organization exposes a research capability via A2A. Internally, the A2A server runs a sub-agent that handles the research task. External callers see an A2A interface; the implementation uses sub-agents for context management.

**Skill becomes an A2A agent.** A well-defined skill can be "lifted" into an A2A server. The skill's `SKILL.md` becomes the agent's internal playbook; A2A provides discovery, task lifecycle, and network transport. This is useful when a capability needs to cross organizational boundaries.

#### The continuum

These patterns form a continuum from local to remote:

```
Sub-agents (local, in-process)
    |
Skills (reusable boundaries, same runtime)
    |
MCP (tools across processes)
    |
A2A (agents across organizations)
```

Moving right adds network overhead, security considerations, and operational complexity. Moving left reduces flexibility and reusability. Choose the simplest pattern that meets your requirements.

#### Common mistakes

**Using A2A for local decomposition.** If your agents run in the same process and you control both, sub-agents are simpler. A2A adds protocol overhead you do not need.

**Using sub-agents instead of skills for reuse.** If you want to share a capability across projects or teams, package it as a skill. Sub-agents are runtime constructs; skills are portable artifacts.

**Embedding workflow logic in MCP tools.** MCP tools should be narrow operations. Put domain logic in skills that orchestrate the tools. This keeps tools reusable.

**Skipping skills for "simple" agents.** Even agents with few capabilities benefit from the progressive disclosure pattern. Skills are not just for large systems; they enforce good context hygiene from the start.
