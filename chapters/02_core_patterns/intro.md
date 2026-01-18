## Introduction

This chapter introduces a set of foundational reasoning patterns that recur across modern agentic systems. These patterns describe how language models structure reasoning, manage complexity, evaluate intermediate results, and interact with their environment. Although they are often presented as distinct techniques, they form a coherent progression from simple prompt-based behavior to structured, iterative, and self-correcting agency.

At the base of this progression are **zero-shot and few-shot reasoning**. These approaches rely entirely on prompting, using instructions and examples to guide behavior without altering the model itself. They demonstrate a central idea of agentic design: reasoning can be shaped at the interface level, and sophisticated behavior can emerge from careful framing alone.

**Chain-of-Thought (CoT)** builds on this foundation by making intermediate reasoning steps explicit. Instead of producing only an answer, the model generates a sequence of thoughts that lead to it. This explicit representation improves performance on multi-step problems and transforms reasoning into an object that can be inspected, guided, or reused. In practice, Chain-of-Thought often gives rise to implicit **planning and decomposition**, as complex problems are broken into smaller steps or subgoals within the reasoning trace.

For tasks that benefit from exploring alternatives rather than following a single linear path, **Tree of Thought** extends Chain-of-Thought into a search process. Multiple reasoning branches are generated, evaluated, and selectively expanded, introducing explicit comparison and pruning. This pattern connects language-model reasoning to classical ideas from planning and search, while remaining fully expressed in natural language.

Reasoning becomes agentic when it is coupled with action. **ReAct** (Reason + Act) interleaves internal reasoning with external actions such as tool calls or environment interactions. Each action produces observations that feed back into subsequent reasoning, creating a closed loop between thought and world. This pattern shifts reasoning from a static, prompt-bounded process to an ongoing interaction with an external state.

As reasoning chains grow longer and more complex, the risk of compounding errors increases. **Self-reflection** addresses this by enabling the model to revisit and revise its own outputs, whether they are answers, plans, or action sequences. Closely related is the pattern of **verification and critique**, where outputs are explicitly evaluated against correctness criteria, constraints, or goals. While reflection emphasizes self-improvement, verification emphasizes judgment; together, they provide the basis for robustness and reliability.

Taken together, these patterns are not isolated techniques but composable building blocks. Zero-shot and few-shot prompting establish the baseline, Chain-of-Thought makes reasoning explicit, planning and decomposition structure longer horizons, Tree of Thought introduces search, ReAct grounds reasoning in action, and reflection and verification provide corrective feedback. The remainder of this chapter examines each pattern in detail, tracing its origins and showing how it is used in practical agentic systems.

### References

1. Brown et al. *Language Models are Few-Shot Learners*. NeurIPS, 2020.
2. Wei et al. *Chain-of-Thought Prompting Elicits Reasoning in Large Language Models*. NeurIPS, 2022.
3. Yao et al. *Tree of Thoughts: Deliberate Problem Solving with Large Language Models*. arXiv, 2023.
4. Yao et al. *ReAct: Synergizing Reasoning and Acting in Language Models*. ICLR, 2023.
5. Shinn et al. *Reflexion: Language Agents with Verbal Reinforcement Learning*. NeurIPS, 2023.
