## Hands-On: Agent Delegation

Delegation is a control flow pattern where one agent invokes another through a tool while retaining control of the overall task. Unlike workflows, where an external orchestrator sequences agent calls, delegation keeps decision-making inside the parent agent. The parent reasons about when to delegate, calls the specialist, and incorporates the result into its own response.

This hands-on explores delegation through `example_delegation.ipynb`. A research assistant delegates fact-checking to a specialist agent.

## Delegation as Control Flow

The key distinction is control flow. In delegation, the parent agent:

1. Receives the user's request
2. Reasons about what work to delegate
3. Calls delegation tools (which run sub-agents internally)
4. Receives results and continues reasoning
5. May delegate again or produce final output

Control always returns to the parent after each delegation. This is different from a hand-off, where one agent would pass responsibility to another and exit.

## The Delegation Tool Pattern

A delegation tool wraps a sub-agent and exposes it to the parent:

```python
async def fact_check(ctx: RunContext[None], claim: str) -> str:
    """Verify a factual claim by delegating to a fact-checking specialist."""
    agent_run, _ = await run_agent(
        fact_checker,
        f"Fact-check this claim: {claim}"
    )
    result = agent_run.result.output
    ctx.usage.incr(agent_run.result.usage())
    return f"Verdict: {result.verdict}. {result.explanation}"
```

The `ctx.usage.incr()` call propagates token usage from the sub-agent to the parent's totals. Without this, you would undercount total resource consumption.

## When to Use Delegation

Delegation is appropriate when the subtask requires reasoning that a simple function cannot provide, when you want the parent agent to retain control over the overall task, and when the specialist has a focused responsibility that benefits from a tailored prompt.

Delegation is less appropriate when the subtask is deterministic and doesn't need reasoning, when you want true autonomy where agents hand off responsibility, or when the workflow is better expressed as explicit stages controlled externally.

## Relationship to Sub-Agents

Delegation is how sub-agents are invoked from a control flow perspective. For detailed coverage of sub-agent patterns, including fixed specialists with structured outputs and dynamic sub-agent creation at runtime, see the [Sub-Agents chapter](../sub_agents/chapter.md).
