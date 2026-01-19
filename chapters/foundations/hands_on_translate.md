# Hands-On: System Prompts vs. User Prompts

This section explores two different approaches to prompting language models using a translation task as our example. We'll compare `example_translate_basic.ipynb` and `example_translate_system_prompt.ipynb` to understand when and why to separate instructions from content.

## Two Ways to Prompt

There are fundamentally two ways to give instructions to a language model:

**Single prompt approach**: Combine instructions and content in one message. Example: "Translate to French: I like coffee."

**Separated prompt approach**: Put instructions in a system prompt and content in a user prompt. System prompt: "Translate into French". User prompt: "I like coffee."

Both approaches produce the same output, but they differ in reusability, maintainability, and how the model processes the instructions.

## Example 1: Everything in the User Prompt

Let's examine `example_translate_basic.ipynb`:

```python
from agentic_patterns.core.agents import get_agent, run_agent

agent = get_agent()
prompt = "Translate to French: I like coffee."
agent_run, nodes = await run_agent(agent, prompt)
print(agent_run.result.output)
```

This approach is straightforward. The entire task is described in a single string. The model receives one message containing both the instruction (translate to French) and the content (I like coffee).

When you send this prompt, the model receives a message structure like:

```json
{
  "role": "user",
  "content": "Translate to French: I like coffee."
}
```

This works perfectly fine for one-off tasks. However, consider what happens if you need to translate multiple sentences. You would need to construct a new prompt each time:

```python
prompt1 = "Translate to French: I like coffee."
prompt2 = "Translate to French: The weather is nice."
prompt3 = "Translate to French: Good morning."
```

The instruction "Translate to French:" is repeated in every prompt, and the structure is harder to maintain if you want to change the target language or instruction style.

## Example 2: Separating System and User Prompts

Now let's examine `example_translate_system_prompt.ipynb`:

```python
from agentic_patterns.core.agents import get_agent, run_agent

language = 'French'
system_prompt = f"Translate into {language}"
agent = get_agent(system_prompt=system_prompt)

prompt = "I like coffee."
agent_run, nodes = await run_agent(agent, prompt, verbose=True)
print(agent_run.result.output)
```

This approach separates concerns. The system prompt defines the agent's behavior (translate into French), while the user prompt provides the content to process (I like coffee).

When you send this prompt, the model receives a message structure like:

```json
[
  {
    "role": "system",
    "content": "Translate into French"
  },
  {
    "role": "user",
    "content": "I like coffee."
  }
]
```

## Understanding System Prompts

System prompts serve a specific purpose in how language models process conversations. When you provide a system prompt, it establishes the context, role, or behavior for the entire conversation. The model treats system messages differently from user messages:

**Priority**: System messages typically carry higher weight in guiding model behavior. They set the frame within which user messages are interpreted.

**Persistence**: In multi-turn conversations, the system prompt remains constant while user prompts change. This makes it ideal for defining an agent's persistent role or instructions.

**Separation of concerns**: System prompts contain meta-instructions about how to process input, while user prompts contain the actual input to process.

In our translation example, "Translate into French" is a meta-instruction. It tells the model what to do with whatever content appears in the user prompt. The actual content "I like coffee" is the input to process according to those instructions.

## Practical Benefits of Separation

The separated approach offers several advantages for production systems:

**Reusability**: Create the agent once with its system prompt, then run it with different user prompts. No need to reconstruct the instruction part each time.

```python
language = 'French'
system_prompt = f"Translate into {language}"
agent = get_agent(system_prompt=system_prompt)

# Translate multiple sentences with the same agent
sentences = ["I like coffee.", "The weather is nice.", "Good morning."]
for sentence in sentences:
    agent_run, _ = await run_agent(agent, sentence)
    print(agent_run.result.output)
```

**Maintainability**: Change the instruction once in the system prompt rather than updating every user prompt. Want to switch from French to Spanish? Modify one line.

**Clarity**: The code structure mirrors the conceptual structure. Instructions live separately from data, making the system easier to understand and modify.

**Consistency**: The model receives instructions in the same format across all requests, reducing variability in how instructions are interpreted.

## When to Use Each Approach

Use the single prompt approach when you have one-off tasks, simple scripts where reusability isn't a concern, or when you're experimenting and want minimal setup.

Use the separated approach when building reusable agents that process multiple inputs, creating systems where behavior needs to be configurable, working with multi-turn conversations where context persists, or building production systems that require maintainability.

For our running enterprise example throughout this book, we'll consistently use separated prompts because production agentic systems benefit from clear separation between agent behavior and input data.

## Implementation in Pydantic-AI

When you call `get_agent(system_prompt=system_prompt)`, our helper library passes the system prompt to Pydantic-AI's `Agent` constructor. Pydantic-AI then includes this system message in every conversation with the model.

Internally, Pydantic-AI constructs the message sequence:

```python
# Simplified representation of what happens
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": user_prompt}
]
```

This message structure is then sent to whichever model provider you've configured (OpenAI, Anthropic, AWS Bedrock, etc.). All major LLM APIs support this system/user message distinction, making it a portable pattern across providers.

## Key Takeaways

System prompts define agent behavior and persist across multiple interactions. User prompts provide the specific content to process. Separating them creates more maintainable, reusable, and scalable agent systems.

For simple one-off tasks, combining everything in a single prompt works fine. For production systems and reusable agents, separating system and user prompts is the better architectural choice.

This separation becomes even more important as we introduce tools, memory, and multi-agent orchestration in later chapters. The system prompt defines what an agent is and what it can do. The user prompt specifies what it should do right now.
