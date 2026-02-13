## Hands-On: Fixed Sub-Agents

This hands-on explores `example_sub_agents_fixed.ipynb`, which demonstrates sub-agents as pre-defined specialists. A coordinator agent delegates to three specialized sub-agents, each with its own focused context and structured output. The pattern shows how decomposition improves both code organization and context efficiency.

### The Setup

The example analyzes a quarterly business report. Instead of a single monolithic agent handling everything, the work is split across specialists: a summarizer, a key points extractor, and a sentiment analyzer. Each sub-agent has a narrow responsibility and returns structured output.

```python
class Summary(BaseModel):
    summary: str = Field(description="2-3 sentence summary of the document")

summarizer = get_agent(
    output_type=Summary,
    system_prompt="""You are a summarization specialist. Produce concise, accurate
summaries that capture the essential information. Be factual and objective."""
)
```

The structured output enforces a contract between the sub-agent and the coordinator. The coordinator knows exactly what shape to expect, making integration predictable.

### Context Isolation

Each sub-agent receives only what it needs. When the summarizer runs, it sees:
- Its own system prompt (summarization instructions)
- The document to summarize

It does not see the key points extractor's instructions, the sentiment analyzer's output format, or the coordinator's orchestration logic. This isolation has practical benefits: the sub-agent's context is minimal, focused, and free of irrelevant instructions that could confuse the model.

### Delegation Tools

The delegation tools wrap sub-agents and expose them to the coordinator:

```python
async def get_summary(ctx: RunContext[None], document: str) -> str:
    """Delegate to summarizer sub-agent."""
    agent_run, _ = await run_agent(summarizer, f"Summarize this document:\n\n{document}")
    result = agent_run.result.output
    ctx.usage.incr(agent_run.result.usage())
    return result.summary
```

The tool takes the document as input, runs the sub-agent, extracts the structured result, and returns it as a string. The `ctx.usage.incr()` call propagates token usage from the sub-agent to the coordinator's totals.

### The Coordinator

The coordinator has access to all three delegation tools:

```python
coordinator = get_agent(
    tools=[get_summary, get_key_points, get_sentiment],
    system_prompt="""You are a document analysis coordinator. When asked to analyze
a document, use your tools to gather insights from specialists, then synthesize
the results into a coherent analysis report. Always use all three tools to provide
a comprehensive analysis."""
)
```

The coordinator's job is orchestration and synthesis. It calls each specialist, receives their outputs, and combines them into a final report. The actual analysis work happens in the sub-agents.

### When to Use Fixed Sub-Agents

Fixed sub-agents work well when you know in advance what specialists you need. Document analysis, content pipelines, and structured workflows often fit this pattern. The specialists are defined once and reused across many requests.

The tradeoff is flexibility. If a new type of analysis is needed, you must define a new sub-agent and add a new tool. The next hands-on shows how dynamic sub-agents address this limitation.
