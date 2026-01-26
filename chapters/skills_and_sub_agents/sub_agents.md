## Sub-agents

A sub-agent is an autonomous agent instance with its own prompt, tools, and execution lifecycle, invoked by a parent agent to perform a well-scoped task. Conceptually, this mirrors function calls or microservices in classical software systems, but with a key difference: sub-agents reason, plan, and act using their own local context rather than sharing a single, ever-growing prompt.

In practice, a parent agent delegates responsibility to sub-agents for tasks such as research, planning, verification, or tool-heavy execution. Each sub-agent operates with a narrowly defined objective and returns a structured result to the parent, which remains responsible for orchestration and final decision-making. This separation allows agentic systems to scale in capability without collapsing under prompt complexity.

Frameworks such as PydanticAI support this pattern explicitly by allowing agents to call other agents as first-class components, passing structured inputs and receiving typed outputs. Similarly, Claude's sub-agent abstractions formalize the same idea: agents are composed, not monolithic.

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
