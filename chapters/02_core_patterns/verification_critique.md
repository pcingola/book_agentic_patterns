## Verification / Critique

**Verification / critique** is the pattern in which a model explicitly evaluates, checks, and challenges its own outputs (or intermediate reasoning) to detect errors, inconsistencies, or unmet constraints before producing a final answer.

### Historical perspective

The roots of verification and critique in AI predate modern large language models. In classical AI and expert systems, verification appeared as rule checking, constraint satisfaction, and formal verification, where candidate solutions were validated against explicit logical or mathematical constraints. Planning systems routinely separated *generation* from *validation*, with search producing candidates and a verifier rejecting invalid plans.

In the context of neural language models, early signals emerged alongside Chain-of-Thought prompting in the early 2020s, when researchers observed that models could be prompted not only to reason but also to *review* or *criticize* reasoning steps. Work on self-consistency (sampling multiple reasoning paths and selecting consistent answers) and reflection-based prompting demonstrated that explicit critique phases could substantially improve reliability. Subsequent research on “self-reflection,” “self-critique,” and “verifier models” formalized this separation between a generator and a critic, often using either the same model in different roles or distinct models specialized for evaluation. These ideas were further reinforced by alignment research, where critique-like mechanisms were used to identify harmful, incorrect, or low-quality outputs.

### The pattern in detail

At its core, the verification / critique pattern introduces a deliberate *evaluation phase* into the agent’s reasoning loop. Rather than treating the first generated answer as final, the agent subjects it to one or more checks that aim to answer a simple question: *Is this actually correct, complete, and acceptable under the given constraints?*

Conceptually, the pattern can be decomposed into three roles:

1. **Generation** – The agent produces an initial solution, plan, or explanation using its standard reasoning capabilities.
2. **Critique** – The agent (or a separate critic) inspects that output, looking for errors, missing steps, logical gaps, violated constraints, or misalignment with the task requirements.
3. **Revision or acceptance** – Based on the critique, the agent either revises the output or accepts it as sufficiently valid.

What distinguishes verification / critique from simple re-prompting is that the evaluation criteria are made explicit. The critique step may focus on factual correctness, internal logical consistency, adherence to instructions, safety constraints, or domain-specific rules. In agentic systems, this often appears as a loop: generate → critique → revise → critique again, until a stopping condition is met.

This pattern is especially powerful when combined with other core patterns. With Chain-of-Thought or Tree of Thought, critique can operate on intermediate reasoning paths, pruning flawed branches before they propagate. With planning and decomposition, critique can validate subplans independently, reducing cascading failures. In tool-using agents, verification may include external checks, such as re-running calculations, validating API responses, or cross-checking facts against trusted sources.

Importantly, verification / critique does not guarantee correctness; rather, it increases robustness by making error detection an explicit objective of the system. In practice, even lightweight critique prompts—such as asking the model to list potential mistakes in its own answer—can yield measurable improvements in accuracy and reliability.

### References

1. Wei, J. et al. *Chain-of-Thought Prompting Elicits Reasoning in Large Language Models*. NeurIPS, 2022.
2. Wang, X. et al. *Self-Consistency Improves Chain of Thought Reasoning in Language Models*. arXiv, 2022.
3. Madaan, A. et al. *Self-Refine: Iterative Refinement with Self-Feedback*. arXiv, 2023.
4. Shinn, N., & Labash, B. *Reflexion: Language Agents with Verbal Reinforcement Learning*. arXiv, 2023.
5. Saunders, W. et al. *Self-Critique and the Limits of Model Introspection*. arXiv, 2022.
