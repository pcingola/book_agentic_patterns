## Tree of Thought (ToT)

**Tree of Thought** is a reasoning pattern in which a model explicitly explores multiple alternative reasoning paths in a branching structure, evaluates intermediate states, and selectively expands the most promising ones toward a final solution.

At its core, Tree of Thought reframes reasoning as a search problem. Instead of asking the model to produce one coherent chain of reasoning from start to finish, the system asks it to generate multiple partial reasoning steps, each representing a possible “state” in the problem-solving process. These states are organized into a tree structure, where each node corresponds to an intermediate thought and edges represent possible next steps.

The process typically unfolds in iterative phases. First, the model generates a set of candidate thoughts from the current state. These thoughts are not final answers but partial solutions, hypotheses, or next-step ideas. Next, each candidate is evaluated. Evaluation can be performed by the model itself (for example, by scoring plausibility or progress), by heuristics defined by the system designer, or by an external verifier. Based on these evaluations, only the most promising branches are expanded further, while weaker ones are pruned.

This branching-and-pruning cycle continues until a stopping condition is met, such as reaching a solution state, exhausting a search budget, or determining that no branch is improving. The final answer is then derived from the best-performing path in the tree. Importantly, the tree does not need to be exhaustive; even shallow branching can significantly improve robustness by allowing recovery from early mistakes.

From an agentic systems perspective, Tree of Thought is especially valuable because it introduces explicit control over exploration and deliberation. The agent can trade off computation for solution quality by adjusting branching width, depth, or evaluation strictness. Compared to Chain-of-Thought, which is implicitly linear and opaque to external control, Tree of Thought exposes intermediate reasoning states as first-class objects that can be inspected, compared, and managed.

