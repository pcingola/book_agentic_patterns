## Hands-On: Tool Use

Tool use is the mechanism by which language models cross the boundary between reasoning and action. Instead of generating text that describes what should happen, the model invokes external functions that actually make it happen. This transforms a language model from a text generator into an agent capable of interacting with the world.

This hands-on explores tool use through `example_tools.ipynb`, demonstrating how models decide when to use tools and how tool results flow back into the reasoning process.

## Why Tools Matter

Language models excel at pattern matching and text generation, but they have fundamental limitations. They cannot reliably perform precise arithmetic, access real-time data, or interact with external systems. Consider asking a model to add two large numbers:

```
What is 40123456789 + 2123456789?
```

A model might attempt to compute this mentally, but large number arithmetic is error-prone when done through token prediction. The model wasn't trained to be a calculator; it was trained to predict text. Even if it produces the correct answer sometimes, it's unreliable.

Tools solve this by delegating specific operations to external code. Instead of predicting what the sum might be, the model calls an `add` function that computes it exactly. The model's job becomes deciding when to use a tool and constructing the correct arguments, not performing the computation itself.

## Defining Tools

In `example_tools.ipynb`, tools are defined as Python functions:

```python
def add(a: int, b: int) -> int:
    """Add two numbers"""
    print(f"Adding {a} + {b}")
    return a + b

def sub(a: int, b: int) -> int:
    """Subtract two numbers"""
    print(f"Subtracting {a} - {b}")
    return a - b
```

Three elements matter here. First, the function name tells the model what the tool does. Second, the type hints (`a: int, b: int`) define what arguments the tool accepts. Third, the docstring provides a natural language description that helps the model understand when to use the tool.

The framework converts these Python functions into JSON schemas that are sent to the model alongside the conversation. The model sees something like:

```json
{
  "name": "add",
  "description": "Add two numbers",
  "parameters": {
    "type": "object",
    "properties": {
      "a": {"type": "integer"},
      "b": {"type": "integer"}
    },
    "required": ["a", "b"]
  }
}
```

This schema is part of the model's context. When the model decides a tool is needed, it generates a structured output specifying which tool to call and with what arguments.

## The Tool Use Loop

When we create an agent with tools and run it:

```python
agent = get_agent(tools=[add, sub])

prompt = "What is the sum of 40123456789 and 2123456789?"
agent_run, nodes = await run_agent(agent, prompt, verbose=True)
```

The following sequence occurs:

1. The model receives the prompt along with the tool schemas.
2. The model reasons that this is an addition problem and that the `add` tool is appropriate.
3. Instead of generating a text answer, the model outputs a tool call: `add(a=40123456789, b=2123456789)`.
4. The framework intercepts this, executes the Python function, and captures the result: `42247245578`.
5. The result is sent back to the model as a new message in the conversation.
6. The model generates its final response incorporating the tool result.

This loop is the foundation of agentic behavior. The model doesn't just predict text; it takes actions and observes their results. Each tool call is a deliberate decision, and each result feeds back into the model's reasoning.

## Tool Selection

The model must decide which tool to use, if any. Given our two tools (`add` and `sub`), the model selects based on the task. If the prompt asks for a sum, it calls `add`. If it asks for a difference, it calls `sub`. If the task doesn't require either operation, the model responds without using tools.

This selection happens through the model's understanding of the tool descriptions and the current context. Good tool names and docstrings make selection more reliable. A tool named `add` with description "Add two numbers" is unambiguous. A tool named `process` with description "Do something with numbers" would be harder for the model to use correctly.

## Why This Example Uses Arithmetic

Arithmetic might seem trivial, but it illustrates tool use precisely because models are unreliable at it. When a model adds small numbers like 2 + 3, it's essentially recalling memorized patterns from training data. When numbers grow large or unusual, the model's accuracy drops because it's pattern matching, not computing.

By using the `add` tool, the model delegates to code that performs exact arithmetic. The print statement in the tool (`print(f"Adding {a} + {b}")`) makes the tool call visible, showing that the computation happened in Python, not in the model's weights.

This principle extends to any operation where precision matters: database queries, API calls, file operations, scientific calculations. The model reasons about what to do; the tool does it correctly.

## The Feedback Loop

Tool use creates a feedback loop between the model and external systems. The model proposes an action, the system executes it, the result becomes new context, and the model continues reasoning. This loop can repeat multiple times in a single conversation.

For example, a more complex task might require the model to call `add` multiple times, or to call `add` and then `sub` on the result. Each tool call extends the conversation with new information that the model incorporates into its next step. This is how agents accomplish multi-step tasks: not by predicting all steps at once, but by taking one action, observing the result, and deciding what to do next.

## Connection to Other Patterns

Tool use is foundational to other agentic patterns. ReAct interleaves reasoning with tool calls in an explicit text format. Planning patterns use tools to execute steps of a plan. Verification patterns use tools to check results. In each case, the core mechanism is the same: the model decides to act, the tool executes, and the result informs further reasoning.

Understanding tool use at this basic level makes the more complex patterns easier to follow. They all build on this same loop of decision, execution, and observation.

## Key Takeaways

Tools enable models to perform actions they cannot do through text generation alone. A model that can call tools is qualitatively different from one that only generates text.

Tools are defined as functions with clear signatures and descriptions. The framework converts these into schemas that the model uses to understand when and how to call each tool.

The tool use loop consists of the model proposing a tool call, the system executing it, and the result being fed back as new context. This loop can repeat multiple times to accomplish complex tasks.

Tool selection depends on good naming and descriptions. The model chooses tools based on its understanding of what each tool does and what the current task requires.
