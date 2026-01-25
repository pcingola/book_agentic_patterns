# Sub-Agents

## Introduction

Sub-agents are a structural pattern for decomposing an agentic system into smaller, specialized agents that collaborate under a coordinating parent agent.

## Sub-agents

A sub-agent is an autonomous agent instance with its own prompt, tools, and execution lifecycle, invoked by a parent agent to perform a well-scoped task. Conceptually, this mirrors function calls or microservices in classical software systems, but with a key difference: sub-agents reason, plan, and act using their own local context rather than sharing a single, ever-growing prompt.

In practice, a parent agent delegates responsibility to sub-agents for tasks such as research, planning, verification, or tool-heavy execution. Each sub-agent operates with a narrowly defined objective and returns a structured result to the parent, which remains responsible for orchestration and final decision-making. This separation allows agentic systems to scale in capability without collapsing under prompt complexity.

Frameworks such as PydanticAI support this pattern explicitly by allowing agents to call other agents as first-class components, passing structured inputs and receiving typed outputs. Similarly, Claude’s sub-agent abstractions formalize the same idea: agents are composed, not monolithic.

A minimal example illustrates the shape of the interaction:

```python
# Parent agent delegates to a specialized sub-agent
result = research_agent.run(
    query="Summarize recent approaches to retrieval-augmented generation"
)

# Parent agent integrates the result into its own reasoning
analysis = f"Based on research findings: {result.summary}"
```

The important property is not the syntax, but the boundary: the sub-agent owns its internal reasoning and context, and only its output crosses back to the parent.

## Context engineering: why sub-agents help

Sub-agents are a powerful context-engineering tool. Large, monolithic prompts tend to accumulate instructions, examples, tool schemas, intermediate reasoning, and conversation history until the model’s effective context utilization degrades. Sub-agents mitigate this by enforcing context locality.

Each sub-agent receives only the information relevant to its task. Irrelevant instructions, historical turns, and tool definitions are excluded by construction. This leads to three practical benefits. First, token budgets are used more efficiently, since each agent operates near the minimum viable context. Second, reasoning quality improves, as the model is not distracted by unrelated constraints. Third, systems become easier to debug, because failures can be isolated to a specific sub-agent with a well-defined responsibility.

From a systems perspective, sub-agents act as an explicit form of context compression. Instead of summarizing or pruning text, the system restructures the problem so that less context is needed in the first place. This is often more robust than aggressive summarization, especially for tasks that require precise tool usage or domain-specific instructions.

## Relationship to A2A and AgentSkills

Sub-agents are a local composition mechanism; protocols and skill specifications generalize this idea across process and organizational boundaries.

The A2A Protocol defines how agents communicate over a network, including discovery, task lifecycles, and streaming results. A sub-agent call within a single process can be seen as the degenerate case of A2A: synchronous, trusted, and low-latency. Designing sub-agents with clear inputs and outputs makes it straightforward to later "lift" them into remote A2A agents without changing their conceptual contract.

AgentSkills provides a complementary abstraction by standardizing how agent capabilities are described, packaged, and reused. A sub-agent often implements a skill: a named capability with documented inputs, outputs, and behavioral guarantees. Conversely, a published skill can be instantiated as a sub-agent inside a larger system. This symmetry encourages modular design, where local sub-agents, reusable skills, and remote A2A agents all share the same conceptual interface.

Taken together, sub-agents, A2A, and AgentSkills form a continuum. Sub-agents optimize local composition and context management. Skills define reusable capability boundaries. A2A enables those boundaries to extend across machines, teams, or organizations.

## Hands-On

The following exercises demonstrate two approaches to sub-agent composition. The first uses pre-defined specialists with structured outputs, suitable for predictable workflows. The second creates sub-agents dynamically at runtime, trading control for flexibility.

[Hands-On: Fixed Sub-Agents](./hands_on_sub_agents_fixed.md)

[Hands-On: Dynamic Sub-Agents](./hands_on_sub_agents_dynamic.md)

## References

1. Anthropic. *Subagents*. Claude Platform Documentation, 2024. [https://platform.claude.com/docs/en/agent-sdk/subagents](https://platform.claude.com/docs/en/agent-sdk/subagents)
2. Anthropic. *Sub-agents*. Claude Code Documentation, 2024. [https://code.claude.com/docs/en/sub-agents](https://code.claude.com/docs/en/sub-agents)
3. PydanticAI Contributors. *Multi-agent applications*. Documentation, 2024. [https://ai.pydantic.dev/multi-agent-applications/](https://ai.pydantic.dev/multi-agent-applications/)
4. AgentSkills Working Group. *AgentSkills: reusable capabilities for agents*. Specification and documentation, 2024. [https://agentskills.io/home](https://agentskills.io/home)
5. A2A Protocol. *Agent-to-Agent Protocol*. Specification, 2024. [https://a2a-protocol.org/latest/](https://a2a-protocol.org/latest/)
