## Self-Reflection

Self-reflection is a reasoning pattern in which an agent explicitly inspects, critiques, and revises its own intermediate reasoning or outputs in order to improve correctness, robustness, or alignment with a goal.

### Historical perspective

The idea of self-reflection in artificial intelligence has deep roots in metacognition research from cognitive science, where human problem solvers were studied as agents capable of monitoring and correcting their own reasoning. In classical AI, related ideas appeared in work on planning systems with execution monitoring, belief revision, and meta-level control, but these mechanisms were usually rule-based and external to the reasoning process itself.

In the context of large language models, self-reflection emerged more clearly in the early 2020s, as researchers observed that models could improve their own answers when prompted to explain, critique, or reconsider them. Early Chain-of-Thought work showed that exposing intermediate reasoning steps increased accuracy, which naturally led to the question of whether those steps could be evaluated and refined. Papers such as *Self-Refine* and *Reflexion* formalized this intuition by introducing explicit loops in which a model generates an answer, reflects on its quality or errors, and then produces a revised solution. This line of work was influenced by reinforcement learning, program synthesis with iterative repair, and earlier notions of deliberation in problem solving.

### The self-reflection pattern

At its core, self-reflection introduces a second-order reasoning step: the agent reasons not only about the task, but also about its own reasoning process or output. Unlike Chain-of-Thought, which focuses on making reasoning explicit, self-reflection adds evaluation and correction as first-class operations.

A typical self-reflection cycle unfolds in several stages. First, the agent produces an initial solution using its standard reasoning process. This solution is then treated as an object of analysis. The agent is prompted, either implicitly or explicitly, to identify flaws, inconsistencies, missing assumptions, or mismatches with the task requirements. Based on this critique, the agent generates a revised solution that incorporates the identified improvements. This cycle may run once or multiple times, depending on the system design.

What distinguishes self-reflection from simple re-prompting is that the critique is grounded in the agent’s own prior output and often structured around explicit criteria, such as correctness, logical consistency, completeness, or adherence to constraints. In more advanced agentic systems, the reflective step can be guided by external signals, including unit tests, environment feedback, or memory of past failures, making reflection both contextual and cumulative.

In agent architectures, self-reflection often appears as a control-loop pattern layered on top of other reasoning strategies. For example, an agent may use Chain-of-Thought to generate a solution, Tree of Thought to explore alternatives, and then self-reflection to select or refine the best candidate. In long-running agents, reflections can be persisted as lessons or heuristics, allowing future behavior to improve without retraining the underlying model. This makes self-reflection a key mechanism for adaptivity and learning-like behavior in otherwise static models.

### References

1. Jason Wei et al. *Chain-of-Thought Prompting Elicits Reasoning in Large Language Models*. NeurIPS, 2022.
2. Shunyu Yao et al. *Self-Refine: Iterative Refinement with Self-Feedback*. arXiv, 2023.
3. Noah Shinn et al. *Reflexion: Language Agents with Verbal Reinforcement Learning*. arXiv, 2023.
4. Edward J. Hu et al. *Toolformer: Language Models Can Teach Themselves to Use Tools*. arXiv, 2023.
