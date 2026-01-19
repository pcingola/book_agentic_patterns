# Hands-On: Chain-of-Thought Reasoning

Chain-of-Thought prompting improves model accuracy on reasoning tasks by instructing the model to show its work. Instead of jumping directly to an answer, the model generates intermediate steps that decompose the problem, apply logic, and arrive at a conclusion through explicit reasoning.

This hands-on explores Chain-of-Thought using `example_chain_of_thought.ipynb`, demonstrating how explicit reasoning improves both accuracy and transparency.

## The Problem: Opaque Reasoning

Language models can solve many tasks by pattern matching against their training data. However, tasks requiring multi-step reasoning often fail when the model tries to compress all reasoning into a single prediction. Consider this word problem:

```
A bakery produces 240 cupcakes per day. They sell cupcakes in boxes of 6.
If each box costs $12 and they sell all cupcakes, how much revenue do they generate per day?
```

This requires three steps: divide 240 by 6 to get the number of boxes, multiply by $12 to get revenue, verify the logic. If the model attempts to jump directly to the answer, it may skip a step or miscalculate.

## The Solution: Explicit Reasoning

Chain-of-Thought prompting instructs the model to generate intermediate reasoning steps before producing the final answer. This externalizes the reasoning process, making it visible and debuggable.

```python
system_prompt = """Solve the problem step by step. Show your reasoning for each step before providing the final answer.

Format:
Step 1: [description]
Step 2: [description]
...
Final Answer: [answer]"""
```

By requiring explicit steps, we force the model to allocate generation capacity to reasoning rather than compressing everything into an opaque prediction.

## Example 1: Direct Answer vs Chain-of-Thought

Let's examine the difference between direct answering and Chain-of-Thought.

### Direct Answer

```python
from agentic_patterns.core.agents import get_agent, run_agent

system_prompt = """Answer the question directly. Provide only the final answer."""

agent_direct = get_agent(system_prompt=system_prompt)

problem = """A bakery produces 240 cupcakes per day. They sell cupcakes in boxes of 6.
If each box costs $12 and they sell all cupcakes, how much revenue do they generate per day?"""

agent_run, _ = await run_agent(agent_direct, problem)

print(agent_run.result.output)
# Output might be: "$480" (correct by luck, or incorrect due to calculation error)
```

The model produces an answer, but we cannot see how it arrived at that answer. If the answer is wrong, we cannot identify where the reasoning failed. Even if correct, we don't know if the model truly understood the problem or got lucky.

### Chain-of-Thought Answer

```python
system_prompt = """Solve the problem step by step. Show your reasoning for each step before providing the final answer.

Format:
Step 1: [description]
Step 2: [description]
...
Final Answer: [answer]"""

agent_cot = get_agent(system_prompt=system_prompt)

agent_run, _ = await run_agent(agent_cot, problem)

print(agent_run.result.output)
# Output:
# Step 1: Calculate the number of boxes. 240 cupcakes ÷ 6 cupcakes per box = 40 boxes
# Step 2: Calculate revenue. 40 boxes × $12 per box = $480
# Final Answer: $480
```

Now we can see the reasoning. The model explicitly calculated the number of boxes before calculating revenue. If the answer were wrong, we could identify which step failed. This transparency is valuable for debugging and verification.

## Example 2: Zero-Shot Chain-of-Thought

The simplest form of Chain-of-Thought is "zero-shot CoT," introduced by Kojima et al. in 2022. You don't need to specify a format or provide examples. Just add the phrase "Think step by step" to your prompt:

```python
system_prompt = """Answer the question. Think step by step."""

agent_zero_cot = get_agent(system_prompt=system_prompt)

agent_run, _ = await run_agent(agent_zero_cot, problem)

print(agent_run.result.output)
```

This remarkably simple technique often produces comparable results to structured CoT prompting. The phrase "Think step by step" (or variations like "Let's solve this step by step") triggers the model to generate intermediate reasoning without requiring explicit format instructions.

Zero-shot CoT works because large language models have been trained on vast amounts of text containing step-by-step explanations. The phrase "Think step by step" activates this pattern in the model's learned representations, causing it to generate similar step-by-step structures.

## Example 3: Logical Reasoning

Chain-of-Thought is not limited to arithmetic. It improves performance on any task requiring sequential reasoning or constraint satisfaction. Consider this logic puzzle:

```python
system_prompt = """Solve the problem step by step. Show your reasoning clearly."""

agent = get_agent(system_prompt=system_prompt)

problem = """Three friends (Alice, Bob, Carol) are sitting in a row at a movie theater.
- Alice is not sitting at either end.
- Bob is sitting to the left of Carol.
What is the seating order from left to right?"""

agent_run, _ = await run_agent(agent, problem)

print(agent_run.result.output)
# Output:
# Step 1: Alice is not at either end, so Alice must be in the middle.
# Step 2: Bob is to the left of Carol.
# Step 3: Since Alice is in the middle, Bob and Carol occupy the ends.
# Step 4: Bob is to the left of Carol, so Bob is on the left end.
# Final Answer: Bob, Alice, Carol
```

The model tracks constraints across multiple steps. Without CoT, it might violate a constraint or produce an inconsistent answer. With CoT, each constraint is explicitly checked, reducing errors.

## When Chain-of-Thought Helps

Chain-of-Thought is most valuable for tasks that involve:

**Multi-step arithmetic or algebra**: Calculations requiring intermediate results before reaching the final answer.

**Logical deduction**: Problems with multiple constraints that must be satisfied simultaneously.

**Planning and decomposition**: Breaking down a complex goal into a sequence of actions.

**Commonsense reasoning**: Drawing inferences that require background knowledge or multiple logical steps.

**Symbolic manipulation**: Transforming expressions according to rules (e.g., simplifying equations, parsing structured data).

Chain-of-Thought is less valuable for tasks where the model can pattern-match directly, such as sentiment analysis, simple classification, or retrieval-based question answering. If the task doesn't require reasoning, adding CoT just increases token usage without improving accuracy.

## Trade-offs and Limitations

Chain-of-Thought is not a silver bullet. It introduces several trade-offs:

**Increased token usage**: Generating reasoning steps consumes more tokens than direct answers. This increases cost and latency.

**Reasoning may contain errors**: The model can produce plausible-sounding reasoning that is logically incorrect. The final answer may be right despite wrong reasoning, or wrong despite correct reasoning.

**Not a guarantee of correctness**: CoT increases the probability of correct answers, but does not guarantee them. For high-stakes applications, consider verifying the reasoning or using additional validation techniques.

**Format compliance**: The model may not always follow the requested format perfectly. Be prepared to parse free-form reasoning even when you request structured steps.

Despite these limitations, Chain-of-Thought remains one of the most effective techniques for improving reasoning in large language models. It serves as a foundation for more advanced patterns like self-reflection, tree-of-thought, and verification, which build on explicit reasoning to further improve accuracy and reliability.

## Implementation Patterns

When implementing Chain-of-Thought in production systems, consider these patterns:

**Use system prompts**: Put CoT instructions in the system prompt so they persist across multiple turns without repeating them in every user message.

```python
system_prompt = "Solve problems step by step. Show your reasoning."
agent = get_agent(system_prompt=system_prompt)
```

**Choose format granularity**: Decide whether to specify an exact format ("Step 1:", "Step 2:") or use free-form reasoning ("Think step by step"). Structured formats are easier to parse but may constrain the model. Free-form prompts are more flexible but harder to parse.

**Verify reasoning programmatically**: For tasks with verifiable steps (like arithmetic), extract and check intermediate results programmatically. If the calculation in "Step 1" is wrong, flag it before accepting the final answer.

**Combine with other patterns**: Chain-of-Thought works well with self-reflection (critique your own reasoning), few-shot learning (show examples of good reasoning), and verification (check your answer).

**Monitor token usage**: Track how much additional cost CoT introduces. For some applications, the improved accuracy justifies the cost. For others, you may need to tune the level of reasoning detail.

## How It Connects to Other Patterns

Chain-of-Thought is a foundational pattern that enables more sophisticated techniques:

**Self-reflection**: After generating reasoning, ask the model to critique it. Did I make any logical errors? Are there alternative interpretations?

**Tree-of-Thought**: Instead of a single reasoning chain, explore multiple reasoning paths and select the best one.

**Verification**: Use a separate agent to verify each reasoning step, catching errors before they propagate.

**ReAct**: Interleave reasoning with actions. Think about what to do, execute an action, observe the result, then reason about the next step.

All of these patterns depend on explicit reasoning. Chain-of-Thought provides the substrate that makes advanced agentic patterns possible.

## Key Takeaways

Chain-of-Thought improves reasoning by externalizing intermediate steps. Instead of opaque predictions, the model generates transparent reasoning traces that can be inspected, debugged, and verified.

The simplest implementation is zero-shot CoT: just add "Think step by step" to your prompt. For more control, specify a structured format or provide few-shot examples of step-by-step reasoning.

Chain-of-Thought is most valuable for multi-step reasoning tasks: arithmetic, logic, planning, and constraint satisfaction. It is less valuable for tasks that can be solved by pattern matching alone.

CoT increases token usage and latency but improves accuracy and transparency. The trade-off is worthwhile for tasks where reasoning quality matters more than speed or cost.

Chain-of-Thought serves as a foundational pattern for more advanced agentic techniques. By making reasoning explicit, it enables self-reflection, verification, and structured exploration of reasoning paths.
