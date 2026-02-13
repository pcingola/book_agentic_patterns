## What is an Agent / Agentic System

An agentic system is software that repeatedly decides what to do next—often by invoking tools—based on its current state, until it achieves a goal.

```
Agent = LLM + tools
```

#### The concept of AI agentic systems

An AI agentic system can be understood as an instantiation of the classic agent loop, implemented with contemporary components. The system maintains some notion of state (explicit or implicit), observes new information, decides on an action, executes that action via tools or APIs, and incorporates the result before repeating the process.

From a reinforcement learning perspective, this is immediately familiar. The “environment” may be a database, an internal service, a file system, or the open web. “Actions” correspond to tool calls. “Observations” are the outputs of those tools. The policy is approximated by a language model conditioned on instructions, context, and prior interaction history. Even when no explicit reward signal is present, the structure of the interaction mirrors the Bellman-style decomposition of decisions over time: each step is chosen with awareness that it will influence future options.

The crucial difference from traditional chat-based systems is that decisions are not terminal. A single response is rarely sufficient. Instead, the model is embedded in a loop that allows it to refine its understanding of the task and adapt its actions based on intermediate results.

#### Key characteristics that distinguish agentic systems from traditional software

Traditional software encodes control flow explicitly. Decisions are implemented as conditional branches, loops are fixed, and the system’s behavior is fully specified ahead of time.

Agentic systems shift part of this responsibility to the model. The developer defines the goal, constraints, and available actions, while the model determines *which* action to take and *when*. This makes agentic systems goal-directed rather than procedure-directed: the emphasis is on achieving an outcome, not following a predefined script.

Another defining characteristic is the centrality of tools. In agentic systems, tools are not auxiliary features; they are the primary means by which the agent interacts with the world. This mirrors the action space in reinforcement learning, where the expressiveness and safety of available actions strongly shape the learned policy.

Agentic systems are also inherently iterative. Rarely does the first action succeed. Instead, the system relies on feedback—tool outputs, errors, partial results—to update its internal state and make a better decision at the next step. This feedback loop is essential for robustness and aligns closely with the trial-and-error dynamics studied in reinforcement learning.

Finally, uncertainty and stochasticity are unavoidable. Language models are probabilistic, and identical inputs may produce different outputs. As a result, reliability emerges not from determinism, but from system-level design: validation, structured outputs, constrained tool interfaces, retries, and well-defined stopping conditions.

#### A simplified definition: “Agent = LLM + tools”

For the purposes of this book, we adopt a deliberately pragmatic definition:

**Agent = LLM + tools (executed in a loop).**

This definition intentionally omits many refinements—explicit memory modules, planners, critics, reward models, or hierarchical policies—not because they are unimportant, but because they can be understood as extensions of this core pattern. If a language model can decide which tool to call next, observe the result, and repeat until a goal is met, the system already behaves like an agent in the classical sense.

A minimal agent loop looks like this:

```python
def run_agent(user_input: str, tools: dict) -> str:
    messages = [
        {"role": "system", "content": "Solve the task using tools when appropriate."},
        {"role": "user", "content": user_input},
    ]

    while True:
        response = llm_chat(messages=messages, tools=tool_schemas(tools))

        if response["type"] == "final":
            return response["content"]

        tool_name = response["name"]
        tool_args = response["args"]
        result = tools[tool_name](**tool_args)

        messages.append(response)
        messages.append({
            "role": "tool",
            "name": tool_name,
            "content": serialize(result),
        })
```

Conceptually, this loop is no different from an agent interacting with an environment step by step. The language model plays the role of the policy, the tools define the action space, and the message history serves as a lightweight state representation.

#### Our approach: simplicity over taxonomy

There is an understandable temptation to draw sharp boundaries between workflows, assistants, planners, autonomous agents, and multi-agent systems. While these distinctions can be useful analytically, they often obscure the engineering reality.

In this book, we take a deliberately simple stance. If a system repeatedly observes, decides, acts, and incorporates feedback—using a language model and tools—it is agentic enough to matter. This perspective aligns naturally with the reinforcement learning view of agents as sequential decision-makers, while remaining practical for engineers building real systems today.

