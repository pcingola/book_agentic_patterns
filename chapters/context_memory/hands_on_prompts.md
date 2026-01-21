# Hands-On: Prompts

The effective context an LLM sees is the concatenation of multiple layers: system prompts, developer instructions, and user prompts. Each layer serves a different purpose and has different persistence behavior. This hands-on explores these prompt layers using `example_prompts.ipynb`.

## The Prompt Layers

When you send a request to an LLM through an agent framework, the model receives a combined context built from several sources. Understanding these layers helps you design agents with predictable, controllable behavior.

**System prompts** establish the agent's identity, invariant rules, and global policies. They define "who the agent is" and constraints that should apply regardless of the specific task. System prompts are typically preserved as part of the message history when continuing a conversation.

**Instructions** (sometimes called developer instructions) provide task-specific guidance for the current run. They control how the agent should approach the immediate task without becoming part of the permanent conversation record. Instructions are re-applied by the agent on each call but are not replayed from prior turns in message history.

**User prompts** contain the actual request from the end user, including their goals, preferences, and situational details.

## System Prompts: Persistent Identity

The notebook begins by creating an agent with only a system prompt:

```python
system_prompt = """You are a concise technical writer.
Always respond in exactly 2 sentences.
Never use bullet points."""

agent_system = get_agent(system_prompt=system_prompt)
```

This system prompt defines three invariants: the agent's role (technical writer), a formatting constraint (exactly 2 sentences), and a prohibition (no bullet points). When we ask this agent to explain a REST API, it must comply with all three rules.

The `get_agent` function accepts a `system_prompt` parameter that becomes part of the agent's configuration. Every request to this agent will include this system prompt in the context sent to the LLM.

## Instructions: Per-Run Control

Next, the notebook creates an agent with instructions instead:

```python
instructions = """Respond in a casual, friendly tone.
Use simple analogies to explain technical concepts."""

agent_instructions = get_agent(instructions=instructions)
```

Instructions serve a similar purpose to system prompts in shaping the agent's behavior, but with a key difference: they are designed for task-specific control rather than persistent identity. The distinction becomes important when managing multi-turn conversations with message history.

Running the same prompt ("Explain what a REST API is") with this agent produces a different response style: casual, friendly, and using analogies rather than the concise technical writing style of the first agent.

## Combining Both Layers

In practice, you often want both persistent identity and task-specific control. The notebook demonstrates this combination:

```python
system_prompt = "You are an expert Python developer."
instructions = "When explaining code, always include a brief example."

agent_combined = get_agent(system_prompt=system_prompt, instructions=instructions)
```

The system prompt establishes the agent's expertise domain (Python development), while the instructions specify how to structure responses for the current session (include examples). This separation keeps identity concerns separate from task concerns.

When asked "What is a list comprehension?", the agent responds as a Python expert (system prompt) and includes a code example (instructions). Both layers contribute to the final response.

## Message History Interaction

The final section demonstrates how these layers interact with conversation history. In multi-turn conversations, you pass message history to maintain context across turns:

```python
# Turn 1
prompt_1 = "What is a generator in Python?"
result_1, nodes_1 = await run_agent(agent_combined, prompt_1)

# Turn 2 with history
message_history = nodes_to_message_history(nodes_1)
prompt_2 = "How does it differ from a list comprehension?"
result_2, _ = await run_agent(agent_combined, prompt_2, message_history=message_history)
```

In Turn 2, the agent understands that "it" refers to generators because the message history provides that context. The agent can compare generators to list comprehensions because it has access to the previous exchange.

The system prompt ("expert Python developer") is part of the stored context and persists across turns. The instructions ("include brief example") are applied fresh on each call by the agent framework. This distinction matters when designing agents that need consistent identity across a conversation while allowing task-specific behavior to evolve.

## Practical Guidelines

When designing prompt layers for your agents, consider these principles.

Use system prompts for invariants that must hold across all interactions: safety policies, role definitions, output format constraints, and non-negotiable rules. Keep system prompts narrow to avoid conflicts with task-specific requirements.

Use instructions for task-specific procedure: how to approach the current request, what checks to perform, domain constraints for this particular use case, and output schema expectations. Instructions can be longer and more detailed since they do not accumulate in message history.

Keep user prompts focused on the actual request. Avoid embedding procedural guidance in user prompts; that belongs in instructions.

The effective prompt is the concatenation of all layers. Because LLMs do not truly "remember" across calls, everything you want the model to condition on must be present in the tokens you send. Designing clear boundaries between prompt layers makes it easier to maintain, debug, and evolve your agents.

## Key Takeaways

Prompts in agentic systems have multiple layers serving different purposes. System prompts define persistent identity and invariants. Instructions provide per-run task control. User prompts carry the actual request. Understanding which content belongs in each layer, and how each layer interacts with message history, is essential for building predictable and maintainable agents.
