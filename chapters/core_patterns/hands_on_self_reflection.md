## Hands-On: Self-Reflection Pattern

Self-reflection is a reasoning pattern where an agent explicitly examines and critiques its own output before revising it. This hands-on explores the self-reflection cycle using `example_self_reflection.ipynb`, demonstrating how agents can improve their solutions through iterative self-critique.

## The Three-Turn Reflection Cycle

A typical self-reflection pattern unfolds in three distinct turns:

**Turn 1: Generate** - The agent produces an initial solution to the task.

**Turn 2: Reflect** - The agent analyzes its own solution, identifying flaws, edge cases, or potential improvements.

**Turn 3: Revise** - The agent produces an improved solution based on its critique.

This cycle differs from simply reprompting the agent because the critique is grounded in the agent's own prior output and structured around explicit evaluation criteria.

## Example: Email Validation Function

The notebook demonstrates self-reflection using a code generation task: writing a Python function to validate email addresses.

### Turn 1: Initial Solution

```python
from agentic_patterns.core.agents import get_agent, run_agent
from agentic_patterns.core.agents.utils import nodes_to_message_history

agent = get_agent()

prompt_1 = """Write a Python function that validates email addresses.
The function should return True if the email is valid, False otherwise."""

agent_run_1, nodes_1 = await run_agent(agent, prompt_1)
print(agent_run_1.result.output)
```

The agent generates an initial implementation. This first attempt often works for common cases but may miss edge cases, security issues, or robustness concerns. A typical first solution might use simple string operations or basic regex patterns that handle obvious valid and invalid formats but lack sophistication.

### Turn 2: Self-Reflection

```python
message_history = nodes_to_message_history(nodes_1)

prompt_2 = """Review your solution and identify potential issues:
1. Are there any edge cases not handled?
2. Are there any security concerns?
3. Could the implementation be more robust?

List the specific problems you find."""

agent_run_2, nodes_2 = await run_agent(agent, prompt_2, message_history=message_history)
print(agent_run_2.result.output)
```

This prompt asks the agent to critique its own work using explicit evaluation criteria. The agent has access to its previous solution through message history, allowing it to analyze what it actually wrote rather than what it intended to write.

The agent might identify issues such as the regex pattern not handling valid international domain names, multiple consecutive dots in the local part not being properly rejected, the function not validating maximum length constraints per RFC 5321, special characters in quoted strings not being handled correctly, or the implementation being vulnerable to ReDoS attacks with certain malicious inputs.

This reflection step is where second-order reasoning occurs. The agent reasons not just about email validation, but about its own reasoning process and implementation choices.

### Turn 3: Revised Solution

```python
message_history = nodes_to_message_history(nodes_2)

prompt_3 = """Based on your critique, provide an improved version of the function that addresses the issues you identified."""

agent_run_3, nodes_3 = await run_agent(agent, prompt_3, message_history=message_history)
print(agent_run_3.result.output)
```

The agent now produces a revised implementation incorporating the improvements identified during reflection. The revised solution typically addresses the specific issues mentioned in the critique: stricter validation rules, edge case handling, security considerations, or adherence to relevant standards.

## Why Message History Matters

Each turn builds on the previous one through message history. Without this continuity, the pattern breaks down. Turn 2 needs the initial solution to critique it. Without message history, the agent wouldn't know what code to review. Turn 3 needs both the solution and the critique. The agent must understand what problems were identified to fix them.

The complete conversation structure looks like this:

```
Turn 1 - User: "Write a function..."
Turn 1 - Agent: [Initial solution]
Turn 2 - User: "Review your solution..."
Turn 2 - Agent: [Critique listing issues]
Turn 3 - User: "Provide an improved version..."
Turn 3 - Agent: [Revised solution]
```

## Comparison: With and Without Reflection

The notebook includes a comparison showing what happens when you ask directly for a robust solution without the reflection cycle:

```python
agent_no_reflection = get_agent()

prompt_direct = """Write a robust Python function that validates email addresses.
The function should return True if the email is valid, False otherwise."""

agent_run_direct, _ = await run_agent(agent_no_reflection, prompt_direct)
print(agent_run_direct.result.output)
```

Adding the word "robust" to the prompt tells the model to be more careful, but it doesn't provide the same structured reasoning process as explicit reflection. The direct approach may or may not produce a solution comparable to the reflected version, and it lacks the intermediate critique that makes the reasoning process transparent.

The reflection cycle offers several advantages over direct prompting. It provides transparency by making the critique explicit, showing why changes were made. It uses structured evaluation with explicit criteria rather than vague instructions like "be robust." The cycle can repeat multiple times if the first revision still has issues. The critique can be logged or analyzed to understand common failure modes.

## When Self-Reflection Helps

Self-reflection is particularly effective for tasks where correctness can be evaluated by examining the output: code generation to check for bugs, edge cases, security issues, or adherence to best practices; structured output to verify JSON schemas, API response formats, or configuration files; logical reasoning to identify gaps in argumentation or unsupported claims; and constraint satisfaction to ensure all requirements from a specification are met.

Self-reflection is less effective when evaluation requires external validation that the agent cannot perform, such as empirical testing against a test suite, user feedback on subjective preferences, or verification against external databases or APIs.

## Reflection Criteria

The quality of reflection depends heavily on the evaluation criteria provided. In our example, we asked three specific questions about edge cases, security concerns, and robustness.

Generic prompts like "Is this good?" or "Can you improve this?" produce weaker critiques. Specific criteria direct the agent's attention to particular dimensions of quality relevant to the task.

For different tasks, you would use different criteria. For a data analysis task, you might ask about statistical validity, assumptions, or visualization clarity. For a business document, you might ask about tone, completeness, or logical flow.

## Multiple Reflection Cycles

The pattern can extend beyond a single reflection cycle. If the revised solution still has issues, you can prompt another round of reflection:

```python
# After Turn 3, start another cycle
message_history = nodes_to_message_history(nodes_3)

prompt_4 = """Review your revised solution. Are there any remaining issues?"""
agent_run_4, nodes_4 = await run_agent(agent, prompt_4, message_history=message_history)

prompt_5 = """Address any remaining issues."""
agent_run_5, nodes_5 = await run_agent(agent, prompt_5, ...)
```

This creates a recursive refinement process that continues until the agent reports no significant issues or until you reach a stopping condition like maximum iterations or diminishing returns.

## Production Considerations

When implementing self-reflection in production systems, consider token cost since each reflection cycle sends the growing conversation history, increasing cost. Balance thoroughness against budget. Latency increases because multiple sequential API calls increase response time. Consider whether the quality improvement justifies the delay. Define stopping criteria for when to stop reflecting, such as maximum iterations, agent confidence indicators, or external validation passing. Invest effort in crafting good reflection prompts since the quality of the critique directly affects the quality of the revision. Remember that the agent may believe it has improved the solution when it hasn't, so external validation remains important.

## Key Differences from Other Patterns

Self-reflection differs from Chain-of-Thought in that CoT makes reasoning explicit but doesn't critique it, while self-reflection adds evaluation and revision. Compared to simple reprompting, asking "Can you do better?" without showing the agent its prior work lacks the grounding that makes reflection effective. Unlike Tree of Thought which explores multiple alternative paths forward, self-reflection improves a single path through iteration. External verification checks output against objective criteria or tests, while self-reflection is the agent checking itself.

These patterns can be combined. An agent might use CoT to generate a solution, self-reflection to refine it, and external verification to confirm correctness.

## Implementation Notes

The example uses the same patterns established in Chapter 1: message history through `nodes_to_message_history` to extract conversation state after each turn, sequential turns where each prompt builds on the previous response, and agent reuse where the same agent instance handles all turns for consistency.

This demonstrates that self-reflection is built from primitives you already know: multi-turn conversations with carefully crafted prompts that direct the agent's attention to evaluating its own output.

## Key Takeaways

Self-reflection is a three-turn pattern: generate, critique, revise. It requires message history to maintain continuity across turns. The quality of reflection depends on explicit evaluation criteria in the critique prompt. Self-reflection works best when the agent can evaluate its own output without external validation.

The pattern increases token cost and latency but can significantly improve output quality for tasks where structured self-evaluation is feasible. It makes reasoning transparent through the explicit critique and can be iterated multiple times for recursive refinement.

Self-reflection transforms a stateless model into an agent that appears to learn from its mistakes within a single session. This capability becomes even more powerful when combined with external feedback, persistent memory, or tool use, which we'll explore in later chapters.
