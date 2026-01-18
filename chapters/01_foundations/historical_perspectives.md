## Historical Perspectives

This section consolidates the historical context underlying the foundational concepts of agentic systems: agents as sequential decision-makers, the probabilistic nature of language models, modular system design, and the evolution of AI methodologies.

### From classical agents to LLM-based systems

The notion of an *agent* predates modern language models by several decades. In classical AI, an agent is defined as an entity that perceives its environment and acts upon it, with the objective of maximizing some notion of performance. This framing was formalized most clearly in reinforcement learning, where the agent-environment interaction loop became the dominant abstraction.

Reinforcement learning formalizes an agent as a *sequential decision-maker*, and Bellman's equations provide the mathematical backbone of this idea. At their core, they express a simple but powerful principle: **the value of a decision depends on the value of the decisions that follow it**.

In a Markov Decision Process (MDP), an agent interacts with an environment characterized by states (s), actions (a), transition dynamics, and rewards. The *state-value function* ($V^\pi(s)$) under a policy ($\pi$) is defined as the expected cumulative reward starting from state (s). Bellman showed that this value can be written recursively:

$$
V^\pi(s) = \mathbb{E}_{a \sim \pi,, s'} \left[ r(s,a) + \gamma V^\pi(s') \right]
$$

This equation says that the value of the current state is the immediate reward plus the discounted value of the next state. The *optimal* value function satisfies the Bellman optimality equation:

$$
V^*(s) = \max_a \mathbb{E}_{s'} \left[ r(s,a) + \gamma V^*(s') \right]
$$

Conceptually, this is the agent loop in its purest form: at each step, choose the action that leads to the best expected future outcome, assuming optimal behavior thereafter. Richard Bellman's key contribution was recognizing that long-horizon decision-making can be decomposed into local decisions evaluated recursively.

Modern agentic systems do **not** solve Bellman equations explicitly. There is no value table, no learned reward model, and often no explicit notion of optimality. However, the *structure* remains the same. Each tool call corresponds to an action, each tool result is an observation of the next state, and the language model implicitly approximates a policy that reasons about future consequences ("If I query the database first, I can answer more accurately later").

Seen through this lens, LLM-based agents are best understood not as a departure from classical agent theory, but as a practical approximation of it-replacing explicit value functions with learned heuristics expressed in natural language, while preserving the recursive, step-by-step decision structure that Bellman formalized decades ago.

Later work in the 1990s on intelligent and multi-agent systems emphasized properties such as autonomy, reactivity, and proactiveness, as well as the ability of agents to interact with one another. While these systems were often symbolic or rule-based, the conceptual loop-observe, decide, act, learn-remained the same.

What changed with large language models is not the agent abstraction itself, but the mechanism used to approximate the policy. Instead of learning a value function or policy explicitly via reward signals, modern agentic systems use language models as powerful, general-purpose policy approximators that can reason over unstructured inputs and decide which actions (tools) to take next.

### From probabilistic language models to modern decoding

Language modeling has been probabilistic from the start: the core object is a probability distribution over sequences, not a single "correct" next token. Early information theory formalized the idea of modeling sources statistically, which later became the conceptual backbone of language modeling. ([ESSRL][1])

Neural language models made this explicit by learning a parameterized distribution over next tokens, and modern LLMs are essentially extremely large versions of that idea. ([Journal of Machine Learning Research][2]) What changed in practice is that, as models became strong generators, *decoding* became a first-class engineering decision. Deterministic decoding (greedy/beam) tends to be repeatable but can degrade quality (repetition, blandness), while stochastic decoding (temperature, top-k/top-p) trades determinism for diversity and sometimes robustness. Nucleus sampling is a canonical example of decoding research motivated by these practical failures. ([arXiv][3])

### From software modules to tool-using agents

Modularity predates "agents" by decades. In classic software engineering, information hiding and stable interfaces were formalized as the core mechanism for building systems that can change without collapsing under their own complexity. The canonical argument is that you do *not* modularize by "steps in the processing," but by design decisions likely to change-so changes are localized behind module boundaries. ([ACM Digital Library][11])

As systems grew, the same pressure pushed modularity "out of process" into services: independently deployable components with explicit network contracts. This trajectory is often summarized as monolith -> modules/packages -> services/SOA -> microservices, with the key idea remaining constant: smaller components, clear interfaces, and ownership boundaries. ([martinfowler.com][12])

In LLM systems, modularity reappeared in a new form around 2022-2023: language models began to *route* to external tools and specialized components rather than "do everything in weights." Neuro-symbolic and tool-augmented architectures (e.g., MRKL) made modular routing explicit, while ReAct showed the practical value of interleaving reasoning with actions (tool calls) during execution. ([arXiv][3]) Toolformer then pushed toward models that can learn to decide *when* to call tools. ([arXiv][4])

### From hand-built intelligence to scalable methods

A repeating pattern in AI history is that approaches which "bake in" human knowledge and reasoning tricks often deliver quick wins, but are eventually outpaced by more general methods that can absorb more compute and data. Sutton's *The Bitter Lesson* distilled this from decades of results across search and learning: progress tends to come from methods that scale (and from the discipline to keep systems simple enough to scale), even when the "hand-designed" approach feels more insightful in the moment. ([UT Austin Computer Science][26])

Modern LLM agents reintroduce an old temptation in a new form: over-fitting behavior through elaborate prompting, brittle heuristics, or highly bespoke orchestration. The best current practice is to resist that temptation by investing in (1) strong interfaces (tools, schemas, contracts), (2) evaluation-driven iteration, and (3) designs that keep the model doing what it's good at (flexible reasoning under uncertainty) while pushing deterministic work into code.

[1]: https://www.essrl.wustl.edu/~jao/itrg/shannon.pdf
[2]: https://www.jmlr.org/papers/volume3/bengio03a/bengio03a.pdf
[3]: https://arxiv.org/abs/1904.09751
[4]: https://arxiv.org/abs/2302.04761
[11]: https://dl.acm.org/doi/10.1145/361598.361623
[12]: https://martinfowler.com/articles/microservices.html
[26]: https://www.cs.utexas.edu/~eunsol/courses/data/bitter_lesson.pdf
