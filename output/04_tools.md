# Tools

# Chapter 4: Tool Use

## Tool Use (from Core Patterns)

Tool use is the core of AI agents and agentic behavior: it is the pattern by which a model reasons about the world and then deliberately acts on it through external capabilities, closing the loop between cognition and execution.

### Historical perspective

As with other agentic patterns, tool use has deep roots in classical AI. Early symbolic agents already separated reasoning from acting, modeling actions as operators with preconditions and effects. These systems assumed that an agent could invoke well-defined procedures to change the environment or query it, and then continue reasoning based on the results.

With statistical and neural approaches, this separation weakened for a time, as models focused on end-to-end prediction. The reintroduction of explicit tool use emerged gradually through retrieval-based systems, program synthesis, and semantic parsing, where models produced structured artifacts—queries, code, or commands—that were executed externally. The decisive shift came with large language models that could reliably emit structured outputs and conditionally decide to use them. At this point, tool use stopped being an implementation detail and became a conceptual foundation of agentic systems: a model that can reason, decide to act, observe the result, and iterate is qualitatively different from one that only generates text.

### The pattern in detail

Tool use formalizes how an agent crosses the boundary between internal reasoning and external action. A tool is defined not by its implementation, but by a clear interface: what inputs it accepts, what outputs it produces, and what side effects it may have. From the agent’s perspective, invoking a tool is a deliberate act governed by constraints, rather than an unstructured guess.

A key concept is that tool invocation is itself part of the reasoning trace. The model must first determine that a tool is appropriate, then select which tool to use, and finally construct a call that satisfies the tool’s contract. This requires explicit structure in the interaction: arguments must be well-formed, optional fields must be handled correctly, and invalid calls must be detectable. In practice, this introduces a disciplined form of generation, where free-form text is replaced—at specific moments—by structured outputs that can be validated before execution.

Another central idea is that tools participate in a feedback loop. A tool call produces a result, which is fed back into the model as new context. The agent then reasons over this result, potentially making further tool calls or deciding that the task is complete. Errors are not exceptional; they are expected. A failed call, a validation error, or an unexpected result becomes just another observation for the agent to reason about. Robust tool use therefore assumes the possibility of retries, alternative strategies, or repair, rather than a single, flawless invocation.

Advanced tool use also emphasizes separation of concerns. The model does not need to know how a tool is implemented, only what it promises. Conversely, the tool does not need to understand the broader goal, only how to execute a specific operation correctly. This separation enables strong guarantees: tool inputs can be validated, outputs can be typed or structured, and side effects can be constrained. Over time, this makes agentic systems more predictable and easier to evolve, as tools can change internally without retraining the reasoning model, as long as their external contracts remain stable.

Finally, tool use generalizes beyond simple function calls. It applies equally to querying knowledge, performing computations, invoking long-running tasks, or interacting with external systems. What unifies these cases is not the nature of the tool, but the pattern: the agent reasons up to the point where action is required, delegates that action through a constrained interface, and then resumes reasoning with the outcome. This loop is what turns a language model into an agent.

### References

1. Russell, S., Norvig, P. *Artificial Intelligence: A Modern Approach*. Prentice Hall, 1995.
2. Zettlemoyer, L., Collins, M. *Learning to Map Sentences to Logical Form*. UAI, 2005.
3. Lewis, P. et al. *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*. NeurIPS, 2020.
4. Schick, T. et al. *Toolformer: Language Models Can Teach Themselves to Use Tools*. arXiv, 2023.
5. Yao, S. et al. *ReAct: Synergizing Reasoning and Acting in Language Models*. ICLR, 2023.

## Structured Output

Structured output is the pattern of treating a model’s response not as free-form text, but as a value that must conform to an explicitly defined, machine-readable shape.

### Historical perspective

Long before large language models, systems that generated or interpreted language were already constrained by structure. Early dialogue systems and natural language generators relied on templates, grammars, and frame-based representations to ensure that what the system produced could be consumed by databases or procedural code. The output of these systems was “language-like,” but its primary purpose was functional rather than conversational.

The shift to neural sequence models in the 2010s changed this balance. Models became exceptionally good at producing fluent text, but the explicit structure that software systems depend on largely disappeared. For a time, this was acceptable because models were mostly used as assistants or interfaces for humans. As soon as they began to act as components inside larger systems—calling APIs, producing plans, or controlling workflows—the lack of structure became a liability.

Research on semantic parsing, program synthesis, and constrained decoding showed that neural models could, in fact, be guided to produce well-formed logical forms, programs, and data structures. At the same time, practical engineering converged on schemas and typed interfaces as the most robust way to integrate probabilistic models into deterministic systems. Structured output emerged from this convergence as a necessary pattern for reliable, agentic behavior.

### Pattern explanation

In an agentic system, structured output defines the moment where reasoning becomes action. Instead of asking the model to “say what to do,” the system asks it to *return* something: a data object whose shape is known in advance and whose validity can be checked automatically.

This immediately changes the nature of the interaction. If unstructured text is allowed as a possible outcome, the model can remain in a conversational mode—asking clarifying questions or explaining uncertainty. When text is excluded and only structured forms are permitted, the model is forced into a decision-making posture. It must commit to a concrete result that satisfies the contract, or fail in a way the system can detect.

Over time, practitioners have learned that it is often better to allow a small number of alternative output forms rather than one large, complicated schema. Each alternative corresponds to a clear semantic outcome: a successful result, a request for missing information, or a deliberate refusal. Keeping these forms simple increases the likelihood that the model will adhere to them and makes the agent’s control flow explicit and inspectable.

Another important aspect is normalization. Even when the logical outcome is a single number or a list, systems typically wrap the result in a structured object. This creates a uniform interface for validation, logging, storage, and tool invocation, and avoids special cases that complicate agent runtimes.

Structured output also fundamentally improves error handling. When outputs are validated against a schema, mistakes are no longer vague or implicit. A missing field, a type mismatch, or an invalid value becomes a concrete failure mode that can trigger a targeted retry, a repair prompt, or a fallback path. This turns uncertainty from something that leaks through the system into something that is contained and managed.

Finally, structured output clarifies agent lifecycles. Some structured responses are meant to end a run and hand control to deterministic code—executing a transaction, committing a plan, or emitting a final result. Others are intermediate artifacts, intended to be fed back into the model as part of an ongoing reasoning loop. Treating these as distinct roles prevents accidental feedback loops and makes long-running agents easier to reason about.

In this sense, structured output is not an optional refinement but a foundational pattern. It is what allows tool use to be reliable, state to be explicit, and agentic systems to scale beyond demonstrations into robust software.

### References

1. Zettlemoyer, L., Collins, M. *Learning to Map Sentences to Logical Form: Structured Classification with Probabilistic Categorial Grammars*. UAI, 2005.
2. Wong, Y. W., Mooney, R. J. *Learning for Semantic Parsing with Statistical Machine Translation*. NAACL, 2006.
3. Yin, P., Neubig, G. *A Syntactic Neural Model for General-Purpose Code Generation*. ACL, 2017.
4. OpenAI. *Function Calling and Structured Outputs*. Technical documentation, 2023.
5. PydanticAI. *Structured Output Concepts*. Documentation, 2024–2025. [https://ai.pydantic.dev/output/](https://ai.pydantic.dev/output/)

# Chapter 4: Tool Use — the Fundamental Pattern

## Tool Discovery and Selection

Tool discovery and selection is the pattern by which an agent determines which external capabilities are relevant to a task and decides which of them to invoke in order to make progress toward its goal.

### Historical perspective

The roots of tool discovery and selection lie in classical AI research on planning, action selection, and multi-agent systems. In early symbolic AI, agents operated over explicitly defined action sets, where each action had preconditions and effects. Selecting a “tool” meant choosing an operator from a known and fixed action space. As systems grew more complex, research in the 1990s and early 2000s expanded toward automated service composition and semantic web services, where agents dynamically selected services based on declarative descriptions rather than hard-coded logic.

With the advent of large language models, tool discovery and selection re-emerged as a central problem in a new form. Instead of symbolic operators, agents were now expected to choose among APIs, databases, search systems, or code execution environments, often described in natural language. Early approaches relied on prompt engineering and manual rules to guide tool use, but these quickly proved brittle as the number of tools increased. This led to structured tool descriptions and explicit reasoning steps that allow models to decide *when* a tool is needed and *which* one is appropriate, forming the basis of modern tool-augmented and agentic systems.

### The pattern explained

At its core, tool discovery and selection separates *capability awareness* from *capability execution*. An agent reasons over descriptions of available tools—what they do, what inputs they require, what outputs they produce, and what constraints they impose—without being tightly coupled to their implementations. This allows the agent to treat tools as interchangeable capabilities rather than fixed function calls.

In simple systems, a single agent may both select and invoke tools. However, as tool catalogs grow, this approach becomes inefficient. Presenting dozens or hundreds of tools to an agent increases context length, dilutes attention, and raises the likelihood of incorrect selection. To address this, tool discovery and selection can be structured as a two-stage agent process.

In the first stage, a *tool-selection agent* performs global reasoning over the task and the full set of available tools. This agent does not execute tools. Its responsibility is to analyze the task requirements and identify which capabilities are potentially relevant. The output of this stage is a structured filter: a restricted subset of tools, possibly accompanied by constraints such as read-only access or domain limitations. This step may be cached or reused across similar tasks, since it is concerned with capability matching rather than execution details.

In the second stage, a *task-execution agent* is invoked with the original task and only the restricted tool set produced by the first stage. From this agent’s perspective, the reduced set of tools defines the entire action space. Because irrelevant tools are absent from its context, the agent can reason more efficiently, produce more reliable tool invocations, and avoid unintended or unsafe actions. This agent applies standard tool-use patterns—deciding when to act, invoking tools with structured inputs, and incorporating outputs into its ongoing reasoning.

This separation mirrors long-standing architectural principles in AI and distributed systems: planning versus acting, control plane versus execution plane, and global reasoning versus local decision-making. Tool discovery becomes an explicit, inspectable step, rather than an implicit side effect of prompting.

### Why the pattern matters

Treating tool discovery and selection as a first-class pattern enables agentic systems to scale. New tools can be added without overwhelming execution agents, safety and permission policies can be enforced during selection, and context length can be tightly controlled. Most importantly, agents remain adaptable: they reason over *what capabilities exist* independently of *how those capabilities are used*.

As agents evolve into long-running systems operating over large and dynamic tool ecosystems, this pattern becomes essential. Without explicit tool discovery and selection, tool use degrades into ad hoc prompting. With it, tool use becomes a deliberate, structured, and scalable component of agentic behavior.

### References

1. Russell, S., Norvig, P. *Artificial Intelligence: A Modern Approach*. Prentice Hall, 1995.
2. McIlraith, S., Son, T. C., Zeng, H. *Semantic Web Services*. IEEE Intelligent Systems, 2001.
3. Schick, T. et al. *Toolformer: Language Models Can Teach Themselves to Use Tools*. NeurIPS, 2023.
4. OpenAI. *Function Calling and Tool-Augmented Language Models*. OpenAI documentation, 2023.
5. Pydantic. *Structured Outputs and Tool Integration Concepts*. Pydantic AI documentation, 2024.






## MCP

* MCP motivation and scope: Why a standardized protocol is needed to connect agents with tools, data, and context.

  * [https://www.anthropic.com/news/model-context-protocol](https://www.anthropic.com/news/model-context-protocol)
  * [https://modelcontextprotocol.io/docs/learn/introduction](https://modelcontextprotocol.io/docs/learn/introduction)

* MCP architectural model: Host, client, and server roles and how they map onto an agent execution loop.

  * [https://modelcontextprotocol.io/docs/learn/architecture](https://modelcontextprotocol.io/docs/learn/architecture)

* Protocol layers: Separation between the JSON-RPC data model and transport mechanisms.

  * [https://modelcontextprotocol.io/specification/2025-06-18/basic](https://modelcontextprotocol.io/specification/2025-06-18/basic)
  * [https://www.jsonrpc.org/specification](https://www.jsonrpc.org/specification)

* Lifecycle and capability negotiation: Initialization, versioning, and feature discovery for interoperable agents.

  * [https://modelcontextprotocol.io/specification/2025-06-18/basic/lifecycle](https://modelcontextprotocol.io/specification/2025-06-18/basic/lifecycle)

* Tools primitive: How agents invoke side-effectful actions via typed, schema-defined tools.

  * [https://modelcontextprotocol.io/specification/2025-06-18/server/tools](https://modelcontextprotocol.io/specification/2025-06-18/server/tools)

* Resources primitive: Supplying structured, addressable context (files, data, memory) to agents.

  * [https://modelcontextprotocol.io/specification/2025-06-18/server/resources](https://modelcontextprotocol.io/specification/2025-06-18/server/resources)

* Prompts primitive: Reusable prompt templates as shared cognitive scaffolding.

  * [https://modelcontextprotocol.io/specification/2025-06-18/server/prompts](https://modelcontextprotocol.io/specification/2025-06-18/server/prompts)

* Transport choices: stdio vs HTTP/Streamable HTTP and their implications for deployment and scaling.

  * [https://modelcontextprotocol.io/specification/2025-06-18/basic/transports](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports)

* Security and authorization: Threat boundaries, safe server design, and OAuth 2.1 for remote access.

  * [https://modelcontextprotocol.io/specification/2025-06-18/basic/security_best_practices](https://modelcontextprotocol.io/specification/2025-06-18/basic/security_best_practices)
  * [https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization](https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization)

* Practical agent integration: How planners and executors use MCP clients in real agent systems.

  * [https://modelcontextprotocol.io/docs/learn/client-concepts](https://modelcontextprotocol.io/docs/learn/client-concepts)


