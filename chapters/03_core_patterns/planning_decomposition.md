## Planning and Decomposition

**Planning and decomposition** is the pattern by which an agent transforms a high-level goal into an ordered or structured set of smaller, executable sub-tasks, often reasoning explicitly about dependencies, constraints, and intermediate states.

### Historical perspective

The roots of planning and decomposition long predate modern language models. In classical artificial intelligence, planning emerged in the 1960s and 1970s through symbolic approaches such as STRIPS and later hierarchical task network (HTN) planning. These systems treated intelligence as the ability to search through a space of actions using explicit world models, operators, preconditions, and effects. Decomposition was formalized as the recursive breakdown of abstract tasks into primitive actions that could be executed in the environment.

In the 2000s and 2010s, automated planning research continued to evolve, but large-scale adoption was limited by brittleness, modeling cost, and the gap between symbolic plans and real-world uncertainty. With the rise of large language models, planning and decomposition reappeared in a different form: rather than relying on hand-specified operators, models could infer task structure from natural language and decompose problems implicitly or explicitly at inference time. Early prompting techniques such as “let’s think step by step” and later structured planning prompts demonstrated that decomposition itself could significantly improve performance, even without explicit execution or search.

More recent work reframed planning as an internal reasoning process of the model, sometimes externalized as text plans, sometimes combined with tool use, execution, and feedback. This reconnected modern LLM-based agents with classical planning ideas, while relaxing the requirement for formal world models.

### The pattern in detail

At its core, planning and decomposition separates *what* an agent wants to achieve from *how* it will achieve it. The agent first reasons at a higher level of abstraction, identifying major steps or milestones, and only then descends into finer-grained actions. This separation helps manage complexity, reduces cognitive load on the model, and creates opportunities for verification, re-planning, or delegation.

In practical agentic systems, the pattern usually unfolds in three conceptual phases. First, the agent interprets the goal and constructs a plan outline. This may be a linear sequence of steps, a tree of sub-goals, or a partial order with dependencies. Second, each step is decomposed into concrete actions that the agent can perform, such as calling tools, querying APIs, or generating artifacts. Third, the agent executes these actions, optionally revisiting the plan when new information or failures arise.

Unlike pure Chain-of-Thought reasoning, which often mixes planning and execution in a single stream, explicit planning and decomposition externalizes structure. The plan can be inspected, modified, validated, or handed off to another agent. This makes the pattern particularly suitable for longer-horizon tasks, multi-tool workflows, and collaborative or multi-agent settings.

Decomposition can be shallow or deep. Simple tasks may require only a short checklist, while complex objectives benefit from hierarchical decomposition, where sub-tasks are themselves planned and broken down recursively. In advanced agents, planning is not a one-shot activity but an ongoing loop: execution produces feedback, feedback triggers plan revision, and the agent adapts its decomposition accordingly. This connects planning tightly with other core patterns such as ReAct, self-reflection, and verification.

Importantly, modern LLM-based planning is often *approximate* rather than optimal. The goal is not to compute the best plan in a formal sense, but to produce a plausible, coherent structure that guides action effectively. This trade-off reflects a shift from correctness-by-construction to usefulness-under-uncertainty, which is characteristic of contemporary agentic systems.

### References

1. Fikes, R., Nilsson, N. *STRIPS: A New Approach to the Application of Theorem Proving to Problem Solving*. Artificial Intelligence, 1971.
2. Sacerdoti, E. *Planning in a Hierarchy of Abstraction Spaces*. Artificial Intelligence, 1974.
3. Nau, D. et al. *Hierarchical Task Network Planning*. AI Magazine, 2003.
4. Wei, J. et al. *Chain-of-Thought Prompting Elicits Reasoning in Large Language Models*. NeurIPS, 2022.
5. Yao, S. et al. *ReAct: Synergizing Reasoning and Acting in Language Models*. ICLR, 2023.
6. Zhou, D. et al. *Least-to-Most Prompting Enables Complex Reasoning in Large Language Models*. ICLR, 2023.
