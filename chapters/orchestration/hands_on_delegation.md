## Hands-On: Agent Delegation

Delegation is a pattern where one agent invokes another through a tool while retaining control of the overall task. Unlike workflows, where an external orchestrator sequences agent calls, delegation keeps decision-making inside the parent agent. The parent reasons about when to delegate, calls the specialist, and incorporates the result into its own response.

This hands-on explores delegation through `example_delegation.ipynb`. A research assistant delegates fact-checking to a specialist agent. The pattern demonstrates how to compose agents while maintaining clear control flow and unified resource tracking.

## Delegation vs. Direct Tool Calls

A regular tool is a function that performs some action: a calculation, an API call, or a database query. A delegation tool is a function that runs another agent. From the parent agent's perspective, both look the same: call a function, get a result. The difference is internal: delegation tools contain an entire reasoning process.

This distinction matters for system design. When you delegate to an agent, you're invoking something that can reason, adapt, and handle ambiguity. A fact-checker agent can evaluate nuanced claims that a simple lookup function cannot. But this power comes with cost: more tokens, more latency, and more complexity to debug.

The decision to delegate should be intentional. Use delegation when the subtask requires reasoning. Use regular tools when a deterministic function suffices.

## The Specialist Agent

The fact-checker is a focused agent with a single responsibility:

```python
class FactCheckResult(BaseModel):
    claim: str = Field(description="The claim that was checked")
    verdict: str = Field(description="accurate, inaccurate, or partially accurate")
    explanation: str = Field(description="Brief explanation of the verdict")

fact_checker = get_agent(
    output_type=FactCheckResult,
    system_prompt="""You are a fact-checker. Evaluate claims for accuracy.
Be precise and cite your reasoning. Focus only on verifiable facts."""
)
```

The structured output enforces a contract. The parent agent knows exactly what shape to expect: a verdict and an explanation. This predictability makes integration straightforward. The specialist's system prompt is narrow and focused, which tends to produce more reliable results than asking a general-purpose agent to fact-check as one of many responsibilities.

## The Delegation Tool

The tool wraps the specialist agent and exposes it to the parent:

```python
async def fact_check(ctx: RunContext[None], claim: str) -> str:
    """Verify a factual claim by delegating to a fact-checking specialist."""
    print(f"[Delegating to fact-checker] Claim: {claim}")

    agent_run, _ = await run_agent(
        fact_checker,
        f"Fact-check this claim: {claim}"
    )
    result = agent_run.result.output

    ctx.usage.incr(agent_run.result.usage())

    print(f"[Fact-checker result] {result.verdict}: {result.explanation}")
    return f"Verdict: {result.verdict}. {result.explanation}"
```

The function signature follows PydanticAI's tool convention. The `RunContext` parameter provides access to the parent agent's execution context, including usage tracking. The `claim` parameter is what the parent agent will provide when it calls the tool.

Inside the function, we run the specialist agent with `run_agent()`. This is a full agent execution: the specialist receives a prompt, reasons about it, and produces structured output. The result is then formatted as a string to return to the parent.

The line `ctx.usage.incr(agent_run.result.usage())` is critical for accounting. It takes the token usage from the delegated agent and adds it to the parent's usage counters. Without this, you would undercount total resource consumption.

## The Parent Agent

The research assistant receives the delegation tool like any other tool:

```python
research_agent = get_agent(
    tools=[fact_check],
    system_prompt="""You are a research assistant. Help users explore topics accurately.
When you make specific factual claims that could be verified, use the fact_check tool.
After fact-checking, incorporate the results into your response."""
)
```

The parent agent doesn't know that `fact_check` runs another agent internally. It sees a tool that takes a claim and returns a verification result. This encapsulation is intentional: the parent reasons about what to verify, not how verification works.

The system prompt guides when to delegate. In this case, the instruction is to verify "specific factual claims that could be verified." This gives the agent discretion. It might verify one claim but not another based on its assessment of which claims are verifiable and worth checking.

## Control Flow

When the research agent runs, the control flow looks like this:

1. Parent agent receives the user's question
2. Parent agent reasons and generates a response, deciding to verify certain claims
3. Parent agent calls `fact_check("the speed of light is 299,792,458 m/s")`
4. The tool runs the specialist agent
5. Specialist agent reasons about the claim and produces a verdict
6. Tool returns the formatted result to the parent
7. Parent agent incorporates the result and continues its response
8. Parent agent may call `fact_check` again for other claims
9. Parent agent produces final output

Control always returns to the parent after each delegation. The parent decides what to do with the result. This is different from a hand-off, where one agent would pass responsibility to another and exit.

## Unified Usage Tracking

After running the research agent, you can inspect total token usage:

```python
usage = agent_run.result.usage()
print(f"Total tokens (including delegated calls): {usage.total_tokens}")
```

Because the delegation tool called `ctx.usage.incr()`, this total includes tokens from both the parent and all delegated agents. This unified accounting is essential for cost management and quota enforcement. If you have multiple levels of delegation (agent A delegates to B, which delegates to C), each level should propagate usage upward.

## When to Use Delegation

Delegation is appropriate when:

- The subtask requires reasoning that a simple function cannot provide
- You want the parent agent to retain control over the overall task
- The specialist has a focused responsibility that benefits from a tailored prompt
- You need to compose capabilities while maintaining a single conversation flow

Delegation is less appropriate when:

- The subtask is deterministic and doesn't need reasoning
- You want true autonomy where agents hand off responsibility
- The workflow is better expressed as explicit stages controlled externally

## Key Takeaways

Delegation wraps an agent in a tool, letting a parent agent invoke it while maintaining control. The parent decides when to delegate based on its own reasoning.

The delegation tool is a regular function that internally runs another agent. The parent doesn't need to know this; it just calls a tool and gets a result.

Usage tracking requires explicit propagation. Call `ctx.usage.incr()` in the delegation tool to include the specialist's token consumption in the parent's totals.

Specialists benefit from focused prompts and structured outputs. Narrow responsibilities tend to produce more reliable results than asking a general agent to handle everything.

Control always returns to the parent after delegation. This distinguishes delegation from hand-offs, where responsibility would transfer permanently.
