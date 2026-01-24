## Hands-On: Zero-shot and Few-shot Prompting

This section demonstrates when few-shot prompting becomes necessary by comparing one task where zero-shot works and one where it fails.

## Example 1: Zero-shot Works Well

Sentiment analysis is a standard task well-represented in training data. The model already understands positive, negative, and neutral sentiments from its pre-training.

```python
system_prompt = """Analyze the sentiment of the given text.
Respond with only: 'positive', 'negative', or 'neutral'."""

agent = get_agent(system_prompt=system_prompt)
text = "This product exceeded my expectations. The quality is outstanding!"
agent_run, _ = await run_agent(agent, text)
print(agent_run.result.output)  # "positive"
```

This works because sentiment classification has clear, universal definitions. The model doesn't need examples to understand what makes text positive versus negative.

## Example 2: Few-shot Is Essential

Classifying GitHub issues as bugs versus feature requests has ambiguous boundaries. Consider this issue:

```
"The search doesn't support wildcards. I can't find files with partial names."
```

Is this a bug or a feature request? It depends on your definition. If wildcard search was promised but doesn't work, it's a bug. If it was never implemented, it's a feature request.

### Zero-shot Attempt

```python
system_prompt = """Classify GitHub issues as either 'bug' or 'feature_request'.
Respond with only the classification."""

agent = get_agent(system_prompt=system_prompt)
issue = "The search doesn't support wildcards. I can't find files with partial names."
agent_run, _ = await run_agent(agent, issue)
```

The model must guess your classification criteria. Different runs may produce inconsistent results for ambiguous cases.

### Few-shot Solution

Examples establish the boundary rule: broken functionality is a bug, missing functionality is a feature request.

```python
system_prompt = """Classify GitHub issues as either 'bug' or 'feature_request'.

Examples:

Issue: "The app crashes when I upload files larger than 10MB."
Classification: bug

Issue: "Add support for uploading files larger than 10MB."
Classification: feature_request

Issue: "The sort button doesn't work. Clicking it does nothing."
Classification: bug

Issue: "Add ability to sort by multiple columns simultaneously."
Classification: feature_request

Respond with only the classification.
"""

agent = get_agent(system_prompt=system_prompt)
agent_run, _ = await run_agent(agent, issue)
```

The examples clarify that "doesn't support" means missing functionality, making it a feature request. Without examples, this boundary remains ambiguous.

## Key Takeaways

Zero-shot prompting works for tasks with clear, universal definitions that are well-represented in training data.

Few-shot prompting is essential when task boundaries are ambiguous and require clarification. The examples encode implicit rules that are difficult to specify through instructions alone.

Use zero-shot when possible to minimize token usage. Move to few-shot when you encounter inconsistent results on edge cases or need to enforce specific classification criteria.
