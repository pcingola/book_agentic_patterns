# Hands-On: Multi-Turn Conversations

Language models are stateless. Each time you send a prompt, the model processes only that input and has no memory of previous interactions. To create coherent conversations that span multiple turns, you must explicitly provide the conversation history with each new request.

This hands-on explores message history using `example_multi_turn.ipynb`, building on the translation examples from the previous section.

## The Problem: Context Loss

Consider this two-turn interaction:

```
Turn 1 - User: "Translate to French: I like coffee."
Turn 1 - Agent: "J'aime le café."

Turn 2 - User: "How do you like it?"
```

If you send the second prompt without any context, the agent has no idea what "it" refers to. The conversation breaks down because the model doesn't remember discussing coffee or translation.

## The Solution: Message History

The `run_agent` function accepts a `message_history` parameter containing previous messages from the conversation. When you include this history, the model can interpret new prompts in the proper context.

```python
agent_run, nodes = await run_agent(
    agent,
    prompt,
    message_history=previous_messages
)
```

The helper function `nodes_to_message_history` extracts the conversation history from the nodes returned by a previous agent run.

## Example: Translation Follow-Up

Let's examine `example_multi_turn.ipynb`, which demonstrates a simple two-turn conversation.

### Setup

```python
from agentic_patterns.core.agents import get_agent, run_agent
from agentic_patterns.core.agents.utils import nodes_to_message_history

agent = get_agent()
```

We create a basic agent without a system prompt, similar to `example_translate_basic.ipynb`.

### Turn 1: Translation Request

```python
prompt_1 = "Translate to French: I like coffee."

agent_run_1, nodes_1 = await run_agent(agent, prompt_1)

print(agent_run_1.result.output)
# Output: J'aime le café.
```

The agent translates the sentence to French. The conversation now contains two messages: the user's request and the agent's response.

### Turn 2: Follow-Up Question With History

```python
# Extract message history from Turn 1
message_history = nodes_to_message_history(nodes_1)

prompt_2 = "How do you like it?"

agent_run_2, nodes_2 = await run_agent(agent, prompt_2, message_history=message_history)

print(agent_run_2.result.output)
# Output: With milk and sugar. / Black. / etc.
```

The agent understands that "it" refers to coffee because we provided the message history. The model sees the complete conversation:

```
Message 1 (user): "Translate to French: I like coffee."
Message 2 (assistant): "J'aime le café."
Message 3 (user): "How do you like it?"
```

With this context, the agent can respond appropriately about coffee preferences.

### Turn 2: Without History

To demonstrate the importance of message history, the notebook shows what happens when you omit it:

```python
# Run the same prompt WITHOUT message history
agent_run_no_history, _ = await run_agent(agent, prompt_2)

print("Without context:", agent_run_no_history.result.output)
# Output might be: "How do I like what? Can you provide more context?"
```

Without history, the agent cannot resolve the pronoun "it" and cannot provide a meaningful response.

## Extracting Message History

The `nodes_to_message_history` utility converts agent run nodes into the message format required by `run_agent`:

```python
final_message_history = nodes_to_message_history(nodes_2)

print(f"Total messages: {len(final_message_history)}")

for i, msg in enumerate(final_message_history, 1):
    print(f"Message {i}:")
    print(msg)
```

This shows the complete conversation structure. Each message contains:
- `role`: The sender (user or assistant)
- `content`: The message text
- `parts`: Message components (text, tool calls, tool returns)

## How It Works Internally

When you call `run_agent` with `message_history`, the framework sends the complete conversation to the LLM:

```python
# Simplified representation of what gets sent
messages = [
    {"role": "user", "content": "Translate to French: I like coffee."},
    {"role": "assistant", "content": "J'aime le café."},
    {"role": "user", "content": "How do you like it?"}
]
```

The model processes all messages together to generate a contextually appropriate response. Each subsequent turn includes the growing conversation history.

## Message History vs System Prompts

Message history and system prompts serve different purposes:

**System prompts** define persistent behavior across the entire conversation. They establish the agent's role, instructions, or personality. System prompts appear at the beginning of the message sequence and remain constant.

**Message history** contains the actual back-and-forth exchange between user and agent. It grows with each turn as new messages are added.

In `example_translate_system_prompt.ipynb`, we used a system prompt:

```python
system_prompt = f"Translate into {language}"
agent = get_agent(system_prompt=system_prompt)
```

You can combine system prompts with message history. The system prompt sets the context, and message history tracks the conversation:

```python
# System prompt + message history
messages = [
    {"role": "system", "content": "Translate into French"},
    {"role": "user", "content": "I like coffee."},
    {"role": "assistant", "content": "J'aime le café."},
    {"role": "user", "content": "How do you like it?"}
]
```

## Production Considerations

When building production systems with multi-turn conversations, consider these factors:

**Token limits**: LLMs have maximum context windows (e.g., 128K tokens). Very long conversations may exceed this limit, requiring you to truncate or summarize older messages.

**Cost**: You pay for every token sent, including message history. Each turn resends the entire conversation, so costs grow with conversation length.

**Storage**: For conversations that persist across sessions (like a chatbot that resumes later), store message history in a database.

**Context boundaries**: In multi-user systems, ensure you don't accidentally mix message histories between different conversations.

**Error handling**: If an agent run fails, decide whether to include the failed turn in the history or retry without it.

## The nodes_to_message_history Utility

Agent runs return "nodes" representing each execution step. These nodes include requests, responses, tool calls, and tool results. The `nodes_to_message_history` function extracts only the messages needed for conversation history:

```python
def nodes_to_message_history(nodes: list, remove_last_call_tool: bool = True) -> Sequence[ModelMessage]:
    """Convert a list of nodes to message history."""
    messages = []
    for n in nodes:
        if hasattr(n, "request"):
            messages.append(n.request)
        elif hasattr(n, "response"):
            messages.append(n.response)
        elif hasattr(n, "model_response"):
            messages.append(n.model_response)

    # Optionally remove the last CallToolsNode if present
    if remove_last_call_tool and len(messages) >= 2 and has_tool_calls(messages[-1]):
        messages = messages[:-1]

    return messages
```

This abstraction shields you from Pydantic-AI's internal node structure, letting you work with conversations at a higher level.

## Key Patterns

When implementing multi-turn conversations:

**Extract history after each turn**: Call `nodes_to_message_history` immediately after each `run_agent` to capture the updated conversation state.

**Pass complete history**: Always pass the full history from the previous turn. Don't try to cherry-pick individual messages.

**Chain turns properly**: Each turn should use the history from the immediately preceding turn to maintain continuity.

```python
# Pattern for chaining turns
agent_run_1, nodes_1 = await run_agent(agent, prompt_1)
history_1 = nodes_to_message_history(nodes_1)

agent_run_2, nodes_2 = await run_agent(agent, prompt_2, message_history=history_1)
history_2 = nodes_to_message_history(nodes_2)

agent_run_3, nodes_3 = await run_agent(agent, prompt_3, message_history=history_2)
```

## Why This Matters

Multi-turn conversations are foundational for advanced agentic patterns:

**Tool use across turns**: An agent might call a tool in one turn, then reference the tool result in a subsequent turn while explaining its reasoning.

**Clarification and refinement**: The agent can ask clarifying questions and incorporate the user's answers into its next response.

**Memory and context**: The agent can reference information from earlier in the conversation without requiring the user to repeat themselves.

**Planning and execution**: Complex tasks can be broken across multiple turns, with the agent maintaining context about the overall goal while working on individual steps.

These capabilities depend on maintaining conversation history across multiple interactions.

## Key Takeaways

Language models don't inherently remember previous turns. Multi-turn conversations require explicitly passing message history with each new prompt. Use `nodes_to_message_history` to extract conversation history from agent run results. Pass this history to the `message_history` parameter in subsequent `run_agent` calls.

Without message history, each turn is isolated and the agent lacks context. With message history, agents can understand references to previous exchanges, maintain coherent conversations across multiple turns, and build on information gathered in earlier interactions.

This capability is essential for building useful agentic systems and serves as the foundation for more sophisticated patterns we'll explore in later chapters.
