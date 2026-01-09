## Chain-of-Thought (CoT)

**Chain-of-Thought** is a reasoning pattern in which a model explicitly decomposes a problem into a sequence of intermediate reasoning steps before producing a final answer.

### Historical perspective

The idea behind Chain-of-Thought did not emerge in isolation; it is rooted in long-standing research on human problem solving, symbolic reasoning, and step-by-step explanation in cognitive science and artificial intelligence. Early expert systems and logic-based AI relied on explicit inference chains, but these systems required hand-crafted rules and did not generalize well. In parallel, educational psychology emphasized the importance of “showing your work” as a way to improve reasoning accuracy and learning outcomes.

In modern machine learning, the immediate precursors to Chain-of-Thought appeared in work on prompting large language models around 2020–2021, when researchers observed that models often failed at multi-step reasoning despite strong performance on surface-level tasks. The key insight, formalized in 2022, was that large language models could be induced to perform significantly better on arithmetic, symbolic, and commonsense reasoning tasks if they were prompted to generate intermediate reasoning steps. This marked a shift from treating models as black-box answer generators toward viewing them as systems capable of producing structured reasoning traces when guided appropriately.

### The pattern explained

At its core, Chain-of-Thought is about **externalizing intermediate reasoning**. Instead of asking a model to jump directly from a question to an answer, the prompt encourages or requires the model to articulate the steps that connect the two. These steps may include decomposing the problem, applying rules or heuristics, performing intermediate calculations, or evaluating partial conclusions.

In practice, the pattern works by conditioning the model to follow a reasoning trajectory. This can be achieved in several ways: by including exemplars that show step-by-step reasoning, by explicitly instructing the model to “think step by step,” or by structuring the task so that intermediate outputs are required before the final response. Regardless of the mechanism, the effect is the same: the model allocates part of its generation capacity to reasoning, rather than compressing all inference into a single opaque prediction.

From an agentic systems perspective, Chain-of-Thought serves as a **foundational reasoning primitive**. It enables decomposition of complex tasks into manageable subproblems, supports inspection and debugging of model behavior, and provides a substrate for more advanced patterns such as self-reflection and tree-based exploration. CoT is especially valuable in tasks that require arithmetic, logical consistency, planning, or constraint satisfaction, where single-step answers are brittle or unreliable.

However, Chain-of-Thought also introduces trade-offs. Generating explicit reasoning increases token usage and latency, and the reasoning trace itself may contain errors even when the final answer is correct—or vice versa. As a result, CoT is best understood not as a guarantee of correctness, but as a tool that increases the *probability* of correct reasoning and improves transparency. Later agentic patterns often build on CoT while selectively summarizing, pruning, or validating reasoning steps to manage these costs.

### References

1. Wei, J., et al. *Chain-of-Thought Prompting Elicits Reasoning in Large Language Models*. NeurIPS, 2022. [https://arxiv.org/abs/2201.11903](https://arxiv.org/abs/2201.11903)
2. Kojima, T., et al. *Large Language Models are Zero-Shot Reasoners*. NeurIPS, 2022. [https://arxiv.org/abs/2205.11916](https://arxiv.org/abs/2205.11916)
3. Nye, M., et al. *Show Your Work: Scratchpads for Intermediate Computation with Language Models*. arXiv preprint, 2021. [https://arxiv.org/abs/2112.00114](https://arxiv.org/abs/2112.00114)
4. Cobbe, K., et al. *Training Verifiers to Solve Math Word Problems*. arXiv preprint, 2021. [https://arxiv.org/abs/2110.14168](https://arxiv.org/abs/2110.14168)
