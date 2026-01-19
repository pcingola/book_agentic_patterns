## Tool Use

Tool use is the core of AI agents and agentic behavior: it is the pattern by which a model reasons about the world and then deliberately acts on it through external capabilities, closing the loop between cognition and execution.

### The pattern in detail

Tool use formalizes how an agent crosses the boundary between internal reasoning and external action. A tool is defined not by its implementation, but by a clear interface: what inputs it accepts, what outputs it produces, and what side effects it may have. From the agent’s perspective, invoking a tool is a deliberate act governed by constraints, rather than an unstructured guess.

A key concept is that tool invocation is itself part of the reasoning trace. The model must first determine that a tool is appropriate, then select which tool to use, and finally construct a call that satisfies the tool’s contract. This requires explicit structure in the interaction: arguments must be well-formed, optional fields must be handled correctly, and invalid calls must be detectable. In practice, this introduces a disciplined form of generation, where free-form text is replaced—at specific moments—by structured outputs that can be validated before execution.

Another central idea is that tools participate in a feedback loop. A tool call produces a result, which is fed back into the model as new context. The agent then reasons over this result, potentially making further tool calls or deciding that the task is complete. Errors are not exceptional; they are expected. A failed call, a validation error, or an unexpected result becomes just another observation for the agent to reason about. Robust tool use therefore assumes the possibility of retries, alternative strategies, or repair, rather than a single, flawless invocation.

Advanced tool use also emphasizes separation of concerns. The model does not need to know how a tool is implemented, only what it promises. Conversely, the tool does not need to understand the broader goal, only how to execute a specific operation correctly. This separation enables strong guarantees: tool inputs can be validated, outputs can be typed or structured, and side effects can be constrained. Over time, this makes agentic systems more predictable and easier to evolve, as tools can change internally without retraining the reasoning model, as long as their external contracts remain stable.

Finally, tool use generalizes beyond simple function calls. It applies equally to querying knowledge, performing computations, invoking long-running tasks, or interacting with external systems. What unifies these cases is not the nature of the tool, but the pattern: the agent reasons up to the point where action is required, delegates that action through a constrained interface, and then resumes reasoning with the outcome. This loop is what turns a language model into an agent.

