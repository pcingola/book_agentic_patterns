## Planning and Decomposition

**Planning and decomposition** is the pattern by which an agent transforms a high-level goal into an ordered or structured set of smaller, executable sub-tasks, often reasoning explicitly about dependencies, constraints, and intermediate states.

At its core, planning and decomposition separates *what* an agent wants to achieve from *how* it will achieve it. The agent first reasons at a higher level of abstraction, identifying major steps or milestones, and only then descends into finer-grained actions. This separation helps manage complexity, reduces cognitive load on the model, and creates opportunities for verification, re-planning, or delegation.

In practical agentic systems, the pattern usually unfolds in three conceptual phases. First, the agent interprets the goal and constructs a plan outline. This may be a linear sequence of steps, a tree of sub-goals, or a partial order with dependencies. Second, each step is decomposed into concrete actions that the agent can perform, such as calling tools, querying APIs, or generating artifacts. Third, the agent executes these actions, optionally revisiting the plan when new information or failures arise.

Unlike pure Chain-of-Thought reasoning, which often mixes planning and execution in a single stream, explicit planning and decomposition externalizes structure. The plan can be inspected, modified, validated, or handed off to another agent. This makes the pattern particularly suitable for longer-horizon tasks, multi-tool workflows, and collaborative or multi-agent settings.

Decomposition can be shallow or deep. Simple tasks may require only a short checklist, while complex objectives benefit from hierarchical decomposition, where sub-tasks are themselves planned and broken down recursively. In advanced agents, planning is not a one-shot activity but an ongoing loop: execution produces feedback, feedback triggers plan revision, and the agent adapts its decomposition accordingly. This connects planning tightly with other core patterns such as ReAct, self-reflection, and verification.

Importantly, modern LLM-based planning is often *approximate* rather than optimal. The goal is not to compute the best plan in a formal sense, but to produce a plausible, coherent structure that guides action effectively. This trade-off reflects a shift from correctness-by-construction to usefulness-under-uncertainty, which is characteristic of contemporary agentic systems.

