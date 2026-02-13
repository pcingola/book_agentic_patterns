## Hands-On: Dynamic Sub-Agents

This hands-on explores `example_sub_agents_dynamic.ipynb`, which demonstrates sub-agents created at runtime. Instead of pre-defined specialists, the coordinator spawns sub-agents on demand by specifying their system prompt and task. This pattern maximizes flexibility: the coordinator decides what expertise it needs based on the problem at hand.

### The Generic Tool

The entire pattern rests on a single tool:

```python
async def run_sub_agent(ctx: RunContext[None], system_prompt: str, task: str) -> str:
    """Create and run a sub-agent with the given system prompt to perform the task."""
    sub_agent = get_agent(system_prompt=system_prompt)
    agent_run, _ = await run_agent(sub_agent, task)
    ctx.usage.incr(agent_run.result.usage())
    return agent_run.result.output
```

The tool takes two parameters: `system_prompt` defines the sub-agent's expertise, and `task` is the specific work to perform. The sub-agent is created, run, and discarded. No specialists are pre-defined.

### The Coordinator

The coordinator has only one tool but unlimited flexibility:

```python
coordinator = get_agent(
    tools=[run_sub_agent],
    system_prompt="""You are a problem-solving coordinator. For complex tasks, break
them down and delegate to specialized sub-agents using the run_sub_agent tool.

When using run_sub_agent:
- system_prompt: Define the sub-agent's expertise (e.g., "You are a financial analyst...")
- task: The specific question or task for that sub-agent

You can create any specialist you need. Synthesize their outputs into a final answer."""
)
```

When faced with a complex question, the coordinator reasons about what expertise would help, creates appropriate sub-agents, and synthesizes their outputs. The coordinator itself decides the decomposition strategy.

### Runtime Decisions

The example asks about investing in a coffee shop. The coordinator might decide to create:
- A financial analyst to evaluate ROI and payback period
- A risk analyst to assess market and operational risks
- A business strategist to consider competitive factors

These specialists are not pre-defined anywhere. The coordinator invents them based on what the problem requires. A different question would produce different specialists.

### Context Engineering

Dynamic sub-agents take context isolation further. Each sub-agent receives exactly two things: its system prompt (written by the coordinator for this specific task) and the task description. There is no accumulated context from previous sub-agents, no shared history, and no instructions for other specialists.

This means the coordinator must include all relevant information in the task description. If the financial analyst needs the revenue numbers, the coordinator must pass them explicitly. This constraint forces clean interfaces between the coordinator and its sub-agents.

### Tradeoffs

Dynamic sub-agents offer maximum flexibility but come with costs. Each sub-agent starts fresh with no pre-tuned prompt. The coordinator must write good system prompts on the fly, which depends on the coordinator's own capabilities. There is no opportunity to refine specialist prompts based on testing.

Fixed sub-agents allow you to craft and test each specialist's prompt carefully. Dynamic sub-agents trade that control for adaptability. The choice depends on whether your use case has predictable structure (favor fixed) or highly variable requirements (favor dynamic).

### Combining Approaches

In practice, you might combine both patterns. Pre-define specialists for common, well-understood tasks. Add a dynamic `run_sub_agent` tool for edge cases where no existing specialist fits. The coordinator can then use whichever approach suits the current request.
