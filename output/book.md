# Chapter 1: Core Agentic Patterns

# Chapter 3: Core Agentic Patterns

## Introduction

This chapter introduces a set of foundational reasoning patterns that recur across modern agentic systems. These patterns describe how language models structure reasoning, manage complexity, evaluate intermediate results, and interact with their environment. Although they are often presented as distinct techniques, they form a coherent progression from simple prompt-based behavior to structured, iterative, and self-correcting agency.

At the base of this progression are **zero-shot and few-shot reasoning**. These approaches rely entirely on prompting, using instructions and examples to guide behavior without altering the model itself. They demonstrate a central idea of agentic design: reasoning can be shaped at the interface level, and sophisticated behavior can emerge from careful framing alone.

**Chain-of-Thought (CoT)** builds on this foundation by making intermediate reasoning steps explicit. Instead of producing only an answer, the model generates a sequence of thoughts that lead to it. This explicit representation improves performance on multi-step problems and transforms reasoning into an object that can be inspected, guided, or reused. In practice, Chain-of-Thought often gives rise to implicit **planning and decomposition**, as complex problems are broken into smaller steps or subgoals within the reasoning trace.

For tasks that benefit from exploring alternatives rather than following a single linear path, **Tree of Thought** extends Chain-of-Thought into a search process. Multiple reasoning branches are generated, evaluated, and selectively expanded, introducing explicit comparison and pruning. This pattern connects language-model reasoning to classical ideas from planning and search, while remaining fully expressed in natural language.

Reasoning becomes agentic when it is coupled with action. **REACT** (Reason + Act) interleaves internal reasoning with external actions such as tool calls or environment interactions. Each action produces observations that feed back into subsequent reasoning, creating a closed loop between thought and world. This pattern shifts reasoning from a static, prompt-bounded process to an ongoing interaction with an external state.

As reasoning chains grow longer and more complex, the risk of compounding errors increases. **Self-reflection** addresses this by enabling the model to revisit and revise its own outputs, whether they are answers, plans, or action sequences. Closely related is the pattern of **verification and critique**, where outputs are explicitly evaluated against correctness criteria, constraints, or goals. While reflection emphasizes self-improvement, verification emphasizes judgment; together, they provide the basis for robustness and reliability.

Taken together, these patterns are not isolated techniques but composable building blocks. Zero-shot and few-shot prompting establish the baseline, Chain-of-Thought makes reasoning explicit, planning and decomposition structure longer horizons, Tree of Thought introduces search, REACT grounds reasoning in action, and reflection and verification provide corrective feedback. The remainder of this chapter examines each pattern in detail, tracing its origins and showing how it is used in practical agentic systems.

### References

1. Brown et al. *Language Models are Few-Shot Learners*. NeurIPS, 2020.
2. Wei et al. *Chain-of-Thought Prompting Elicits Reasoning in Large Language Models*. NeurIPS, 2022.
3. Yao et al. *Tree of Thoughts: Deliberate Problem Solving with Large Language Models*. arXiv, 2023.
4. Yao et al. *ReAct: Synergizing Reasoning and Acting in Language Models*. ICLR, 2023.
5. Shinn et al. *Reflexion: Language Agents with Verbal Reinforcement Learning*. NeurIPS, 2023.


## Zero-shot / Few-shot Reasoning

Zero-shot and few-shot reasoning describe a model’s ability to perform a task from a natural language description alone, or with only a small number of examples, without any task-specific training or fine-tuning.

The roots of zero-shot and few-shot reasoning lie in transfer learning and representation learning research from the late 2000s and early 2010s. Early work in computer vision and natural language processing explored *zero-shot learning* as a way to classify or act on categories never seen during training, typically by leveraging semantic embeddings or attribute descriptions. In NLP, this line of research was closely tied to distributed word representations and the idea that semantic structure learned from large corpora could generalize beyond explicit supervision.

A decisive shift occurred with the emergence of large pre-trained language models. The introduction of models such as GPT-2 and later GPT-3 demonstrated that scaling model size and training data led to *in-context learning*: models could infer the task purely from the prompt. The GPT-3 paper formalized the distinction between zero-shot, one-shot, and few-shot prompting, showing that performance often improved simply by adding a handful of examples to the input, without updating model parameters. This reframed few-shot learning from a training paradigm into a prompting paradigm, where examples are part of the input rather than the training data.

Subsequent research connected these behaviors to meta-learning, implicit task induction, and probabilistic sequence modeling. Rather than explicitly learning a new task, the model appears to infer a latent task description from the prompt and condition its generation accordingly. This insight strongly influenced how modern agentic systems are designed, as zero-shot and few-shot reasoning enable flexible behavior without rigid task schemas.

At its core, zero-shot reasoning relies on the model’s ability to interpret instructions expressed in natural language and map them to previously learned patterns. The model does not receive any explicit examples of input–output pairs; instead, it must infer what is being asked from descriptive cues such as task definitions, constraints, and desired output formats. This makes zero-shot reasoning highly dependent on prompt clarity and on the breadth of knowledge encoded during pre-training.

Few-shot reasoning extends this idea by embedding a small number of demonstrations directly into the prompt. These demonstrations serve as implicit specifications of the task. Rather than being rules in a formal sense, they act as contextual anchors that reduce ambiguity. The model infers a pattern from these examples and continues it when presented with a new input. Importantly, the model parameters remain fixed; adaptation happens entirely through conditioning on the prompt.

In agentic systems, zero-shot and few-shot reasoning are foundational because they enable rapid task acquisition. An agent can be instructed to perform a novel operation, adopt a new output schema, or follow a new decision heuristic simply by modifying its prompt. Few-shot examples are often used to stabilize behavior, enforce consistency, or encode domain-specific conventions without retraining. This makes such patterns especially suitable for dynamic environments where tasks change frequently or cannot be fully specified in advance.

There are, however, clear limitations. Zero-shot prompts can be brittle when tasks are underspecified, and few-shot prompts can be sensitive to example ordering, phrasing, and length. As tasks grow more complex, these patterns are often combined with other reasoning structures—such as Chain-of-Thought or ReAct—to provide additional scaffolding. Nevertheless, zero-shot and few-shot reasoning remain the entry point for most agent behaviors, defining the minimal mechanism by which a model is instructed to act.

### References

1. Palatucci, M., Pomerleau, D., Hinton, G., & Mitchell, T. *Zero-shot Learning with Semantic Output Codes*. NIPS, 2009.
2. Mikolov, T., Chen, K., Corrado, G., & Dean, J. *Efficient Estimation of Word Representations in Vector Space*. arXiv, 2013.
3. Radford, A., Wu, J., Child, R., et al. *Language Models are Unsupervised Multitask Learners*. OpenAI, 2019.
4. Brown, T. B., Mann, B., Ryder, N., et al. *Language Models are Few-Shot Learners*. NeurIPS, 2020.
5. Xie, S., Ma, X., Wang, Y., et al. *An Explanation of In-Context Learning as Implicit Bayesian Inference*. ICLR, 2022.


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


## Tree of Thought (ToT)

**Tree of Thought** is a reasoning pattern in which a model explicitly explores multiple alternative reasoning paths in a branching structure, evaluates intermediate states, and selectively expands the most promising ones toward a final solution.

### Historical perspective

The Tree of Thought pattern emerged in the early 2020s as researchers began to probe the limits of linear prompting strategies such as zero-shot and Chain-of-Thought reasoning. While Chain-of-Thought demonstrated that large language models could benefit from articulating intermediate steps, it also revealed a structural limitation: reasoning was still constrained to a single trajectory. If the model committed early to a poor path, later steps often could not recover.

This motivated research into more deliberate and search-like forms of reasoning, drawing inspiration from classical AI techniques such as tree search, planning, and heuristic evaluation. Around 2023, several papers formalized these ideas by treating language model reasoning as a process of state expansion and evaluation rather than a single sequence of tokens. The Tree of Thought framework crystallized this direction, combining language-model generation with explicit branching, scoring, and pruning mechanisms.

### Detailed explanation of the pattern

At its core, Tree of Thought reframes reasoning as a search problem. Instead of asking the model to produce one coherent chain of reasoning from start to finish, the system asks it to generate multiple partial reasoning steps, each representing a possible “state” in the problem-solving process. These states are organized into a tree structure, where each node corresponds to an intermediate thought and edges represent possible next steps.

The process typically unfolds in iterative phases. First, the model generates a set of candidate thoughts from the current state. These thoughts are not final answers but partial solutions, hypotheses, or next-step ideas. Next, each candidate is evaluated. Evaluation can be performed by the model itself (for example, by scoring plausibility or progress), by heuristics defined by the system designer, or by an external verifier. Based on these evaluations, only the most promising branches are expanded further, while weaker ones are pruned.

This branching-and-pruning cycle continues until a stopping condition is met, such as reaching a solution state, exhausting a search budget, or determining that no branch is improving. The final answer is then derived from the best-performing path in the tree. Importantly, the tree does not need to be exhaustive; even shallow branching can significantly improve robustness by allowing recovery from early mistakes.

From an agentic systems perspective, Tree of Thought is especially valuable because it introduces explicit control over exploration and deliberation. The agent can trade off computation for solution quality by adjusting branching width, depth, or evaluation strictness. Compared to Chain-of-Thought, which is implicitly linear and opaque to external control, Tree of Thought exposes intermediate reasoning states as first-class objects that can be inspected, compared, and managed.

### References

1. Yao, S., et al. *Tree of Thoughts: Deliberate Problem Solving with Large Language Models*. arXiv preprint, 2023. [https://arxiv.org/abs/2305.10601](https://arxiv.org/abs/2305.10601)
2. Wei, J., et al. *Chain-of-Thought Prompting Elicits Reasoning in Large Language Models*. NeurIPS, 2022.
3. Newell, A., Simon, H. A. *Human Problem Solving*. Prentice-Hall, 1972.
4. Russell, S., Norvig, P. *Artificial Intelligence: A Modern Approach*. Pearson, various editions.


## ReAct (Reason + Act)

ReAct is a prompting pattern where an LLM alternates *explicit reasoning steps* with *tool/environment actions*, using observations from those actions to steer the next reasoning step.

ReAct appears in the 2022 wave of “reasoning by prompting.” The immediate precursor is **Chain-of-Thought (CoT)** prompting (early 2022), which showed that giving exemplars with intermediate reasoning steps can unlock multi-step problem solving in large models. ([2]) But CoT on its own is “closed-book”: it improves decomposition and planning, yet still forces the model to *invent* facts and compute purely in-token—making it vulnerable to hallucination and compounding errors when external information is needed.

In parallel, multiple lines of research were converging on “LLMs as agents” that *act* via external interfaces. **WebGPT** (late 2021) trained a model to browse the web in a text environment, explicitly collecting citations during interaction. ([arXiv][3]) **MRKL systems** (mid 2022) articulated a modular neuro-symbolic architecture: keep the LLM as a language/coordination layer, and route specialized subproblems to tools/knowledge modules. ([arXiv][4]) Around the same time, grounding work like **Do As I Can, Not As I Say (SayCan)** explored selecting feasible actions via an affordance model while using an LLM for high-level planning. ([arXiv][5])

### Core ideas

**ReAct** (first posted Oct 2022; later published via ICLR venue) crystallized these threads into a simple, general prompt format: *interleave* reasoning traces with actions so that the model’s “thoughts” can request information or execute steps, then immediately incorporate the resulting observations into the next reasoning step. ([arXiv][1])

ReAct structures an agent’s trajectory as a repeating loop:

1. **Thought (Reasoning trace):** the model writes a brief internal/explicit rationale describing what it knows, what it needs, and what it will do next.
2. **Action (Tool/environment step):** the model emits a structured action (e.g., `Search[...]`, `Lookup[...]`, `Click[...]`, `UseCalculator[...]`, `TakeStep[...]`) that is executed by the system.
3. **Observation:** the system returns the tool result (snippet, retrieved fact, environment state, error), which is appended to the context.
4. Repeat until a **Final** response is produced.

What distinguishes ReAct from simpler tool-augmented prompting is the *granularity* of this interaction. Reasoning and acting are interleaved at every step, rather than separated into large phases. This reduces hallucination by encouraging the model to seek external information when needed, improves robustness by enabling mid-course correction, and yields trajectories that are interpretable as step-by-step decision processes.

A typical ReAct prompt provides 1–2 exemplars of full trajectories in a consistent schema, then a new task. For example (conceptually):

* `Thought: ...`
* `Action: Search[...]`
* `Observation: ...`
* `Thought: ...`
* `Action: Lookup[...]`
* `Observation: ...`
* `Thought: ...`
* `Final: ...`

From a system-design perspective, ReAct also reinforces a clean separation of concerns. The language model is responsible for proposing reasoning and actions, while the surrounding runtime is responsible for enforcing action schemas, executing tools, handling failures, and maintaining state. This separation makes ReAct a natural foundation for more complex agentic systems and later patterns built on top of it.

### References

* **ReAct: Synergizing Reasoning and Acting in Language Models** (Yao et al., 2022; ICLR venue) ([arXiv][1])
* **Chain-of-Thought Prompting Elicits Reasoning in Large Language Models** (Wei et al., 2022) ([arXiv][2])
* **WebGPT: Browser-assisted question-answering with human feedback** (Nakano et al., 2021) ([arXiv][3])
* **MRKL Systems: A modular, neuro-symbolic architecture…** (Karpas et al., 2022) ([arXiv][4])
* (Related “tool delegation” line) **Toolformer: Language Models Can Teach Themselves to Use Tools** (Schick et al., 2023) ([arXiv][6])

[1]: https://arxiv.org/abs/2210.03629?utm_source=chatgpt.com "ReAct: Synergizing Reasoning and Acting in Language Models"
[2]: https://arxiv.org/abs/2201.11903?utm_source=chatgpt.com "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models"
[3]: https://arxiv.org/abs/2112.09332?utm_source=chatgpt.com "WebGPT: Browser-assisted question-answering with human feedback"
[4]: https://arxiv.org/abs/2205.00445?utm_source=chatgpt.com "MRKL Systems: A modular, neuro-symbolic architecture that combines large language models, external knowledge sources and discrete reasoning"
[5]: https://arxiv.org/abs/2204.01691?utm_source=chatgpt.com "Do As I Can, Not As I Say: Grounding Language in Robotic ..."
[6]: https://arxiv.org/abs/2302.04761?utm_source=chatgpt.com "Language Models Can Teach Themselves to Use Tools"


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


## Human in the Loop

**Human-in-the-loop (HITL)** is the pattern where an agent deliberately pauses autonomous execution to request human input, validation, or authorization before proceeding with tool use or decision making.

### Historical perspective

The idea of keeping humans actively involved in automated decision systems predates modern AI by decades. Early work in control theory and human–computer interaction in the 1960s and 1970s already emphasized *human supervisory control*, where automated systems executed routine actions but escalated uncertain or high-risk situations to human operators. In machine learning, this evolved into *interactive learning* and *active learning*, where models selectively queried humans for labels when uncertainty was high.

In the 2010s, research on human-in-the-loop machine learning formalized these ideas around feedback loops, uncertainty estimation, and cost-aware querying. With the rise of large language models and agentic systems in the 2020s, HITL re-emerged as a practical necessity rather than a theoretical preference. Early autonomous agents demonstrated impressive capabilities but also highlighted failure modes related to hallucinations, unsafe actions, and irreversible side effects when tools had real-world impact. As a result, human-in-the-loop patterns became a core design principle for production-grade agents, especially in enterprise, safety-critical, and compliance-sensitive environments.

### The pattern in agentic systems

In agentic tool use, human-in-the-loop is not simply “asking the user a question.” It is a structured control point in the agent’s execution graph where autonomy is intentionally suspended. The agent externalizes its current state—intent, assumptions, planned actions, and proposed tool calls—and waits for a human signal to continue, modify, or abort execution.

At a high level, the pattern consists of three steps:

1. **Detection of a handoff condition**
   The agent decides that human involvement is required. This may be triggered by uncertainty, policy constraints, permission boundaries, or explicit rules such as “all write actions require approval.”

2. **State serialization and presentation**
   The agent produces a structured summary of what it intends to do, often including inputs, expected effects, and risks. This summary must be concise, inspectable, and understandable by a human.

3. **Resumption with human input**
   The human response is fed back into the agent as structured input, allowing the agent to continue, revise its plan, or terminate.

This makes HITL fundamentally different from conversational clarification. The human is not just another information source but an authority that can override, constrain, or authorize the agent’s actions.

### Typical use cases

Human-in-the-loop is most valuable when tool use has **irreversible or high-cost side effects**. Common examples include deploying code, modifying production data, sending external communications, or executing financial transactions. It is also essential when agents operate under **organizational or legal constraints**, where accountability must remain with a human decision maker.

Another important use case is **error recovery and ambiguity resolution**. When an agent detects conflicting signals, incomplete data, or low confidence in its own reasoning, escalating to a human is often cheaper and safer than attempting further autonomous reasoning.

### Human checkpoints as part of tool workflows

In practice, HITL is often implemented as a special kind of tool or workflow node that represents a human checkpoint. From the agent’s perspective, this looks similar to any other tool call, except that the response is asynchronous and externally provided.

A simplified illustrative snippet:

```python
# Pseudocode illustrating a human checkpoint
if action.requires_approval:
    approval = request_human_review(
        summary=action.plan_summary(),
        proposed_tool=action.tool_name,
        inputs=action.tool_inputs,
    )
    if not approval.approved:
        abort_execution(reason=approval.feedback)
```

The key idea is that the agent treats human feedback as structured data, not free-form chat. This allows the system to remain deterministic and auditable.

### Human-in-the-loop vs. autonomy levels

HITL should not be viewed as a binary choice between “fully manual” and “fully autonomous.” Instead, agentic systems typically define **levels of autonomy**, where human involvement varies by context:

* Read-only or advisory actions may run autonomously.
* Write actions may require post-hoc review.
* Destructive or externally visible actions may require pre-approval.

Designing these boundaries explicitly is part of tool permissioning and governance, not an afterthought.

### Design considerations

Effective human-in-the-loop systems share several characteristics. They minimize cognitive load by presenting only the information necessary for a decision. They preserve full execution state so that approval does not require recomputation or guesswork. Finally, they make escalation explicit and intentional, avoiding hidden or implicit human dependencies that are hard to reason about.

When implemented correctly, HITL does not slow agents down unnecessarily. Instead, it creates well-defined synchronization points between human judgment and machine execution, enabling safe scaling of agentic systems.

### References

1. Sheridan, T. B., & Verplank, W. L. *Human and Computer Control of Undersea Teleoperators*. MIT Man-Machine Systems Laboratory, 1978.
2. Settles, B. *Active Learning Literature Survey*. University of Wisconsin–Madison, 2010.
3. Amershi, S. et al. *Human-in-the-Loop Machine Learning*. ACM CHI, 2014.
4. Russell, S. *Human-Compatible Artificial Intelligence*. AI Magazine, 2019.
5. OpenAI. *Best Practices for Human-in-the-Loop AI Systems*. Technical blog and documentation, 2023.



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


## Tool Contracts and Schemas

Tool contracts and schemas define the precise, machine-verifiable interface through which a language model reasons about, invokes, composes, and recovers from interactions with external tools.

### Historical perspective

Early approaches to tool use in language systems relied on informal conventions. Models produced natural-language descriptions of intended actions, and downstream code attempted to infer meaning using heuristics or pattern matching. These systems were brittle, opaque, and difficult to debug, echoing long-standing limitations of natural-language interfaces.

Two research threads gradually converged to address these issues. Work on semantic parsing and program induction explored mapping language to executable structures with explicit meaning, while advances in typed data validation emphasized schemas and contracts as a foundation for reliability. With the emergence of large language models capable of reliably producing structured outputs, these ideas became operational. Around 2022–2023, agent systems began to replace textual “action descriptions” with structured tool calls validated against explicit schemas, enabling deterministic execution, retries, and composition. Tool use shifted from a prompting convention to an architectural pattern.

### Tools as explicit contracts

A tool is defined not by its implementation, but by its *contract*. This contract specifies the tool’s name, intent, inputs, outputs, and operational constraints. In Python-centric systems, contracts are naturally derived from function signatures, type annotations, and docstrings.

A minimal example illustrates the idea:

```python
class WeatherRequest(BaseModel):
    city: str
    unit: str  # "C" or "F"

class WeatherResponse(BaseModel):
    temperature: float
    unit: str

def get_weather(req: WeatherRequest) -> WeatherResponse:
    """Return the current temperature for a city."""
    ...
```

From this definition, the runtime derives a schema that is passed to the language model. The model never sees executable code—only the interface. This separation is critical: the model reasons about *capabilities*, not implementations.

### Structured output and tool calls

Once tool contracts are available, the model is constrained to produce structured output. Instead of emitting free-form text, it must either select a tool and provide arguments conforming to its schema, or emit a structured final result.

Conceptually, a tool call looks like:

```json
{ "name": "get_weather", "arguments": { "city": "Buenos Aires", "unit": "C" } }
```

Arguments are validated before execution. If validation fails, the error is returned to the model as structured feedback, allowing it to correct itself. Structured output thus replaces brittle parsing with explicit, enforceable contracts.

### The tool call loop

Tool use occurs inside a loop. The model emits a structured action, the framework validates and executes it, and the result is appended to the agent’s state before the model continues.

At a high level:

```python
while True:
    msg = model.generate(state)
    if msg.is_final:
        return msg
    result = execute_tool(msg)
    state.append(result)
```

This loop is the operational core of agentic systems. Contracts and schemas ensure that every transition—generation, execution, and state update—is well defined and inspectable.

### Explicit termination via final schemas

To avoid ambiguous stopping conditions, frameworks introduce an explicit final schema. Rather than replying with unconstrained text, the model must emit a structured object representing completion.

```python
class FinalResult(BaseModel):
    answer: str
```

Termination is therefore a validated action, not an implicit convention. This guarantees that every agent run ends in a well-typed result, simplifying downstream processing, logging, and evaluation.

### Retries as part of the contract

Retries are not an implementation detail; they are part of the tool contract. A tool’s schema and documentation can communicate whether retries are safe, under what conditions they should occur, and which inputs must remain stable.

A retry-aware contract might include an explicit idempotency key:

```python
class PaymentRequest(BaseModel):
    amount_cents: int
    idempotency_key: str
```

When a tool fails, the failure is returned as structured data rather than an exception. Errors can be marked as retryable or fatal, allowing the model to reason explicitly about recovery. Because retries are mediated through the same schema, repeated calls remain safe, auditable, and deterministic.

This design shifts retry logic from opaque control flow into the reasoning loop itself.

### Parallel tool calls

Not all tool calls are sequential. In many cases, the model can identify independent actions that may be executed concurrently. Modern agent runtimes allow the model to emit *multiple* tool calls in a single step when their contracts indicate no dependency.

Conceptually:

```json
[
  { "name": "fetch_user_profile", "arguments": { "user_id": "123" } },
  { "name": "fetch_recent_orders", "arguments": { "user_id": "123" } }
]
```

The framework executes these calls in parallel and returns their results together as structured state updates. From the model’s perspective, this is still a single reasoning step, but one that expands the available context more efficiently.

Parallelism is only safe because contracts make dependencies explicit. Without schemas, concurrent execution would be speculative; with schemas, it becomes a controlled optimization.

### Why this pattern matters

Tool contracts and schemas transform tool use from an informal convention into a disciplined interface. They enable validation before execution, structured feedback after execution, principled retries, safe parallelism, and explicit termination.

More importantly, they define clear capability boundaries. The model can act only through interfaces that are precisely specified, making agent behavior predictable, debuggable, and scalable. In practice, this pattern is what allows tool use to serve as the foundation of reliable agentic systems rather than an ad hoc extension of prompting.

### References

1. Andreas, J., et al. *Semantic Parsing as Machine Translation*. ACL, 2013.
2. Liang, P., et al. *Neural Symbolic Machines*. ACL, 2017.
3. OpenAI. *Function Calling and Structured Outputs in Large Language Models*. Technical blog, 2023.
4. Yao, S., et al. *ReAct: Synergizing Reasoning and Acting in Language Models*. ICLR, 2023.


## Tool Permissions

Tool permissions define the explicit authority boundaries that govern what an agent is allowed to observe, query, or mutate when interacting with external systems.

### Historical perspective

The notion of permissions in agentic systems inherits directly from two earlier research lines. The first is **capability-based security**, developed in the 1970s and 1980s, where authority is represented as an explicit, unforgeable capability rather than an implicit global right. The second is **sandboxing and access control** in operating systems, which formalized read/write/execute distinctions to contain damage from faulty or malicious programs.

When early autonomous agents emerged in planning and robotics research, permissions were mostly implicit: agents were assumed to operate in closed worlds with trusted sensors and actuators. As agents began to interact with external APIs, databases, and eventually the open internet, this assumption broke down. By the late 2010s, research on **tool-augmented language models** and **LLM-based agents** highlighted new failure modes: unintended side effects, prompt injection, and data exfiltration through tools. This led to renewed emphasis on explicit permission models, especially in enterprise and safety-critical contexts.

### Tool permissions in agentic systems

In an agentic system, tools are not neutral utilities. Each tool represents a channel through which the agent can affect or learn about the world. Tool permissions therefore serve three closely related goals:

1. **Containment**: limiting the blast radius of mistakes or hallucinations.
2. **Confidentiality**: preventing sensitive context from leaking through tool calls.
3. **Governance**: making agent behavior auditable and policy-compliant.

Unlike traditional applications, agents dynamically decide *when* and *how* to invoke tools. This makes static access control insufficient. Permissions must be enforced at the tool boundary and evaluated at runtime, not merely assumed at design time.

A useful mental model is to treat every tool invocation as a privileged operation that must be explicitly justified by the agent’s role and current task.

### Read vs write permissions

The most fundamental distinction is between **read** and **write** capabilities.

**Read tools** observe or retrieve information without modifying external state. Examples include database queries, file reads, or internet search. Although often considered “safe,” read tools can still leak sensitive information indirectly, especially when their results are combined with private context.

**Write tools** mutate state: updating a database, sending an email, executing a transaction, or modifying files. These tools carry a higher risk because mistakes are persistent and sometimes irreversible.

In practice, robust agent architectures treat read and write tools very differently:

* Read tools are often broadly available but heavily filtered and redacted.
* Write tools are narrowly scoped, role-bound, and frequently gated behind additional checks or confirmations.

A minimal illustration of this distinction at the tool boundary might look like:

```python
# Read-only tool: allowed to observe, never mutate
def search_documents(query: str) -> list[str]:
    """Searches an indexed corpus and returns matching excerpts."""
    ...

# Write-capable tool: explicit mutation of external state
def update_record(record_id: str, payload: dict) -> None:
    """Updates a persistent record. Requires write permission."""
    ...
```

The critical point is not the function signature itself, but the **permission metadata** attached to it and enforced by the agent runtime.

### Permission to connect and external access

A particularly sensitive permission is the ability to **connect to external systems**, such as the public internet or third-party APIs.

Granting an agent unrestricted network access introduces several risks:

* **Prompt leaking**: sensitive internal context may be embedded into search queries or API calls.
* **Data exfiltration**: private data can be unintentionally transmitted to untrusted services.
* **Policy violations**: agents may access sources that are disallowed by organizational or legal constraints.

Enterprise-grade systems therefore treat “connect” as a first-class permission, separate from read or write. An agent may be allowed to read from internal databases but forbidden from making outbound network requests, or allowed to search only through approved, mediated services.

Conceptually, this often appears as a constrained tool set:

```python
# Internet access explicitly mediated
def web_search(query: str) -> list[str]:
    """Searches the web using an approved gateway with redaction."""
    ...
```

Here, the gateway—not the agent—enforces logging, filtering, and redaction, ensuring that private context never leaves the trust boundary.

### Prompt leaking and contextual integrity

Prompt leaking is a uniquely agentic failure mode. Because agents reason over rich internal context, they may inadvertently embed that context into tool inputs. For example, a search query might include proprietary information simply because it was salient in the agent’s reasoning trace.

Permissions mitigate this by enforcing **contextual integrity**: tools receive only the minimum information required to perform their function. This is often implemented by:

* Stripping or summarizing context before tool invocation.
* Separating private system state from user-visible or tool-visible state.
* Auditing tool inputs and outputs as structured artifacts.

The key insight is that permission checks are not only about *whether* a tool can be called, but also about *what information* is allowed to flow through that call.

### Permissions as an architectural boundary

In mature agentic systems, tool permissions become an architectural primitive rather than an afterthought. They define clear responsibility boundaries between:

* The agent’s reasoning core.
* The execution environment.
* External systems and data sources.

This separation enables safer composition of agents, easier audits, and incremental deployment of new capabilities without expanding the agent’s authority by default. In enterprise environments, it also aligns agent behavior with existing security, compliance, and governance frameworks.

Tool permissions therefore act as the practical bridge between abstract agent autonomy and real-world operational constraints.

### References

1. Lampson, B. *Protection*. ACM SIGOPS Operating Systems Review, 1971.
2. Dennis, J. B., Van Horn, E. C. *Programming Semantics for Multiprogrammed Computations*. Communications of the ACM, 1966.
3. Miller, M. S. *Capability-Based Security*. PhD Thesis, Johns Hopkins University, 2006.
4. Lewis, P. et al. *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*. NeurIPS, 2020.
5. OWASP Foundation. *Top 10 for Large Language Model Applications*. 2023. URL (optional)


## The Workspace

The workspace pattern introduces a shared, persistent file system that agents and tools use to externalize intermediate artifacts, manage context, and coordinate work beyond the limits of the model’s prompt.

---

### Historical perspective

The workspace pattern has deep roots in earlier AI research, long before language models imposed explicit context window constraints. Classical symbolic AI systems already separated transient reasoning from persistent state. Planning systems of the 1970s represented world states and intermediate plans in external data structures that survived individual inference steps. This separation made it possible to reason incrementally without recomputing everything from scratch.

In the 1980s, blackboard architectures made this idea explicit. Multiple specialized components cooperated indirectly by reading from and writing to a shared data store, rather than communicating through tightly coupled message passing. Cognitive architectures such as Soar and ACT-R later reinforced this distinction between short-term working memory and longer-lived declarative or procedural memory.

Modern agentic systems rediscover the same need under new constraints. Large language models are stateless and bounded by a finite context window, while real-world tasks often produce artifacts that are large, multi-modal, and persistent. The workspace re-emerges as the natural solution: a place outside the model where results, evidence, and intermediate state can accumulate over time.

---

### The workspace as a concrete abstraction

At its core, the workspace is intentionally simple: it is a directory on disk. Tools can read files from it and write files into it, and those files persist across tool calls and agent steps. There is no requirement for a database, schema, or specialized API. The power of the pattern comes precisely from its minimalism.

By relying on files as the shared medium, the workspace becomes universally accessible. Tools written in different languages, running in different processes, or operating on different modalities can still interoperate. The agent’s prompt remains small and focused on reasoning, while the workspace absorbs the bulk of the system’s state.

Conceptually, the workspace sits between the agent’s internal reasoning loop and the external world. It is not part of the model’s hidden state, and it is not necessarily user-facing output. Instead, it functions as shared working material: drafts, logs, datasets, generated assets, and partial results.

---

### Sharing and coordination

A defining property of the workspace is that it is shared. Tools do not pass large payloads to each other directly; they leave artifacts behind. Another tool, or another agent, can later pick them up by reading the same files. Humans can also inspect or modify these artifacts, turning the workspace into a collaboration surface rather than a hidden implementation detail.

This indirect coordination significantly reduces coupling. A tool only needs to know how to write its output and how to describe where it was written. It does not need to know which agent, tool, or human will consume it next. As systems scale to dozens of tools and agents, this loose coupling becomes essential.

---

### Context management, memory, and RAG

The workspace plays a central role in managing limited context windows. Large intermediate artifacts—such as long transcripts, structured datasets, or verbose logs—do not belong in the prompt. Instead, they are written to the workspace and referenced indirectly.

Over time, the workspace naturally takes on the role of long-term memory. Artifacts persist across runs and can be selectively reintroduced into context when needed. This aligns closely with retrieval-augmented generation: documents stored in the workspace can be indexed, embedded, retrieved, and summarized, without ever forcing the full content back into the model’s prompt.

The result is a clear separation of concerns. The model reasons over concise summaries and pointers, while the workspace holds the unbounded, durable material.

---

### Writing files instead of returning large outputs

A practical best practice follows directly from this pattern. When a tool produces an output that is too large to safely return in full, it should write the complete result to the workspace and return only a concise summary together with a file path.

```python
def analyze_large_dataset(data, workspace):
    result = heavy_analysis(data)

    path = workspace / "analysis" / "full_result.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialize(result))

    return {
        "summary": summarize(result, max_tokens=200),
        "path": str(path),
    }
```

This allows the agent to continue reasoning without polluting its context, while preserving full fidelity in the external artifact.

---

### Multi-modal tools and the workspace

The workspace pattern is especially important for multi-modal tools. Images, audio, and video are naturally file-based artifacts and do not fit cleanly into textual prompts. Rather than attempting to encode or inline such outputs, tools should write them to the workspace and return lightweight metadata.

```python
def generate_image(prompt, workspace):
    image = render_image(prompt)

    path = workspace / "images" / "output.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)

    return {
        "description": prompt,
        "path": str(path),
    }
```

This keeps the agent’s reasoning loop purely textual while enabling rich, multi-modal outputs to flow through the system.

---

### Tool composition and system robustness

Because tools communicate indirectly through files, the workspace enables flexible composition. Tool chains can be rearranged without changing interfaces, partial failures can be inspected by examining intermediate artifacts, and retries become simpler because previous outputs already exist on disk.

In practice, the workspace often doubles as a debugging and audit surface. Especially in enterprise or regulated environments, the ability to inspect what an agent produced at each step is as important as the final answer.

---

### References

1. Newell, A. *The Knowledge Level*. Artificial Intelligence, 1982.
2. Engelmore, R., Morgan, A. *Blackboard Systems*. Addison-Wesley, 1988.
3. Laird, J. *The Soar Cognitive Architecture*. MIT Press, 2012.
4. Lewis, P. et al. *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*. NeurIPS, 2020.
5. Pydantic-AI Documentation. *Tools and Output Concepts*. [https://ai.pydantic.dev/](https://ai.pydantic.dev/)


## Advanced topics

Advanced tool use is where an agent stops being a “function caller” and becomes a supervised, adaptive system: it can ask for approval, reshape its toolset at runtime, defer execution across boundaries, and diagnose or repair its own tool interface.

### Historical perspective

Many of the “advanced” mechanisms in modern tool-using agents are re-appearances of older ideas from human–computer interaction and interactive AI. Mixed-initiative interfaces studied when and how a system should act autonomously versus when it should ask the user, emphasizing principles for interruptibility, uncertainty-aware escalation, and keeping the human in control (late 1990s). ([Eric Horvitz][1])

In parallel, interactive machine learning formalized feedback loops where people correct, guide, or approve model behavior during operation rather than only at training time. These ideas map cleanly onto tool-using agents: the “model” proposes an external action (a tool call), and a human can confirm, deny, or revise it before any irreversible side-effect occurs. ([Microsoft][2])

### Human in the loop for tools

Human-in-the-loop (HITL) for tool use is not just “ask the user sometimes.” It is a deliberate control surface that converts high-impact tool invocations into *reviewable* requests. The key is to treat certain tool calls as *proposed actions* that require explicit approval (or additional input) before execution.

In practice, HITL is most valuable when tools have one or more of these properties:

* **Irreversible side effects** (sending messages, placing orders, writing to production systems).
* **Security/privacy risk** (exfiltration, access-controlled data, broad queries that could leak context).
* **High cost** (compute, paid APIs, long-running jobs).
* **Ambiguity** (the model’s intent is plausible but underspecified).

A common pattern is *policy-based gating*: decide at runtime whether a proposed tool call can run automatically, must be approved, or must be denied/rewritten.

```python
def requires_approval(tool_name: str, args: dict) -> bool:
    # High-risk tools always require review
    if tool_name in {"send_email", "post_to_slack", "execute_sql", "deploy"}:
        return True
    # Risk-based gating on arguments
    if tool_name == "execute_sql" and ("DROP" in args.get("query", "").upper()):
        return True
    if tool_name == "web_search" and args.get("query_scope") == "broad":
        return True
    return False
```

When approval is required, the agent should emit a structured “tool request” that is easy to review: tool name, arguments, rationale, expected side effects, and a rollback story (if any). The approval channel can also support *human steering*: the reviewer edits arguments, adds constraints, or supplies missing context, then resumes the run.

HITL is increasingly described as a first-class mechanism in agent frameworks, where certain tool calls can be flagged for approval based on context or arguments. ([GitHub][3])

### Dynamic tools

“Dynamic tools” means the agent’s available tool interface is not static. Instead, the system can **filter, modify, or augment** tool definitions *at each step* based on context, policy, user role, runtime state, or the current phase of a plan. Conceptually, this is a *tool shaping* step inserted between “decide next action” and “call a tool.”

Common uses:

* **Contextual minimization:** only expose tools relevant to the current subtask (reduces tool confusion and prompt/tool overhead).
* **Progressive disclosure:** start with safe read-only tools; unlock write tools only after a validated plan.
* **Capability routing:** swap tool backends based on tenant, region, permissions, or latency.
* **Argument hardening:** inject guardrails (rate limits, scopes, allowlists) into schemas or tool metadata.

```python
def prepare_tools(all_tools: list, state: dict) -> list:
    phase = state.get("phase", "explore")

    # In exploration, restrict to read-only tools.
    if phase == "explore":
        return [t for t in all_tools if t.meta.get("side_effects") == "none"]

    # In execution, allow write tools but only if a plan was approved.
    if phase == "execute" and state.get("plan_approved") is True:
        return all_tools

    # Default: safest subset.
    return [t for t in all_tools if t.meta.get("risk") in {"low"}]
```

This pattern is explicitly supported in modern tool systems as an agent-wide hook to filter/modify tool definitions step-by-step. ([Pydantic AI][4])

### Deferred tools

Deferred tools separate *selection* of a tool call from *execution* of that tool call. The agent can propose one or more tool invocations, then **pause** and return a bundle of “deferred requests.” Execution happens later—possibly by a human reviewer, an external worker, or a different trust zone—after which the run resumes with the corresponding results.

This is the cleanest way to model:

* HITL approvals (human approves/denies, maybe edits arguments).
* Long-running jobs (async execution).
* Cross-environment execution (agent in a restricted environment, tool runs elsewhere).
* Compliance boundaries (execution requires audit logging, ticketing, or dual control).

The core contract is an *idempotent continuation*: the agent pauses with structured requests, then resumes with structured results, maintaining stable call identifiers so results can be matched to requests.

```python
# Run 1: agent proposes actions but does not execute them.
deferred = agent.run_until_deferred(user_goal)

# deferred.calls: [{id, tool_name, args, rationale, risk_level}, ...]

approved_results = []
for call in deferred.calls:
    decision = human_review(call)  # approve/deny/edit
    if decision.approved:
        result = execute_tool(call.tool_name, decision.args)
        approved_results.append({"id": call.id, "result": result})
    else:
        approved_results.append({"id": call.id, "error": "denied"})

# Run 2: resume with results, continuing the same trajectory.
final = agent.resume_with_results(history=deferred.history, results=approved_results)
```

This “pause with requests → resume with results” mechanism is described directly in deferred-tool documentation. ([Pydantic AI][5])

### Tool doctor (development-time focus)

A *tool doctor* is a development-cycle mechanism used to analyze tool definitions and produce concrete recommendations for improvement **before** those tools are exposed to a running agent. Its goal is preventive rather than reactive: to eliminate ambiguous, underspecified, or misleading tool contracts that would otherwise manifest as failures, retries, or incorrect behavior at runtime.

From an architectural perspective, many issues attributed to “model errors” are in fact interface errors. Poorly chosen tool names, vague descriptions, inconsistent argument schemas, unclear return types, or undocumented side effects all increase the cognitive load on the model and reduce the reliability of tool selection and invocation. A tool doctor treats tool definitions as first-class artifacts that deserve the same scrutiny as APIs or library interfaces in traditional software engineering.

In the development cycle, the tool doctor is typically run as part of tool authoring or integration, alongside tests and schema validation. It inspects each tool definition and evaluates it against a set of qualitative criteria: whether the name accurately reflects behavior, whether the description is sufficiently explicit for an LLM to reason about usage, whether arguments are well-typed and semantically clear, and whether return values and side effects are properly documented. The output is a structured set of recommendations that developers can act on directly.

Conceptually, this is closer to *linting* or *design review* than to runtime monitoring. The emphasis is on improving contracts, not executing tools. A minimal interaction loop looks like this:

```python
# Development-time analysis
tools = load_tool_definitions()
recommendations = run_tool_doctor(tools)

for r in recommendations:
    if r.severity in {"warn", "critical"}:
        apply_fix(r)
```

Your provided implementation follows this pattern closely. It batches tools to stay within context limits, ignores well-defined or irrelevant tools, and focuses on non-trivial improvements. This batching is not an optimization detail but a design constraint: tool doctors are meant to be run repeatedly during development, and they must scale to tool libraries with dozens or hundreds of entries.

A key design choice is that recommendations are *structured*, not free-form text. By emitting typed findings—tool name, issue category, severity, and suggested changes—the tool doctor enables downstream automation. Recommendations can be surfaced in CI pipelines, turned into pull request comments, or even applied semi-automatically to regenerate improved tool schemas.

```python
ToolRecommendation(
    tool_name="search_documents",
    severity="warn",
    issue="Description underspecified",
    recommendation="Clarify expected input scope and ranking behavior",
    example_patch="Search indexed documents by keyword with optional filters..."
)
```

Although it is possible to apply similar diagnostics to runtime logs, this should be understood as an extension rather than the primary role of a tool doctor. The canonical use is *pre-runtime*: improving tools so that agents encounter fewer ambiguities, require fewer retries, and operate within clearer safety and capability boundaries.

In short, the tool doctor belongs squarely in the development loop. It formalizes a practice that experienced teams already follow informally—reviewing and refining tool interfaces—but adapts it to the unique demands of language-model-driven agents, where the “caller” is probabilistic and highly sensitive to interface quality.

### Putting the pieces together

Advanced tool use is best understood as a *control architecture* around the basic tool loop:

1. **Prepare toolset (dynamic tools):** expose only relevant/safe tools for this step. ([Pydantic AI][4])
2. **Model proposes tool calls:** possibly multiple calls in a plan.
3. **Gate execution (HITL policy):** auto-run safe calls; defer risky calls for approval. ([GitHub][3])
4. **Pause/resume (deferred tools):** return structured requests; later resume with structured results. ([Pydantic AI][5])
5. **Diagnose and improve (tool doctor):** if failures recur, repair the tool contract (and optionally code), then re-run.

This combination preserves autonomy where it is safe and cheap, while providing strong guarantees—reviewability, auditability, and controllable side effects—where it matters.

### References

1. Eric Horvitz. *Principles of Mixed-Initiative User Interfaces*. CHI, 1999. ([ACM Digital Library][7])
2. Saleema Amershi, et al. *Power to the People: The Role of Humans in Interactive Machine Learning*. AI Magazine, 2014. ([Microsoft][2])
3. Shunyu Yao, et al. *ReAct: Synergizing Reasoning and Acting in Language Models*. 2022 (ICLR 2023). ([arXiv][8])
4. PydanticAI Documentation. *Advanced Tool Features (Dynamic Tools)*. ([Pydantic AI][4])
5. PydanticAI Documentation. *Deferred Tools*. ([Pydantic AI][5])
6. Ilyes Bouzenia, et al. *An Autonomous, LLM-Based Agent for Program Repair (RepairAgent)*. arXiv, 2024. ([arXiv][6])
7. W. Takerngsaksiri, et al. *Human-In-the-Loop Software Development Agents*. arXiv, 2024. ([arXiv][9])

[1]: https://erichorvitz.com/chi99horvitz.pdf?utm_source=chatgpt.com "Principles of Mixed-Initiative User Interfaces - of Eric Horvitz"
[2]: https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/amershi_AIMagazine2014.pdf?utm_source=chatgpt.com "The Role of Humans in Interactive Machine Learning"
[3]: https://github.com/pydantic/pydantic-ai?utm_source=chatgpt.com "GenAI Agent Framework, the Pydantic way"
[4]: https://ai.pydantic.dev/tools-advanced/?utm_source=chatgpt.com "Advanced Tool Features"
[5]: https://ai.pydantic.dev/deferred-tools/?utm_source=chatgpt.com "Deferred Tools"
[6]: https://arxiv.org/abs/2403.17134?utm_source=chatgpt.com "An Autonomous, LLM-Based Agent for Program Repair"
[7]: https://dl.acm.org/doi/10.1145/302979.303030?utm_source=chatgpt.com "Principles of mixed-initiative user interfaces"
[8]: https://arxiv.org/abs/2210.03629?utm_source=chatgpt.com "ReAct: Synergizing Reasoning and Acting in Language Models"
[9]: https://arxiv.org/abs/2411.12924?utm_source=chatgpt.com "Human-In-the-Loop Software Development Agents"


## MCP — Model Context Protocol

The Model Context Protocol (MCP) defines a standardized, long-lived interface through which models interact with external capabilities—tools, resources, and stateful services—using structured messages over well-defined transports.

---

### Historical perspective

The emergence of MCP is closely tied to the practical challenges encountered in early desktop and IDE-style agent deployments around 2023–2024. Systems such as Claude Desktop exposed local capabilities—files, shells, search indices, and custom utilities—to language models. Initially, these integrations relied on embedding tool descriptions directly into prompts and parsing structured outputs. While workable for short-lived interactions, this approach quickly showed its limits as sessions became longer, tools more numerous, and state more complex.

The architectural inspiration for MCP comes largely from the Language Server Protocol (LSP), introduced in 2016. LSP demonstrated that a clean separation between a client (the editor) and a capability provider (the language server) could be achieved using a small set of protocol primitives: JSON-RPC messaging, capability discovery, and long-running server processes. MCP generalizes this idea from *editor ↔ language tooling* to *model ↔ external environment*.

From a research perspective, MCP builds on earlier work in tool-augmented language models, program synthesis with external oracles, and agent architectures that distinguish reasoning from acting. As agents evolved from single-turn planners into systems expected to operate continuously—maintaining memory, monitoring processes, and reacting to external events—the lack of a stable interaction protocol became a bottleneck. MCP arises not as a new reasoning paradigm, but as the infrastructural layer required to make agentic behavior robust over time.

---

### From embedded tools to protocolized capabilities

Traditional tool use patterns treat tools as prompt-level constructs: schemas are injected into context, the model emits a structured call, and the runtime executes it. MCP reframes this interaction by moving tools out of the prompt and into **external servers** that expose capabilities through a shared protocol.

In this model, a tool is no longer a static definition bundled with the agent. It is a remotely exposed capability with its own lifecycle, versioning, and state. The agent connects to a server, queries what is available, and then reasons about which capabilities to invoke. This shift enables reuse across agents, reduces prompt size, and makes tool behavior observable and debuggable at the protocol level.

---

### Transport evolution and protocol design

MCP adopts JSON-RPC 2.0 as its core message format, inheriting well-understood semantics for requests, responses, notifications, and error handling. Early implementations favored persistent local transports, closely mirroring LSP. As MCP moved beyond desktop use cases, the protocol evolved to support web-native transports.

HTTP enables MCP servers to be deployed behind standard infrastructure, integrated with authentication and authorization systems, and scaled independently. Server-Sent Events (SSE) complement this by allowing servers to push asynchronous updates and streamed results back to the agent runtime. Crucially, MCP separates message semantics from transport details, allowing the same protocol concepts to operate across local, remote, and hybrid environments.

---

### MCP as a generalization of tool use

While tool invocation is a central use case, MCP generalizes the notion of “tools” into a broader concept of **capabilities**. These typically include callable functions, addressable resources such as files or datasets, reusable prompt fragments, and event streams emitted by long-running operations.

Rather than embedding all of this information in the model’s context window, the agent maintains a live connection to one or more MCP servers. The model focuses on reasoning and decision-making, while the protocol layer handles execution, retries, streaming, and persistence. A minimal interaction sequence illustrates the idea:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "capabilities/list"
}
```

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "search_documents",
    "arguments": {
      "query": "tool permissions in agent systems"
    }
  }
}
```

The model never needs to know where the tool runs or how it is implemented—only the contract exposed by the server.

---

### MCP as an architectural boundary

A key contribution of MCP is the introduction of a **hard architectural boundary** between models and execution environments. MCP makes explicit that models reason, but do not own stateful side effects. Files, caches, background tasks, and long-running computations live on the server side; the model interacts with them through identifiers and protocol messages.

This separation clarifies responsibilities. Tool servers evolve independently of agent prompts. Multiple agents can share the same capabilities. Security and permissioning can be enforced at the protocol boundary rather than through fragile prompt conventions. Conceptually, MCP plays a role similar to an operating system interface: it mediates access to resources without embedding implementation details into application logic.

---

### Capability discovery and late binding

MCP emphasizes late binding. Capabilities are discovered at connection time rather than fixed at agent construction. This allows agents to adapt to different environments, permission sets, or deployments without modification. The agent remains generic; specialization emerges from the servers it connects to.

This design is particularly important in enterprise and multi-tenant settings, where available tools may depend on user identity, organizational policy, or runtime context. By deferring binding decisions to the protocol layer, MCP avoids the combinatorial explosion that would result from statically encoding all possibilities into prompts.

---

### Stateful servers and long-running interactions

Another defining aspect of MCP is the explicit distinction between stateless models and stateful servers. Persistent context belongs with the server: open documents, indexed corpora, partial computations, or monitoring tasks. The model references this state indirectly, using handles or resource identifiers.

This inversion is essential for long-running agents. Instead of repeatedly expanding prompts to carry accumulated state, MCP allows agents to operate over compact references. Token usage is reduced, failure modes become clearer, and sessions can span far beyond what prompt-based approaches allow.

---

### Streaming, events, and non-blocking tools

MCP also generalizes beyond simple request–response interactions. Tools may emit incremental updates or asynchronous events, allowing agents to monitor progress, interleave reasoning, or react to external changes. This enables non-blocking patterns such as long-running analysis, background ingestion, or continuous observation of external systems.

At the protocol level, these interactions are explicit, rather than simulated through repeated polling or prompt reconstruction.

---

### Why MCP matters

MCP provides the connective tissue that allows all prior tool-use patterns to scale. Tool contracts define what can be called, permissions define whether it may be called, workspaces define where artifacts live, and MCP defines how these pieces interact over time. It does not replace tool use; it stabilizes it.

For modern agentic systems—especially those operating over long horizons, with many tools or multiple agents—MCP is less an optimization than a prerequisite for maintainable design.

---

### References

1. Microsoft. *Language Server Protocol Specification*. Microsoft, 2016–. [https://microsoft.github.io/language-server-protocol/](https://microsoft.github.io/language-server-protocol/)
2. Anthropic. *Model Context Protocol*. Technical documentation, 2024. [https://modelcontextprotocol.io/](https://modelcontextprotocol.io/)
3. Pydantic AI Team. *Model Context Protocol Overview*. Technical documentation, 2024. [https://ai.pydantic.dev/mcp/overview/](https://ai.pydantic.dev/mcp/overview/)
4. Schick et al. *Toolformer: Language Models Can Teach Themselves to Use Tools*. NeurIPS, 2023.
5. Yao et al. *ReAct: Synergizing Reasoning and Acting in Language Models*. ICLR, 2023.


### Orchestration & Control Flow

# Chapter 5: Orchestration & Control Flow

## Workflows

**One-line introduction.**
Workflows define a structured, repeatable control flow that coordinates multiple agent steps—often across roles, tools, and time—into a coherent execution pipeline.

### Historical perspective

The idea of workflows predates modern AI by decades. Early inspirations come from **workflow management systems** and **business process modeling** in the 1990s, where explicit graphs and state transitions were used to coordinate long-running, multi-step processes. In parallel, **multi-agent systems (MAS)** research explored coordination mechanisms such as task allocation, delegation, and contract nets, formalized in the late 1980s and 1990s.

In AI planning, classical planners introduced the notion of decomposing goals into ordered or partially ordered actions. Later, **Hierarchical Task Networks (HTNs)** provided a way to encode reusable procedural knowledge. As large language models emerged, early agent designs reused these ideas implicitly: chains of prompts, hand-written controllers, and role-based agents passing messages.

From around 2023 onward, workflows re-emerged as a first-class abstraction in agent frameworks. This shift was driven by practical constraints: increasing system complexity, the need for observability and recovery, and the realization that purely autonomous agents benefit from explicit control structures. Modern workflow-based agents combine LLM-driven reasoning with deterministic orchestration layers, reconnecting contemporary agent systems with earlier ideas from workflow engines and MAS coordination.

### The workflow pattern

A workflow is an explicit control structure that governs *when*, *how*, and *by whom* work is performed. Rather than a single agent reasoning end-to-end, the system is decomposed into stages with well-defined responsibilities.

At its core, a workflow defines:

* **Stages or nodes**, each representing a task, agent invocation, or decision point.
* **Transitions**, which specify how execution moves from one stage to the next.
* **State**, which carries intermediate artifacts (plans, partial results, decisions) across stages.

Unlike simple chains, workflows allow branching, looping, retries, and conditional execution. This makes them suitable for complex tasks such as document processing pipelines, research assistants, or operational agents that must pause, resume, or escalate.

#### Delegation and hand-offs

A common workflow structure relies on *delegation*. A coordinating component assigns a subtask to a specialized agent, then waits for its result before continuing. Delegation is typically asymmetric: one agent owns the global objective, while others operate within narrower scopes.

Closely related are *hand-offs*, where responsibility is explicitly transferred. Instead of returning a result and terminating, an agent may pass control—along with context and state—to another agent. This is useful when tasks progress through distinct phases, such as analysis → execution → verification.

Conceptually, delegation returns control to the caller, while a hand-off moves the workflow forward by changing the active agent.

#### Single-agent vs multi-agent workflows

Workflows can be implemented with a single agent invoked multiple times, or with multiple agents collaborating. In a single-agent workflow, the orchestration layer constrains the agent’s reasoning by dividing execution into steps. In multi-agent workflows, each node is backed by a different agent with its own tools, permissions, or prompt specialization.

Multi-agent workflows are particularly effective when:

* Tasks require heterogeneous expertise.
* Tool access must be isolated.
* Parallel progress is possible on independent subtasks.

Frameworks such as LangGraph (from the LangChain ecosystem) popularized graph-based workflows where nodes represent agents and edges encode control flow. The key idea, however, is independent of any framework: workflows externalize control logic instead of embedding it entirely in prompts.

### Illustrative snippets

The following snippets illustrate concepts rather than full implementations.

**Delegation within a workflow**

```python
# Coordinator assigns a focused task to a specialist agent
result = specialist_agent.run(
    task="Summarize recent papers on topic X",
    context=shared_state
)

shared_state["summary"] = result
```

**Programmatic hand-off**

```python
# Agent decides the next responsible agent
next_agent = choose_agent(shared_state)

return {
    "handoff_to": next_agent,
    "state": shared_state,
}
```

**Conditional transitions**

```python
if shared_state["confidence"] < 0.8:
    goto("verification_step")
else:
    goto("final_output")
```

These patterns make the control flow explicit and auditable, while still allowing agents to reason within each step.

### Why workflows matter

Workflows provide a bridge between autonomous reasoning and engineered reliability. By separating *what* an agent reasons about from *how* execution progresses, they enable better debugging, testing, and governance. They also integrate naturally with long-running and event-driven systems, where execution cannot be assumed to be linear or instantaneous.

In orchestration-heavy systems, workflows are often the backbone on which more advanced patterns—graphs, replanning, and agent-to-agent protocols—are built.

### References

1. Smith, R. G. *The Contract Net Protocol*. IEEE Transactions on Computers, 1980.
2. Erol, K., Hendler, J., Nau, D. *Hierarchical Task Network Planning*. Artificial Intelligence, 1994.
3. Wooldridge, M. *An Introduction to MultiAgent Systems*. Wiley, 2002.
4. LangChain Team. *Workflows and Agents in LangGraph*. LangChain Documentation, 2024. [https://docs.langchain.com/](https://docs.langchain.com/)
5. LangChain Team. *Multi-Agent Workflows with LangGraph*. LangChain Blog, 2024. [https://blog.langchain.com/](https://blog.langchain.com/)


## Graphs

The graph pattern models agent execution as a directed graph of states and transitions, enabling explicit, inspectable, and controllable flows beyond linear or workflow-based orchestration.

### Historical perspective

The use of graphs to represent computation predates modern agentic systems by several decades. Early work on finite state machines and Petri nets in the 1960s established that complex behavior could be described as transitions between explicit states governed by formal rules. In parallel, compiler research introduced control flow graphs as a way to reason about all possible execution paths of a program, enabling static analysis, optimization, and verification.

In artificial intelligence, graph-based representations became central through planning and decision-making research. Classical planners represented world states and actions as nodes connected by transitions, while later work on Markov Decision Processes framed sequential decision-making as movement through a state-transition graph under uncertainty. As large language models began to be used as reasoning components rather than static predictors, these ideas resurfaced in a practical form: explicit graphs provided a way to structure multi-step, branching, and iterative behaviors that were otherwise fragile when encoded implicitly in prompts.

### The graph pattern in agentic systems

In agentic systems, a graph is composed of nodes, edges, and shared state, with execution defined as traversal through this structure. A node represents a semantically meaningful unit of work, such as invoking a model, calling a tool, validating an intermediate result, or coordinating with another agent. Nodes are deliberately coarse-grained, reflecting conceptual steps in reasoning or action rather than low-level operations.

Edges define the possible transitions between nodes. These transitions may be unconditional, rule-based, or dependent on runtime state, including model outputs. Unlike workflows, graphs naturally support branching, merging, and cycles, which makes them well suited for retry loops, refinement processes, conditional escalation, and adaptive strategies.

State is the explicit data structure that flows through the graph. It accumulates inputs, intermediate artifacts, decisions, and metadata produced by nodes. Because state is explicit and typed, it can be validated at boundaries, persisted between steps, replayed for debugging, or partially reconstructed after failure. This explicitness is a key difference from prompt-centric approaches, where state is often implicit and difficult to reason about.

Execution begins at a designated entry node. Each node consumes the current state, performs its logic, updates the state, and then selects the next edge to follow. Execution continues until a terminal node is reached or an external condition intervenes.

### Typed state and deterministic transitions

A central concept emphasized in modern graph-based agent frameworks is the use of explicitly defined state schemas. Rather than allowing arbitrary mutation, the state is treated as a well-defined contract between nodes. Each node declares which parts of the state it reads and which parts it may update, making data flow explicit.

This approach has two important consequences. First, it enables early validation and clearer failure modes: invalid or incomplete state can be detected at node boundaries rather than propagating silently. Second, it allows transitions to be expressed deterministically over state, even when individual nodes rely on probabilistic model outputs. The graph structure remains stable and inspectable, while uncertainty is localized within nodes.

### Conditional edges and control logic

Graphs make control logic explicit by modeling decisions as conditional transitions rather than hidden prompt instructions. After a node executes, the next node is selected by evaluating conditions over the updated state. These conditions may encode business rules, confidence thresholds, validation results, or external signals.

This separation between execution and control simplifies reasoning about system behavior. It becomes possible to enumerate all potential execution paths, understand where loops may occur, and verify that termination conditions exist. In contrast, when control logic is embedded implicitly in prompts, these properties are difficult to inspect or guarantee.

### Cycles, retries, and refinement

Cycles are a first-class feature of graph-based orchestration. They are commonly used to model refinement loops, such as drafting, evaluating, and revising an output until it meets a quality bar. Because the loop is explicit in the graph, exit conditions are also explicit and auditable, reducing the risk of unbounded retries or hidden infinite loops.

This structure also supports bounded retries and fallback strategies. A node may transition back to a previous step a fixed number of times, after which execution is redirected to an alternative path, such as escalation to a human or a more expensive reasoning strategy.

### Graphs in multi-agent orchestration

In multi-agent systems, graphs provide a clear mechanism for coordinating specialized agents. Nodes may correspond to different agents, each with distinct capabilities and constraints. The graph encodes when responsibility is handed off, how partial results are integrated, and under what conditions an agent is re-invoked.

Because the orchestration logic is explicit, system-level properties such as coverage, escalation paths, and failure handling can be reasoned about independently of individual agent prompts. This separation is essential for building reliable, production-grade agentic platforms.

### Operational considerations

From an operational standpoint, graph-based orchestration aligns naturally with long-running and fault-tolerant execution. Explicit nodes and transitions define natural checkpoints where state can be persisted. If execution is interrupted, it can resume from a known node with a known state. Execution traces map directly onto the graph, improving observability and post-mortem analysis.

Although graphs introduce more upfront structure than simple chaining, this structure is what enables scale, robustness, and controlled evolution. As agentic systems grow in complexity, explicit graphs shift orchestration from an emergent property of prompts to a designed and verifiable component of the system.

### References

1. C. A. Petri. *Kommunikation mit Automaten*. PhD thesis, University of Bonn, 1962.
2. R. Bellman. *Dynamic Programming*. Princeton University Press, 1957.
3. S. Russell, P. Norvig. *Artificial Intelligence: A Modern Approach*. Pearson, 1995.
4. Pydantic documentation. *Graphs*. 2024. [https://ai.pydantic.dev/graph/](https://ai.pydantic.dev/graph/)
5. LangChain. *Introduction to LangGraph*. LangChain Academy, 2023. [https://academy.langchain.com/courses/intro-to-langgraph](https://academy.langchain.com/courses/intro-to-langgraph)


# Chapter 5: Orchestration & Control Flow

## A2A: Agent-to-Agent Communication

**One-line introduction.**
Agent-to-Agent (A2A) communication is a coordination pattern in which autonomous agents interact through a shared protocol to delegate work, exchange state, and compose system-level behavior.

---

### Historical perspective

The intellectual roots of A2A go back to early work on distributed artificial intelligence and multi-agent systems in the late 1980s and 1990s. At that time, researchers observed that complex problem solving could not be reduced to a single reasoning entity, but instead emerged from cooperation, negotiation, and coordination between multiple agents. This led to the first explicit agent communication languages, such as KQML, and later to standardized specifications like FIPA-ACL, which formalized the structure and semantics of messages exchanged between agents.

In parallel, research in distributed systems and software architecture shaped how independent components should interact. Message passing, remote procedure calls, and event-driven systems emphasized loose coupling, explicit interfaces, and failure isolation. The actor model reinforced the idea that independent computational entities should communicate only through messages, never by shared mutable state.

Modern LLM-based agents inherit all of these traditions. While the internal reasoning mechanisms have changed dramatically, the architectural pressures remain the same: as soon as systems involve multiple agents with different responsibilities, lifecycles, or ownership boundaries, communication must be explicit, structured, and observable. The A2A Protocol emerges in this context as a contemporary formalization of agent communication, designed for long-running, heterogeneous, and production-grade agentic systems.

---

### The A2A pattern

At its core, A2A treats each agent as an independent, network-addressable entity with a well-defined boundary. An agent exposes what it can do, accepts requests from other agents, and produces responses or follow-up messages, all without revealing its internal implementation. Coordination is achieved through message exchange rather than shared control flow or shared memory.

This separation has important consequences. Agents can be developed, deployed, and evolved independently. Failures are localized to agent boundaries. System behavior emerges from interaction patterns rather than from a single central orchestrator. In this sense, A2A shifts orchestration from an internal control structure to an external protocol.

Unlike workflows or graphs, which primarily describe how steps are sequenced within a bounded execution, A2A focuses on how autonomous agents relate to one another across time. It provides the connective tissue that allows multiple workflows, owned by different agents, to form a coherent system.

---

### Core capabilities

A2A communication relies on a small set of foundational capabilities that are intentionally minimal but powerful. Each agent has a stable identity and a way to describe its capabilities so that other agents know what kinds of requests it can handle. Communication happens through standardized message envelopes that carry not only the payload, but also metadata such as sender, recipient, intent, and correlation identifiers. This metadata makes it possible to trace interactions, reason about partial failures, and correlate responses with earlier requests.

Messages are typically intent-oriented rather than procedural. Instead of calling a specific function, an agent asks another agent to *perform an analysis*, *retrieve information*, or *review a decision*. This level of abstraction makes interactions more robust to internal refactoring and allows agents to apply their own policies, validation steps, or human-in-the-loop checks before acting.

Crucially, A2A communication is asynchronous by default. An agent may acknowledge a request immediately, process it over minutes or hours, and send intermediate updates or a final result later. This makes the pattern well suited for long-running tasks, background analysis, and real-world integrations where latency and partial completion are unavoidable.

---

### How A2A works in practice

From an execution standpoint, A2A introduces a thin protocol layer between agents. When one agent wants to delegate work, it constructs a message that describes the intent and provides the necessary input data. This message is sent through the A2A transport to another agent, which validates the request, performs the work according to its own logic, and replies with one or more messages.

A minimal illustration looks like the following:

```python
# Agent A: delegate a task to another agent
message = {
    "to": "research-agent",
    "intent": "analyze_document",
    "payload": {"document_id": "doc-123"},
    "correlation_id": "task-42",
}

send_message(message)
```

```python
# Agent B: handle the request and respond
def on_message(message):
    if message["intent"] == "analyze_document":
        result = analyze_document(message["payload"])
        response = {
            "to": message["from"],
            "intent": "analysis_result",
            "payload": result,
            "correlation_id": message["correlation_id"],
        }
        send_message(response)
```

The important aspect is not the syntax, but the architectural boundary. Each agent owns its execution, state, and failure handling. The protocol provides just enough structure to make coordination reliable without constraining internal design choices.

---

### Role of A2A in orchestration

As agentic systems scale, purely centralized orchestration becomes increasingly fragile. A2A enables a more decentralized model in which agents collaborate directly, while higher-level orchestration emerges from their interaction patterns. In practice, A2A often complements other control-flow constructs: workflows define local sequencing, graphs define structured decision paths, and A2A connects these pieces across agent boundaries.

This section intentionally remains shallow. The goal is to position A2A as a first-class orchestration pattern rather than to exhaustively specify the protocol. Later chapters will examine transports, schemas, security models, and advanced coordination strategies built on top of A2A.

---

### References

1. Wooldridge, M. *An Introduction to MultiAgent Systems*. Wiley, 2002.
2. Finin, T. et al. *KQML as an Agent Communication Language*. International Conference on Information and Knowledge Management, 1994.
3. FIPA. *FIPA ACL Message Structure Specification*. FIPA, 2002.
4. A2A Protocol Working Group. *A2A Protocol Specification*. 2024. [https://a2a-protocol.org/latest/](https://a2a-protocol.org/latest/)


## Long-running tasks and async execution

Long-running tasks and asynchronous execution allow agents to pursue goals that extend beyond a single interaction by persisting state, delegating work, and resuming execution in response to events.

### Historical perspective

The roots of long-running and asynchronous agent behavior lie in early research on autonomous agents and distributed systems. In the late 1970s and 1980s, the actor model and message-passing systems established the idea that computation could be expressed as independent entities communicating asynchronously, without shared control flow. During the 1990s, agent-oriented research—most notably Belief–Desire–Intention (BDI) architectures—formalized the notion of persistent goals and plans that unfold over time, can be suspended, and are revised as new information arrives.

Parallel developments in workflow systems, operating systems, and later cloud orchestration frameworks addressed similar problems from a systems perspective: how to manage long-running jobs, recover from partial failure, and coordinate independent workers. Modern agentic systems combine these traditions. Large language models provide flexible planning and reasoning, but must be embedded in orchestration layers that explicitly model time, state, and asynchronous coordination. Recent work on deep agents, sub-agents, and agent-to-agent protocols reflects this convergence between classical distributed systems and contemporary LLM-based agents.

### Conceptual model

In synchronous agent designs, reasoning and execution are tightly coupled: the agent plans, acts, and responds in a single linear flow. This breaks down when tasks take a long time, depend on slow external systems, or require parallel effort. The long-running and async execution pattern introduces a clear separation between intention, execution, and coordination.

An agent first commits to an objective and records it as durable state. Execution then proceeds asynchronously, often delegated to subordinate agents or background workers. Rather than blocking, the parent agent yields control and resumes only when meaningful events occur, such as task completion, partial results, timeouts, or external signals. The agent’s reasoning step becomes episodic, triggered by state transitions instead of continuous conversation.

### Deep agents and hierarchical delegation

A common realization of this pattern is the use of deep agent hierarchies. A top-level agent is responsible for the overall goal and lifecycle, while subordinate agents are created to handle well-scoped pieces of work. These sub-agents may themselves spawn further agents, forming a tree of responsibility that mirrors the structure of the problem.

The key property is that delegation is asynchronous. Once a sub-agent is launched, the parent does not wait synchronously for a response. Instead, it records expectations and moves on. When results eventually arrive, the parent agent incorporates them into its state and decides whether to proceed, replan, or terminate the task.

```python
# Conceptual sketch of async delegation

task_id = create_task(goal="analyze dataset", state="planned")

spawn_subagent(
    parent_task=task_id,
    objective="collect raw data",
    on_complete="handle_result"
)

spawn_subagent(
    parent_task=task_id,
    objective="run statistical analysis",
    on_complete="handle_result"
)

update_task(task_id, state="in_progress")
```

This structure enables parallelism and allows each sub-agent to operate on its own timeline.

### State, events, and resumption

Long-running tasks require explicit state management. Conversation history alone is insufficient, since execution may span hours or days and must survive restarts or failures. Instead, task state is externalized into durable storage and updated incrementally as events occur.

Execution progresses through a sequence of state transitions. Each transition triggers a short reasoning step that decides the next action. In this sense, the agent behaves more like an event-driven system than a conversational chatbot.

```python
# Resumption triggered by an async event

def handle_result(task_id, result):
    record_result(task_id, result)
    if task_is_complete(task_id):
        update_task(task_id, state="completed")
    else:
        decide_next_step(task_id)
```

This approach makes long-running behavior explicit, observable, and recoverable.

### Relationship to A2A protocols

Agent-to-agent (A2A) protocols provide the communication layer that makes asynchronous execution robust and scalable. Instead of direct, synchronous calls, agents exchange structured messages that represent requests, progress updates, and completion signals. Time decoupling is essential: senders and receivers do not need to be active simultaneously.

Within this pattern, long-running tasks can be understood as distributed conversations among agents, mediated by A2A messaging. Protocols define how agents identify tasks, correlate responses, and negotiate responsibility. This allows sub-agents to be deployed independently, scaled horizontally, or even operated by different organizations, while still participating in a coherent long-running workflow.

### Failure, recovery, and human involvement

Because long-running tasks operate over extended periods, failure is not exceptional but expected. The pattern therefore emphasizes retries, checkpoints, and escalation. Agents may automatically retry failed sub-tasks, switch strategies, or pause execution pending human review. Human-in-the-loop integration fits naturally at well-defined checkpoints, where the current task state can be inspected and adjusted without restarting the entire process.

### References

1. Hewitt, C. *Actor Model of Computation*. Artificial Intelligence, 1977.
2. Rao, A. S., & Georgeff, M. P. *BDI Agents: From Theory to Practice*. Proceedings of the First International Conference on Multi-Agent Systems, 1995.
3. Wooldridge, M. *An Introduction to Multi-Agent Systems*. John Wiley & Sons, 2002.
4. LangChain Blog. *Multi-Agent Workflows and Long-Running Agents*, 2023.
5. Pydantic AI Documentation. *Multi-agent applications and deep agents*. 2024. [https://ai.pydantic.dev/](https://ai.pydantic.dev/)
6. Anthropic. *Sub-agents and task delegation*. Documentation, 2024. [https://code.claude.com/docs/en/sub-agents](https://code.claude.com/docs/en/sub-agents)


## Event-driven agents

Event-driven agents organize their behavior around the reception and handling of events, reacting incrementally to changes in their environment rather than executing a predefined sequence of steps.

### Historical perspective

The foundations of event-driven agents can be traced back to early work in distributed systems and concurrency. In the 1970s, the actor model introduced the idea of autonomous entities that communicate exclusively through asynchronous message passing, eliminating shared state and global control flow. This model already embodied the core intuition behind event-driven agents: computation progresses as a reaction to incoming messages, not as a linear program.

During the 1980s and 1990s, research on reactive systems further refined these ideas. Reactive systems were defined not by producing a single output, but by maintaining ongoing interaction with an external environment. This work influenced state machines, event loops, and later publish–subscribe systems, which became common in large-scale distributed software during the 2000s. Complex event processing and event-driven middleware extended these ideas to environments with high event volumes and loose coupling between producers and consumers.

Modern agentic systems revive and generalize these concepts. Large language model–based agents frequently operate in open-ended, asynchronous environments: user messages arrive unpredictably, tools may take seconds or hours to respond, and other agents may emit signals at any time. Event-driven control flow provides a natural abstraction for these conditions, avoiding the rigidity of synchronous pipelines and enabling agents to remain responsive over long periods.

### Core idea

In an event-driven agent architecture, execution is initiated by events rather than by a single entry point. An event represents a meaningful occurrence: a user request, a message from another agent, the completion of a long-running task, a timer firing, or a change in external state. The agent listens for such events and reacts by updating its internal state, invoking reasoning or tools, and potentially emitting new events.

Control flow is therefore implicit. Instead of encoding “what happens next” as a fixed sequence, the agent’s behavior emerges from the combination of event types it understands, the current state it maintains, and the logic used to handle each event. This leads naturally to systems that are interruptible, resumable, and capable of handling multiple concurrent interactions.

### Structure of an event-driven agent

Conceptually, an event-driven agent is composed of three elements. First, there are event sources, which may be external (users, other agents, infrastructure callbacks) or internal (timers, state transitions). Second, there is an event dispatcher or loop that receives events and routes them to the appropriate logic. Third, there are event handlers that implement the agent’s reasoning and decision-making.

A handler typically performs a small, well-defined reaction: it interprets the event, loads the relevant state, possibly invokes an LLM or a tool, updates state, and emits follow-up events. The following sketch illustrates the idea:

```python
def handle_event(event, state):
    if event.type == "user_message":
        state = process_user_input(event.payload, state)
    elif event.type == "task_completed":
        state = integrate_result(event.payload, state)

    return state, next_events(state)
```

The important point is that handlers are written to be independent and idempotent. They do not assume exclusive control over execution, nor do they rely on a particular ordering beyond what is encoded in the state.

### Relationship to workflows and graphs

Event-driven agents differ fundamentally from workflow- or graph-based orchestration. Workflows and graphs make control flow explicit by defining steps and transitions ahead of time. Event-driven agents instead rely on reactions to stimuli. There is no single “next node”; the next action depends on which event arrives and how the current state interprets it.

In practice, these approaches are often combined. Event-driven orchestration is commonly used at the top level, determining when and why something happens, while workflows or graphs are used inside individual handlers to structure more complex reasoning or tool usage. This hybrid model preserves flexibility without sacrificing clarity where structured control flow is beneficial.

### Asynchrony, long-running tasks, and state

Event-driven agents align naturally with asynchronous execution. A handler can trigger a long-running operation and return immediately, relying on a future event to resume processing when the operation completes. This avoids blocking the agent and allows many tasks to progress concurrently.

State management becomes central in this model. Because events may arrive late, early, or more than once, handlers must validate assumptions against persisted state and handle duplicates safely. State is therefore externalized into durable storage, and events are treated as facts that may be replayed or retried.

A typical completion handler follows this pattern:

```python
def handle_task_completed(event, state):
    task_id = event.payload["task_id"]
    if task_id not in state.pending_tasks:
        return state  # stale or duplicate event

    state.pending_tasks.remove(task_id)
    state.results.append(event.payload["result"])
    return state
```

This style ensures that the agent can recover from failures and restarts without losing coherence.

### Event-driven agents in cloud environments

In production systems, event-driven agents are commonly implemented using managed cloud services. The key architectural idea is to separate a lightweight, reactive control plane from heavyweight execution.

The control plane consists of short-lived handlers that react to events, interpret state, and decide what to do next. In cloud platforms, these handlers are typically implemented as serverless functions or container-based services that scale automatically and are invoked by an event router. The data plane consists of longer-running or resource-intensive jobs executed in managed batch or container services.

In an AWS-style architecture, events are routed through a managed event bus or message queue. Lightweight handlers execute in response to these events, updating persistent state and submitting long-running jobs when needed. Batch-style services execute those jobs and emit completion events back onto the event bus, closing the loop. The agent itself is not a single process, but an emergent behavior defined by the flow of events and state transitions across these components.

A simplified control-plane handler might look like this:

```python
def on_event(event):
    state = load_state(event.correlation_id)

    if event.type == "request.received":
        job_id = submit_long_task(event.payload)
        state.pending[job_id] = "in_progress"
        save_state(state)

    elif event.type == "job.completed":
        update_state_with_result(state, event.payload)
        emit_event("agent.ready_for_next_step", state.summary())
        save_state(state)
```

A similar pattern applies in other cloud environments, where event routing services deliver events to short-lived handlers and long-running work is delegated to managed compute services. The specific services differ, but the conceptual model remains the same: events drive execution, handlers coordinate state, and completion is signaled through new events.

### Coordination between agents

Event-driven architectures also provide a natural foundation for multi-agent systems. Instead of invoking each other directly, agents publish and subscribe to events. This reduces coupling and allows agents to evolve independently. Messages between agents become a special case of events with well-defined schemas and semantics.

This approach also supports partial observability and access control. Agents can be restricted to seeing only certain event types or streams, which is critical in enterprise or safety-sensitive deployments.

### Practical considerations

Event-driven agents trade explicit control flow for flexibility. This increases the importance of observability, structured event schemas, and robust logging. Debugging often involves tracing event histories rather than stepping through code. Testing focuses on simulating event sequences and validating resulting state transitions.

Despite these challenges, event-driven agents are increasingly central to real-world agentic systems. They provide a scalable and resilient foundation for long-lived, interactive agents that must operate reliably in asynchronous, distributed environments.

### References

1. Hewitt, C. *Viewing Control Structures as Patterns of Passing Messages*. Artificial Intelligence, 1973.
2. Harel, D., Pnueli, A. *On the Development of Reactive Systems*. Logics and Models of Concurrent Systems, 1985.
3. Eugster, P. et al. *The Many Faces of Publish/Subscribe*. ACM Computing Surveys, 2003.
4. Luckham, D. *The Power of Events: An Introduction to Complex Event Processing*. Addison-Wesley, 2002.
5. [https://ai.pydantic.dev/](https://ai.pydantic.dev/)


# Execution Modes

## CodeAct

CodeAct is a code-centric execution pattern in which an agent reasons primarily by iteratively writing, executing, and refining code, using program execution itself as the main feedback loop.

### Historical perspective

Early agent systems treated code execution as an auxiliary tool: a way to call an API, run a calculation, or fetch data. This view began to shift with work on program synthesis, neural program induction, and reinforcement learning with executable environments, where the boundary between “reasoning” and “acting” blurred. In these settings, programs were not merely outputs but intermediate artifacts used to explore a solution space.

The CodeAct approach crystallized this shift by explicitly framing agent behavior as alternating between natural language reasoning and concrete code execution. The key insight was that many complex tasks—data analysis, environment control, system configuration—are more reliably solved by letting the model *think in code*, observe runtime effects, and adapt. This lineage connects earlier ideas such as tool-augmented language models and ReAct-style loops, but places executable code at the center rather than at the periphery.

### The CodeAct pattern

At its core, CodeAct treats code execution as the agent’s primary action modality. Instead of planning entirely in natural language and then calling tools, the agent incrementally constructs small programs, runs them, inspects results, and revises its approach. Reasoning emerges from the interaction between generated code and observed execution outcomes.

A typical CodeAct loop has four conceptual phases:

1. **Intent formation**: the agent translates a goal into a concrete computational step.
2. **Code generation**: the agent emits a small, focused code fragment.
3. **Execution and observation**: the code is executed in a controlled environment and produces outputs, side effects, or errors.
4. **Reflection and refinement**: the agent incorporates the observed behavior into the next iteration.

This loop continues until the goal is satisfied or the agent determines it cannot proceed further. Importantly, the unit of work is intentionally small: short scripts, single commands, or incremental state changes. This keeps failures local and feedback immediate.

Conceptually, this can be sketched as:

```python
while not goal_satisfied:
    step = agent.propose_code(context)
    result = execute(step)
    context = agent.observe_and_update(context, result)
```

The distinguishing feature is that *execution results are first-class signals*. Errors, stack traces, runtime values, and filesystem changes all become part of the agent’s working context.

### Execution environments and isolation

Effective CodeAct systems rely on a well-defined execution substrate. Code must run in an environment that is both expressive enough to be useful and constrained enough to be safe. The implementation summarized in the MCP Sandbox design illustrates several architectural consequences of this requirement.

Each agent session executes code inside a dedicated, isolated environment with its own filesystem and process space. This isolation allows the agent to experiment freely—creating files, starting processes, modifying state—without risking cross-session interference. From the agent’s perspective, the environment behaves like a persistent workspace rather than a disposable tool call.

A common pattern is to fix a canonical working directory inside the execution environment and treat it as the agent’s “world”:

```python
# inside the execution environment
with open("results.txt", "w") as f:
    f.write(str(computation_output))
```

The persistence of this workspace across executions is crucial. It allows CodeAct agents to build state incrementally, revisit previous artifacts, and recover transparently from execution failures by recreating the environment while preserving data.

### Failure, feedback, and recovery

Because CodeAct agents execute arbitrary code, failures are expected rather than exceptional. Syntax errors, runtime exceptions, timeouts, and resource exhaustion all serve as informative feedback. Robust systems therefore separate *failure detection* from *failure recovery*.

Execution is typically wrapped with pre-flight validation and post-execution checks:

```python
status = check_environment()
if not status.ok:
    recreate_environment()

result = run_code(snippet, timeout=5)
```

If execution fails, the agent does not crash the session. Instead, the failure is surfaced as structured feedback that informs the next reasoning step. Automatic environment recreation, combined with persistent workspaces, ensures that recovery is transparent and does not erase progress.

This design aligns naturally with the CodeAct philosophy: errors are signals to reason over, not terminal conditions.

### Concurrency and long-running behavior

Unlike simple tool calls, CodeAct executions may involve long-running processes such as servers, simulations, or background jobs. Treating these as first-class entities requires explicit lifecycle management distinct from one-off commands.

A common pattern is to separate *commands* from *services*. Commands are synchronous and produce immediate feedback; services are started, monitored, and stopped explicitly. The agent reasons about service state by inspecting process health and logs rather than assuming success.

This distinction enables CodeAct agents to orchestrate complex computational setups while retaining control over resource usage and cleanup.

### Security and control boundaries

Placing code execution at the center of agent behavior raises obvious safety concerns. CodeAct systems therefore rely on layered defenses: execution time limits, resource quotas, non-privileged runtimes, and strict filesystem scoping. From a pattern perspective, the important point is that these controls are *environmental*, not prompt-based. The agent is allowed to generate powerful code precisely because the execution substrate enforces hard constraints.

This separation of concerns simplifies agent design. The model focuses on problem solving, while the execution layer guarantees containment.

### Why CodeAct matters

CodeAct represents a shift from “agents that occasionally run code” to “agents whose primary mode of thought is executable”. This shift has practical consequences: more reliable iteration, clearer grounding in observable behavior, and a tighter feedback loop between intention and outcome. In practice, CodeAct often reduces prompt complexity, because correctness is enforced by execution rather than by exhaustive natural language reasoning.

As agents increasingly operate in technical domains—data engineering, infrastructure management, scientific computing—CodeAct provides a natural and scalable execution model.

### References

1. Wang et al. *CodeAct: Autonomous Code-Centric Agents*. arXiv, 2023.
2. Yao et al. *ReAct: Synergizing Reasoning and Acting in Language Models*. arXiv, 2022.
3. Chen et al. *Evaluating Large Language Models Trained on Code*. arXiv, 2021.
4. MCP documentation and design notes. *Model Context Protocol*. 2024.


## MCP Sandbox Overview

MCP Sandbox is an implementation of CodeAct. Itprovides secure, isolated execution environments for running arbitrary code through Docker containers. The system manages concurrent multi-tenant sessions, each with dedicated containers and filesystems, while ensuring resource isolation, failure recovery, and operational observability.

## Core Architecture

### Multi-Tenant Session Model

The architecture implements strict session isolation where each user session operates in a dedicated container with its own filesystem. Sessions are identified by a composite key (`user_id:session_id`), enabling multiple concurrent sessions per user while maintaining complete isolation.

**Key Design Decisions**:
- Composite session keys provide natural multi-tenancy without complex access control
- One-to-one mapping between sessions and containers simplifies lifecycle management
- Session state machines (CREATING → RUNNING → STOPPED/ERROR) enable predictable state transitions
- Activity tracking with configurable timeouts enables automatic resource reclamation

**Trade-offs**:
- Each session requires a full container (higher resource usage vs. simpler isolation)
- Container startup latency on first request (mitigated by lazy creation pattern)
- Resource overhead acceptable for strong isolation guarantees

### Data Isolation Through Filesystem Namespacing

Each session's data resides in a host directory mounted into the container at a fixed path. This design provides filesystem isolation while enabling data persistence across container lifecycles.

**Directory Hierarchy**:
```
{base_data_dir}/
  └── {user_id}/
      └── {session_id}/
          └── [session data]
```

**Benefits**:
- Physical isolation at filesystem level prevents cross-session access
- Data persists when containers are recreated after failures
- Path translation layer (`to_host_path`/`to_container_path`) abstracts storage details
- Supports both bind mounts (local development) and named volumes (production)

**Path Translation Pattern**:
- Container paths are fixed (`/workspace`) for consistency
- Host paths computed from session context (`user_id`, `session_id`)
- Translation happens at the boundary between application and container layers
- Volume subpaths enable multi-tenancy on shared storage

### Lifecycle Management with Health Monitoring

Containers follow a managed lifecycle with verification at each stage and continuous health monitoring to detect failures.

**Startup Verification**:
- Containers must achieve sustained "running" state (multiple consecutive checks)
- Prevents race conditions where containers briefly appear running before crashing
- Startup failures captured with diagnostic logs for debugging
- Fast-fail approach: Reject containers that cannot reach stable state

**Continuous Health Monitoring**:
- Background thread periodically checks all tracked containers
- Detects external failures: manual stops, crashes, OOM kills, removals
- Handler pattern enables reactive responses to failures
- Polling interval trades detection latency vs. system load

**Automatic Cleanup**:
- Age-based cleanup removes old containers automatically
- Prevents resource accumulation from abandoned sessions
- Force cleanup on startup handles unclean shutdowns
- Port resources released synchronously with container removal

### Multi-Level Failure Detection

The system implements defense-in-depth for failure detection, combining proactive monitoring with reactive validation.

**Detection Layers**:

1. **Proactive Layer** (Health Monitoring):
   - Periodic background polling of all containers
   - Detects failures even when system is idle
   - Marks affected sessions for automatic recovery

2. **Reactive Layer** (Pre-Use Validation):
   - Status check before every operation
   - Catches failures between monitoring intervals
   - Ensures container validity immediately before use

3. **Recovery Layer** (Automatic Recreation):
   - Sessions marked ERROR automatically recreated on next use
   - Transparent to clients (idempotent operations)
   - Data preserved through persistent storage

**Failure Flow**:
```
External Failure
    ↓
Health Monitor Detection
    ↓
Session Marked ERROR
    ↓
Client Next Request
    ↓
Pre-Use Validation
    ↓
Container Recreated
    ↓
Operation Proceeds
```

This layered approach provides maximum detection latency of one monitoring interval while ensuring operations never proceed on failed containers.

### Concurrency Model

The system uses multi-threaded background processing with careful synchronization to handle concurrent operations safely.

**Thread Categories**:
- **Lifecycle Threads**: Container cleanup, session expiration
- **Monitoring Threads**: Health checks, service status monitoring
- **Execution Threads**: Command execution with timeout enforcement

**Synchronization Strategy**:
- Fine-grained locks protect shared data structures
- Copy-before-iterate pattern prevents modification-during-iteration
- All background threads are daemon threads (clean shutdown)
- Lock-free reads where possible through immutable snapshots

**Command Execution Isolation**:
- Each command execution runs in isolated process
- Timeout enforcement through process termination
- Inter-process communication via queues (not shared memory)
- Graceful degradation: SIGTERM → SIGKILL escalation

**Race Condition Prevention**:
- Sustained state checks (multiple consecutive reads) for critical transitions
- Activity updates before status checks (establishes happens-before relationships)
- Atomic state transitions through lock-protected modifications
- No assumptions about operation ordering across threads

### Service Management Architecture

Long-running processes (web servers, databases) require different lifecycle management than one-off commands. The service subsystem addresses this with background process management and health monitoring.

**Background Execution Pattern**:
- Services started via `nohup` with output redirection
- PID captured and tracked for lifecycle operations
- Process monitoring through PID checks, not container status
- Exit code captured for post-mortem analysis

**Monitoring Strategy**:
- Per-session service monitor with dedicated thread
- Periodic process existence checks via PID
- Port detection through `lsof` (dynamic port discovery)
- Status updates don't affect session activity (read-only monitoring)

**Service State Machine**:
```
STARTING → RUNNING → STOPPED (graceful)
                   → FAILED (error exit)
                   → STOPPING → STOPPED (manual stop)
```

**Lifecycle Operations**:
- **Start**: Generate script, execute with nohup, capture PID
- **Monitor**: Check PID, update ports, detect failures
- **Stop**: Graceful SIGTERM, wait, force SIGKILL if needed, fallback to pattern kill
- **Logs**: Tail stdout/stderr files, queryable by clients

**Design Rationale**:
- Services don't allocate specific ports (container has pre-allocated pool)
- System detects actual ports post-startup (flexible port binding)
- Services cleared on container failure (stale state eliminated)
- No automatic restart (client controls service lifecycle)

### Resource Management

**Port Allocation**:
- Fixed pool of ports allocated per container at creation
- Singleton port manager prevents double-allocation
- Ports released when container removed (no leaks)
- Services bind to any available port within allocation

**Resource Limits**:
- CPU quotas prevent CPU exhaustion
- Memory limits prevent OOM on host
- Configurable per-container via ContainerConfig
- Limits enforced by container runtime

**Port Management Pattern**:
- Pre-allocation at container creation (not on-demand)
- Fixed pool per container (predictable resource usage)
- Container-scoped allocation (cleanup happens naturally)
- Detection over configuration (discover actual ports post-startup)

### Security Architecture

**Defense-in-Depth Layers**:

1. **Container Isolation**:
   - Separate Linux namespaces per session
   - Non-root execution (runs as dedicated user)
   - Resource limits prevent DoS
   - Filesystem isolation through mount namespaces

2. **Network Security**:
   - Configurable port binding (localhost vs. all interfaces)
   - Optional proxy mode for restricted environments
   - Port exhaustion prevention through fixed pools
   - Service port range isolation

3. **Execution Security**:
   - Timeout enforcement prevents infinite loops
   - Working directory restrictions
   - Command execution through controlled interfaces
   - Script generation with safe path handling

4. **Access Control**:
   - Session-based isolation (no cross-session access)
   - Path translation prevents directory traversal
   - Workspace-scoped file operations
   - Session authentication at API boundary

**Proxy Mode Design**:
- Containers inherit parent's network configuration
- Enables corporate proxy compliance
- Maintains network isolation in restricted environments
- Optional feature activated via configuration

### Observability Design

Comprehensive structured logging enables debugging, auditing, and operational monitoring.

**Log Categories**:
- **System Logs**: Infrastructure events (container lifecycle, health monitoring)
- **Command Logs**: Execution events with timing and results
- **Code Logs**: Programming language execution with full context
- **Service Logs**: Long-running process lifecycle and health

**Log Enrichment Strategy**:
- Context propagation: All logs include user_id, session_id, container_id
- Timing information: Duration tracking for performance analysis
- Error context: Stack traces, diagnostic output, pre-failure state
- Correlation IDs: Trace requests across component boundaries

**Structured Logging Benefits**:
- Machine-readable format (JSON) enables automated analysis
- Queryable by multiple dimensions (user, session, event type)
- Consistent schema across all log types
- Extensible through metadata fields

**Operational Visibility**:
- Container failures logged with diagnostic information
- Service failures include stdout/stderr snapshots
- Background thread errors logged without crashing threads
- Health monitoring events tracked for trend analysis

## Key Design Patterns

### Lazy Initialization with Auto-Creation

Resources created on first use rather than eagerly. Sessions and containers created when first accessed, not when user connects.

**Benefits**:
- Reduces resource consumption (only create what's needed)
- Faster apparent response (no upfront cost)
- Natural load distribution (creation spreads over time)

**Implementation**: `ensure_container_available()` checks existence and creates if needed transparently to caller.

### Handler Registration for Event Notification

Components register callbacks with lifecycle managers to receive notifications about events (container failures, service crashes).

**Benefits**:
- Loose coupling between components
- Easy to extend with new handlers
- Event processing isolated from detection

**Pattern**:
```python
container_manager.register_external_failure_handler(
    session_manager.handle_external_container_failure
)
```

### Copy-Before-Iterate for Thread Safety

Shared collections copied before iteration to avoid modification-during-iteration errors without holding locks during processing.

**Pattern**:
```python
with self.lock:
    items_copy = list(self.items.values())
# Process without lock
for item in items_copy:
    process(item)
```

**Trade-offs**: Memory cost of copy vs. reduced lock contention.

### Singleton Pattern for Global Resources

Shared resources like PortManager use singleton pattern to ensure single source of truth.

**Rationale**: Port allocation must be globally coordinated to prevent conflicts.

**Implementation**: Module-level instance with accessor function.

### Base Class Pattern for Common Functionality

`BaseOperator` provides common functionality (session management, container checks, logging) to all operator types (shell, code, service).

**Benefits**:
- Code reuse across operator types
- Consistent patterns for container access
- Centralized session activity tracking
- Uniform error handling

### Monitoring Pattern with Read-Only Operations

Service monitoring reads status without updating session activity, preventing monitors from keeping sessions alive indefinitely.

**Key Distinction**:
- User operations: Update session activity (keep alive)
- Monitoring operations: Read-only (don't affect lifetime)

**Implementation**: Separate code paths with `update_activity` flag.

## Key Learnings and Best Practices

### Sustained State Verification

Don't trust single status checks for critical state transitions. Container appearing "running" once doesn't guarantee stability.

**Solution**: Require multiple consecutive checks before considering state stable. Prevents race conditions where containers briefly appear running before crashing.

### Separation of Detection and Recovery

Failure detection and recovery should be separate concerns handled at different layers.

- Health monitoring detects failures and updates state
- Request handling triggers recovery when needed
- Separation enables testing each independently

### Activity-Based Lifecycle Management

Resources (sessions, containers) lifetime controlled by inactivity timeout rather than absolute TTL.

**Benefits**:
- Active sessions never expire unexpectedly
- Inactive resources reclaimed automatically
- Activity tracking simple (update timestamp on use)

### Workspace Persistence Pattern

Separating workspace storage from container lifecycle enables transparent container recreation.

- Data outlives containers
- Failures recoverable without data loss
- Container becomes disposable execution environment

### Monitoring Without Side Effects

Background monitoring must not affect system state (beyond updates to monitoring data).

**Principle**: Monitoring checks status but doesn't trigger activity updates, session creation, or container recreation.

**Rationale**: Prevents monitoring from keeping resources alive indefinitely.

### Graceful Degradation in Cleanup

Cleanup operations should never crash the cleanup process. Log errors but continue processing remaining items.

**Pattern**:
```python
for item in items:
    try:
        cleanup(item)
    except Exception as e:
        log_error(e)  # Don't crash cleanup thread
        continue
```

### Timeout Enforcement Through Process Isolation

Reliable timeout enforcement requires process isolation. Cannot reliably interrupt thread executing user code.

**Solution**: Execute commands in separate process, terminate process on timeout.

### Pre-allocated Resource Pools

Pre-allocate resources (ports) at container creation rather than on-demand.

**Benefits**:
- Predictable resource usage
- Simpler allocation logic
- Natural cleanup (resources released with container)
- Prevents resource exhaustion from gradual leaks

### State Machine Clarity

Explicit state machines with well-defined transitions make system behavior predictable.

**Examples**:
- Container status: CREATING → RUNNING → STOPPED/ERROR
- Service status: STARTING → RUNNING → STOPPED/FAILED
- Session status tracks container status

Clear states enable:
- Predictable error handling
- Simplified recovery logic
- Better observability

## Scalability Considerations

**Current Design Limits**:
- One container per session (1:1 ratio)
- Background threads poll all tracked resources
- Port pool size limits concurrent containers

**Scaling Strategies**:
- Horizontal: Multiple MCP server instances with load balancing
- Vertical: Increase container resource limits
- Port pools: Separate ranges per server instance
- Monitoring: Migrate to event-based model for large container counts

**Trade-offs Accepted**:
- Polling overhead acceptable for hundreds of containers
- One container per session provides strongest isolation
- Port pre-allocation wastes some resources for predictability


## REPL

**One-line introduction.**
The REPL pattern enables an agent to iteratively execute code in a shared, stateful environment, providing immediate feedback while preserving the illusion of a continuous execution context.

### Historical perspective

The REPL (Read–Eval–Print Loop) is one of the oldest interaction models in computing. It emerged in the 1960s with interactive Lisp systems, where programmers could incrementally define functions, evaluate expressions, and inspect results without recompiling entire programs. This interactive style strongly influenced later environments such as Smalltalk workspaces and, decades later, Python and MATLAB shells.

In the context of AI systems, early program synthesis and symbolic reasoning tools already relied on REPL-like loops to test hypotheses and refine partial solutions. More recently, the rise of notebook environments and agentic systems has renewed interest in REPL semantics as a way to let models explore, test, and refine code through execution. The key research shift has been from “single-shot” code generation to **execution-aware reasoning**, where intermediate results guide subsequent steps.

### The REPL pattern in agentic systems

In an agent setting, a REPL is not merely a convenience for developers; it is a reasoning primitive. The agent alternates between generating code, executing it, observing outputs or errors, and deciding what to do next. This loop allows the agent to ground abstract reasoning in concrete runtime behavior.

A typical agent-driven REPL follows a conceptual loop:

```
while not task_complete:
    code = agent.propose_next_step(observations)
    result = execute(code, state)
    observations = observations + result
```

Two properties distinguish a production-grade REPL from a simple shell.

First, **state continuity**. Each execution step must see the effects of previous steps. Variables, user-defined functions, and imports should persist across executions so that the agent can build solutions incrementally.

Second, **isolation and safety**. Arbitrary code execution is dangerous in long-running systems. Modern REPL designs therefore decouple *logical continuity* from *physical isolation*: each execution runs in a constrained environment, yet the system reconstructs enough context to make the experience appear continuous.

### Process isolation with a persistent-state illusion

A robust REPL for agents typically executes each step in a fresh process. This avoids crashes, memory leaks, and infinite loops from destabilizing the host system. To preserve continuity, the environment state is serialized before execution and merged back afterward.

Conceptually:

```
# Before execution
snapshot = serialize(namespace_without_modules)

# In isolated process
namespace = deserialize(snapshot)
replay(imports)
replay(function_definitions)
exec(code, namespace)
delta = extract_updated_variables(namespace)

# After execution
namespace.update(delta)
```

The important constraint is that only serializable objects can persist. Modules and other non-serializable artifacts are handled indirectly, usually by tracking their source representation rather than their in-memory form.

### Import and function tracking

One subtle challenge in isolated REPL execution is that imports and function definitions do not survive process boundaries. A common solution is to treat them as *replayable declarations*.

Each execution step is analyzed to extract:

* Import statements, stored as source strings.
* Function definitions, stored as their full source.

Before running the next step, all prior imports and function definitions are re-executed in order. This works because imports are idempotent and function redefinition is generally safe.

A simplified illustration:

```
# On parsing a cell
imports += extract_imports(code)
functions += extract_functions(code)

# On next execution
for stmt in imports:
    exec(stmt, namespace)
for fn in functions:
    exec(fn, namespace)
exec(current_code, namespace)
```

This approach preserves developer- and agent-defined APIs across executions without requiring unsafe object sharing.

### Output capture as first-class data

For agents, execution output is not only for human inspection; it is input to the next reasoning step. A REPL therefore treats outputs as structured data rather than raw text.

Typical output categories include:

* Standard output and error streams.
* The value of the last expression.
* Exceptions and tracebacks.
* Structured artifacts such as tables, HTML, or images.

Separating *output storage* from *output references* is a useful best practice. Binary data (for example, images) can be stored internally and exposed via lightweight references, allowing the agent or client to fetch them on demand without bloating every response.

### Asynchronous execution and concurrency

In agent platforms, REPL execution often happens inside servers that must remain responsive. Blocking execution directly in the event loop does not scale. A common pattern is to expose an asynchronous API while offloading the actual execution to worker threads or subprocesses.

Conceptually:

```
async def execute_step(code):
    result = await run_in_worker(process_execute, code)
    return result
```

This separation allows multiple agents or sessions to execute code concurrently while preserving responsiveness.

### Sessions, persistence, and multi-user concerns

Unlike a local shell, an agent REPL usually operates in a multi-user environment. Each session must be isolated, identifiable, and recoverable. Persisting execution history and state to disk after each operation ensures that work is not lost and that sessions can be resumed after failures.

Persistence also enables secondary capabilities, such as exporting the session into a notebook format or replaying execution steps for audit and debugging.

### Best practices distilled

Several best practices consistently emerge when implementing REPLs for agents:

* Prefer process-level isolation over threads for safety and control.
* Serialize only data, not execution artifacts; replay imports and functions explicitly.
* Treat outputs as structured, inspectable objects.
* Make execution asynchronous at the API level.
* Persist state frequently to support recovery and reproducibility.
* Impose explicit limits on execution time and resource usage.

Together, these patterns allow agents to reason *through execution* without compromising system stability.

### References

1. McCarthy, J. *LISP 1.5 Programmer’s Manual*. MIT Press, 1962.
2. Abelson, H., Sussman, G. J., Sussman, J. *Structure and Interpretation of Computer Programs*. MIT Press, 1996.
3. Kluyver, T. et al. *Jupyter Notebooks – a publishing format for reproducible computational workflows*. IOS Press, 2016.
4. Chen, M. et al. *Evaluating Large Language Models Trained on Code*. arXiv, 2021.


## NL2SQL (Natural Language to SQL)

NL2SQL is the execution pattern in which an agent translates a natural language question into a validated, read-only SQL query, executes it safely, and returns results in a form suitable for both human inspection and downstream processing.

### Historical perspective

Research on translating natural language into database queries predates modern language models by several decades. Early systems in the 1970s and 1980s, such as LUNAR and CHAT-80, relied on hand-crafted rules and domain-specific grammars. These approaches demonstrated the feasibility of natural language interfaces to databases but were expensive to build and brittle outside narrowly defined schemas.

From the late 2000s onward, statistical and neural semantic parsing reframed NL2SQL as a supervised learning problem: mapping text directly to formal query representations. Public datasets such as GeoQuery and WikiSQL enabled broader experimentation, while encoder–decoder architectures improved generalization across schemas. The recent emergence of large language models shifted the emphasis again. Instead of training a specialized parser per database, modern systems condition a general-purpose model with rich schema context, examples, and execution constraints. As a result, NL2SQL has become a practical and reliable execution mode in production agentic systems, provided it is embedded in a defensively designed pipeline.

### The NL2SQL execution pattern

NL2SQL should be understood as a controlled execution pipeline rather than a simple text-to-SQL transformation. The database is a high-impact tool, and the schema is the primary grounding mechanism that constrains the model’s reasoning.

A typical workflow begins with a natural language question. Before any SQL is generated, the agent is provided with a complete, annotated schema describing tables, columns, relationships, and conventions. Using this context, the agent proposes a SQL query. That query is then passed through explicit validation steps that enforce security and correctness constraints, such as read-only access and single-statement execution. Only validated queries are executed, and results are returned in a bounded form.

This separation between reasoning, validation, and execution is what makes NL2SQL robust enough for real-world use.

### Schema as first-class context

One of the most important lessons from production NL2SQL systems is that schema preparation belongs offline. Instead of querying database catalogs dynamically at runtime, schemas are extracted once, enriched, and cached as structured metadata. This cached schema becomes the authoritative reference for all NL2SQL reasoning.

A “good” schema for agents is not minimal. It is intentionally verbose and explanatory, especially around ambiguous or overloaded fields. Confusing column names are clarified in comments, enum-like fields explicitly list their allowed values, and small samples of real data illustrate typical usage.

A representative schema fragment might look like this:

```sql
-- Table: orders
-- Purpose: Customer purchase orders in the e-commerce system

CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY,
        -- Unique identifier for each order

    status VARCHAR(20),
        -- Current lifecycle state of the order
        -- Allowed values (controlled vocabulary):
        --   pending    : order placed, not yet processed
        --   shipped    : order shipped to customer
        --   cancelled  : order cancelled before shipment

    channel VARCHAR(20),
        -- Sales channel through which the order was placed
        -- Allowed values:
        --   web, mobile_app, phone_support

    total_amount DECIMAL(10,2),
        -- Total order value in USD, including taxes

    created_at TIMESTAMP,
        -- Order creation timestamp in UTC

    customer_id INTEGER
        -- References customers.customer_id
);

-- Sample data (illustrative):
-- order_id , status   , channel     , total_amount
-- 10231    , shipped  , web         , 149.99
-- 10232    , pending  , mobile_app  ,  29.50
```

This level of annotation significantly reduces ambiguity for the agent. It also discourages the model from inventing values that do not exist in the database, a common failure mode when schemas are underspecified.

### Controlled vocabularies and query reliability

Well-designed NL2SQL schemas emphasize controlled vocabularies. Fields such as status codes, categories, types, or channels should be treated as explicit enums, even if the underlying database does not enforce them strictly.

From an agent’s perspective, controlled vocabularies serve two purposes. First, they constrain generation: when the model knows that `status` can only be one of a small, named set, it is far less likely to hallucinate invalid filter conditions. Second, they improve semantic alignment between user language and database values. Natural language phrases like “open orders” or “completed orders” can be reliably mapped to documented enum values rather than guessed strings.

Embedding enum values directly in schema comments, along with short explanations, makes this mapping explicit. In practice, this often matters more than formal database constraints, because the agent reasons over the schema text rather than the physical DDL alone.

### Query generation and validation

Even with a high-quality schema, generated SQL must be treated as untrusted input. NL2SQL systems therefore apply multiple validation layers before execution.

At a minimum, only read-only queries are permitted, and multiple statements are rejected, but this is a dangerous becaus harmfull code may still be possible. A simple syntactic validation step can catch common violations:

```python
query = query.strip()

# WARNING: This is just a quick validation step, ALWAYS rely on DB permissions for security
if not query.upper().startswith("SELECT"):
    raise ValueError("Only SELECT queries are allowed")

if query.rstrip(";").count(";") > 0:
    raise ValueError("Multiple SQL statements are not allowed")
```

Much more effective is to have "READ-ONLY" database users that are restricted by permissions at the database level. This way, even if the agent generates a malicious query, it cannot perform harmful operations.

Beyond syntactic checks, execution safeguards are typically applied. Query timeouts prevent expensive scans from monopolizing database resources, and explicit limits on result size protect both the database and the agent’s context window.

### Result handling and the workspace

Large result sets should not be injected directly into the agent context. Instead, results are written to files in a shared workspace, and only a small preview is returned.

```python
df.to_csv("workspace/results/orders_summary.csv")

preview = df.head(10)
```

The agent can then summarize the findings, show a few representative rows, and provide the file path for full inspection. This pattern keeps prompts small while preserving complete, reusable data for humans or downstream tools.

### Security and access control

Production NL2SQL systems operate under strict security constraints. Database access is typically read-only, and credentials are managed externally through a secrets manager. Queries are executed on behalf of users without exposing raw credentials to the agent.

This design supports auditing, user-specific permissions, and credential rotation without modifying agent logic. The agent interacts with the database only through a constrained execution interface.

### Architectural considerations

Successful NL2SQL systems usually adopt a layered architecture. Database-specific logic is isolated behind abstract interfaces, while business logic operates on standardized result types. This separation allows the same NL2SQL agent to work across multiple databases with minimal changes.

Equally important is minimizing runtime complexity. Schema extraction, annotation, enum detection, and example query generation are expensive operations that belong in offline pipelines. At runtime, the agent should rely entirely on cached metadata and focus on reasoning, validation, and execution.

### References

1. Woods, W. A. *Progress in Natural Language Understanding: An Application to Lunar Geology*. AFIPS Conference Proceedings, 1973.
2. Zelle, J., Mooney, R. *Learning to Parse Database Queries Using Inductive Logic Programming*. AAAI, 1996.
3. Zhong, V., et al. *Seq2SQL: Generating Structured Queries from Natural Language using Reinforcement Learning*. arXiv, 2017.
4. Yu, T., et al. *Spider: A Large-Scale Human-Labeled Dataset for Complex and Cross-Domain Semantic Parsing and Text-to-SQL Task*. EMNLP, 2018.


## Autonomous vs supervised execution, approval, rollback, and reversibility

An execution-mode pattern for tool- and code-running agents that balances autonomy with explicit control points (approvals) and safety nets (rollback / compensations) around state-changing actions.

### Historical perspective

The intellectual roots of “supervised autonomy” predate LLM agents by decades. In mixed-initiative user interfaces, researchers studied how systems should fluidly shift control between human and machine, often guided by uncertainty and the cost of mistakes (e.g., when to ask, when to act, when to defer). ([erichorvitz.com][1]) In parallel, databases and distributed systems developed a rigorous vocabulary for **commit**, **logging**, **recovery**, and **undo**, because real systems fail mid-execution and must restore consistent state. ([ACM Digital Library][2])

In the LLM era, the “agent” framing made these older ideas operational again: LLMs began to interleave reasoning with actions (tool calls, API invocations, code execution), increasing both capability and risk. ReAct popularized the now-common loop of *think → act → observe → revise*, which naturally raises the question of when actions should be allowed to mutate the world without a checkpoint. ([arXiv][3]) At the same time, human feedback became a standard technique for aligning model behavior with user intent, reinforcing a broader pattern: autonomy works best when paired with *auditable steps* and *human arbitration* at the right moments. ([arXiv][4]) More recently, systems work has begun to formalize “undo,” “damage confinement,” and *post-facto validation* as first-class abstractions for LLM actions—explicitly connecting modern agents back to transaction and recovery concepts. ([arXiv][5])

### The pattern in detail

The core idea is to treat agent execution as a **controlled transaction over an external world**. The agent can reason freely, but actions that might change state are wrapped in a small number of well-defined mechanisms:

1. **Autonomy levels (policy-driven):** not “autonomous vs supervised” as a binary, but a spectrum of allowed actions.
2. **Approval gates (pre-commit controls):** pause execution before a risky or irreversible step, obtain an explicit decision, then continue.
3. **Rollback / compensation (post-commit controls):** if something goes wrong—or if a human later rejects the outcome—undo what can be undone, and compensate what cannot.
4. **Durability and auditability:** record enough to resume, explain, and repair.

A practical way to implement this is to classify steps into **non-mutating** vs **mutating** actions (and optionally *irreversible mutating* as a special case). Recent work highlights that failures often hinge on a small number of mutating steps, motivating selective gating rather than gating everything. ([OpenReview][6])

#### 1) Model the agent as an execution loop with explicit “pause and resume”

Instead of running the agent until it prints an answer, run it until it either:

* completes, or
* reaches an action that requires external input (approval, UI-side execution, long-running job result).

Conceptually:

```python
@dataclass
class ToolCall:
    name: str
    args: dict
    call_id: str
    is_mutating: bool
    requires_approval: bool

@dataclass
class PauseForApproval:
    pending: list[ToolCall]
    # include enough context to show a human what will happen
    summary: str

def agent_step(messages, tools, policy) -> str | PauseForApproval:
    call = plan_next_tool_call(messages, tools)  # LLM decision
    meta = tool_metadata(call.name)

    if meta.is_mutating and policy.requires_approval(call):
        return PauseForApproval(
            pending=[ToolCall(call.name, call.args, call.id, True, True)],
            summary=render_human_summary(call),
        )

    result = execute_tool(call)
    messages = messages + [call_to_message(call), tool_result_message(result)]
    return continue_or_finish(messages)
```

This “pause object” is the key architectural move: it turns human-in-the-loop from an ad-hoc UI prompt into a **first-class execution outcome** that can be persisted, audited, and resumed. Many modern agent frameworks implement a variant of this via “deferred tool calls” that end a run with a structured list of pending approvals/results, then continue later when those arrive. ([Pydantic AI][7])

#### 2) Approval gates should be selective, contextual, and explainable

A good approval gate is not “approve every tool call.” Instead, make approvals depend on:

* **mutation risk:** does it change state (send, delete, purchase, write, deploy)?
* **blast radius:** how big is the possible damage (one file vs an account)?
* **reversibility:** can the action be undone cheaply and reliably?
* **sensitivity:** does it touch secrets, money, user identity, regulated data?

A simple policy sketch:

```python
def requires_approval(call: ToolCall, ctx) -> bool:
    if not call.is_mutating:
        return False

    if call.name in {"send_email", "submit_payment", "delete_record"}:
        return True

    # contextual gating: protected resources, large diffs, prod env, etc.
    if call.name == "write_file" and ctx.path in ctx.protected_paths:
        return True

    if estimate_blast_radius(call, ctx) > ctx.max_autonomous_blast_radius:
        return True

    return False
```

The human needs a crisp, non-LLM-shaped explanation: *what will be changed, where, and how to undo it.* Architecturally, store metadata alongside the paused call (reason codes, diffs, impacted resources) so the UI can render a reliable “approval card” rather than raw model text. Deferred-tool designs explicitly support attaching metadata to approval requests for exactly this purpose. ([Pydantic AI][7])

#### 3) Treat rollback as a design constraint, not an afterthought

Rollback is easy only in toy settings. In real systems:

* some actions are **naturally reversible** (edit draft → revert, create resource → delete it),
* others are **logically compensatable** (refund payment, send correction email),
* others are **irreversible** (data leaked, notification pushed to many recipients).

This leads to three complementary techniques:

**A. Undo logs / versioned state** (classic transaction recovery)
Record “before” state and/or a sequence of state transitions so you can restore consistency after partial failure. ([ACM Digital Library][2])

**B. Compensating actions (Sagas)**
For distributed or multi-step workflows, define a compensation for each step and run compensations in reverse order on failure. ([Microsoft Learn][8])

**C. Damage confinement (blast-radius limits)**
If you cannot guarantee undo, restrict what the agent is allowed to touch. Recent LLM-agent runtime work explicitly frames “undo” plus “damage confinement” as the practical path to post-facto validation. ([arXiv][5])

A minimal “saga-like” execution record:

```python
@dataclass
class StepRecord:
    call: ToolCall
    result: dict | None
    compensation: ToolCall | None  # how to undo/compensate

def run_workflow(plan: list[ToolCall]) -> list[StepRecord]:
    log: list[StepRecord] = []
    for call in plan:
        res = execute_tool(call)
        log.append(StepRecord(call=call, result=res, compensation=derive_compensation(call, res)))
    return log

def rollback(log: list[StepRecord]) -> None:
    for step in reversed(log):
        if step.compensation:
            execute_tool(step.compensation)
```

Key best practice: require tool authors (or tool wrappers) to provide a compensation strategy *at the same time* they provide the mutating tool.

#### 4) Idempotency and retries are part of “reversibility”

Approval and rollback don’t matter if your execution layer is unreliable. Two properties reduce accidental double-effects:

* **Idempotency keys:** if the agent retries, the external system should recognize “same request” and not re-apply it.
* **Replayable logs:** if the agent process dies mid-run, you can resume from the last known-good step.

This is why “durable execution” and “pause/resume” designs show up together in modern agent tool stacks: approvals and long-running jobs naturally imply persistence and resumption. ([Pydantic AI][9])

#### 5) Putting it together: supervised autonomy as a small state machine

The clean mental model is an agent runtime with a handful of states:

* **Plan / Think** (free-form, no side effects)
* **Dry-run / Preview** (compute diffs, show what would change)
* **Approve** (human or policy decision)
* **Commit** (execute mutating actions)
* **Verify** (check postconditions; detect partial failure)
* **Repair** (retry, compensate, or escalate)

This also clarifies a subtle but important point: *human-in-the-loop is not only “before commit”*. Post-facto validation becomes credible only if you have real undo/containment mechanisms behind it, as argued in GoEx-style runtime proposals. 

### References

1. Eric Horvitz. *Principles of Mixed-Initiative User Interfaces*. CHI, 1999. ([erichorvitz.com][1])
2. Theo Haerder and Andreas Reuter. *Principles of Transaction-Oriented Database Recovery*. ACM Computing Surveys, 1983. ([ACM Digital Library][2])
3. Jim Gray and Andreas Reuter. *Transaction Processing: Concepts and Techniques*. Morgan Kaufmann, 1992. ([Elsevier Shop][10])
4. Shunyu Yao et al. *ReAct: Synergizing Reasoning and Acting in Language Models*. arXiv, 2022. ([arXiv][3])
5. Long Ouyang et al. *Training Language Models to Follow Instructions with Human Feedback*. NeurIPS, 2022. ([NeurIPS Proceedings][11])
6. Reiichiro Nakano et al. *WebGPT: Browser-assisted Question-answering with Human Feedback*. arXiv, 2021. ([arXiv][12])
7. Shishir G. Patil et al. *GoEx: Perspectives and Designs Towards a Runtime for Autonomous LLM Applications*. arXiv, 2024. ([arXiv][5])
8. Microsoft Azure Architecture Center. *Saga Design Pattern*. (Documentation). ([Microsoft Learn][8])
9. Pydantic AI Documentation. *Deferred Tools: Human-in-the-Loop Tool Approval*. (Documentation). ([Pydantic AI][7])

[1]: https://erichorvitz.com/chi99horvitz.pdf?utm_source=chatgpt.com "Principles of Mixed-Initiative User Interfaces - of Eric Horvitz"
[2]: https://dl.acm.org/doi/10.1145/289.291?utm_source=chatgpt.com "Principles of transaction-oriented database recovery"
[3]: https://arxiv.org/abs/2210.03629?utm_source=chatgpt.com "ReAct: Synergizing Reasoning and Acting in Language Models"
[4]: https://arxiv.org/abs/2203.02155?utm_source=chatgpt.com "Training language models to follow instructions with human feedback"
[5]: https://arxiv.org/abs/2404.06921?utm_source=chatgpt.com "[2404.06921] GoEX: Perspectives and Designs Towards a ..."
[6]: https://openreview.net/forum?id=JuwuBUnoJk&utm_source=chatgpt.com "Small Actions, Big Errors — Safeguarding Mutating Steps ..."
[7]: https://ai.pydantic.dev/deferred-tools/ "Deferred Tools - Pydantic AI"
[8]: https://learn.microsoft.com/en-us/azure/architecture/patterns/saga?utm_source=chatgpt.com "Saga Design Pattern - Azure Architecture Center"
[9]: https://ai.pydantic.dev/?utm_source=chatgpt.com "Pydantic AI - Pydantic AI"
[10]: https://shop.elsevier.com/books/transaction-processing/gray/978-0-08-051955-5?utm_source=chatgpt.com "Transaction Processing - 1st Edition"
[11]: https://proceedings.neurips.cc/paper_files/paper/2022/file/b1efde53be364a73914f58805a001731-Paper-Conference.pdf?utm_source=chatgpt.com "Training language models to follow instructions with ..."
[12]: https://arxiv.org/abs/2112.09332?utm_source=chatgpt.com "WebGPT: Browser-assisted question-answering with human feedback"



# RAG (Retrieval-Augmented Generation)

## RAG: Introduction

**Retrieval-Augmented Generation (RAG)** is an architectural pattern that combines information retrieval systems with generative language models so that responses are grounded in external, up-to-date, and inspectable knowledge rather than relying solely on model parameters.

### Historical perspective

The core idea behind RAG predates modern large language models and can be traced back to classical information retrieval and question answering systems from the 1990s and early 2000s, where a retriever selected relevant documents and a separate component synthesized an answer. Early open-domain QA systems combined search engines with symbolic or statistical answer extractors, highlighting the separation between *finding information* and *using it*.

With the rise of neural language models, research shifted toward integrating retrieval more tightly with generation. Dense retrieval methods, such as neural embeddings for semantic search, emerged in the late 2010s and enabled retrieval beyond keyword matching. This line of work culminated in explicit Retrieval-Augmented Generation formulations around 2020, where retrieved documents were injected into the model’s context to guide generation. The motivation was twofold: reduce hallucinations by grounding outputs in real documents, and decouple knowledge updates from expensive model retraining.

### Conceptual overview of RAG

At a high level, a RAG system treats external data as a first-class component of generation. Instead of asking a model to answer a question directly, the system first retrieves relevant information from a corpus, then conditions the model on that information when generating the final answer. The language model remains a reasoning and synthesis engine, while the retriever acts as a dynamic memory.

This separation introduces a clear information workflow with two main phases: **document ingestion** and **document retrieval**, followed by **generation**.

![Image](https://www.solulab.com/wp-content/uploads/2024/07/Retrieval-Augmented-Generation-2-1024x569.jpg)

![Image](https://media.licdn.com/dms/image/v2/D4D12AQGfhRsQs5s4lA/article-inline_image-shrink_1000_1488/article-inline_image-shrink_1000_1488/0/1728125633128?e=2147483647\&t=Bj2Ev3UUFRmn5Jio99rQn2L95xJCQ8n6lWoz6HeGXto\&v=beta)

![Image](https://media.geeksforgeeks.org/wp-content/uploads/20250620114121537025/Semantic-Search-using-VectorDB.webp)

### Information workflow in RAG systems

#### Document ingestion

Document ingestion is the offline (or semi-offline) process that prepares raw data for efficient retrieval. It typically begins with collecting documents from sources such as filesystems, databases, APIs, or web crawls. These documents are then normalized into a common textual representation, which may involve parsing PDFs, stripping markup, or extracting structured fields.

Because language models have limited context windows, documents are usually divided into smaller units. This chunking step aims to balance semantic coherence with retrievability: chunks should be large enough to preserve meaning, but small enough to be selectively retrieved. Each chunk is then transformed into a numerical representation, typically via embeddings that capture semantic similarity. The resulting vectors, along with metadata such as source, timestamps, or access permissions, are stored in an index optimized for similarity search.

Ingested data is therefore not just stored text, but a structured memory that supports efficient and meaningful retrieval.

#### Document retrieval

Document retrieval is the online phase, executed at query time. Given a user query or task description, the system first produces a query representation, often using the same embedding space as the documents. This representation is used to search the index and retrieve the most relevant chunks according to a similarity or scoring function.

Retrieval rarely ends at a single step. Results may be filtered using metadata constraints, re-ranked using more expensive scoring models, or combined with other retrieval strategies such as keyword search or structured database queries. The outcome is a small set of contextually relevant passages that can fit within the model’s context window.

These retrieved chunks form the factual grounding for the generation step, effectively acting as an external, query-specific memory.

### How a simple RAG works

In its simplest form, a RAG system can be described as a linear pipeline: ingest documents, retrieve relevant chunks, and generate an answer conditioned on them. The following pseudocode illustrates the core idea, omitting implementation details:

```python
# Offline ingestion
chunks = chunk_documents(documents)
vectors = embed(chunks)
index.store(vectors, metadata=chunks.metadata)

# Online query
query_vector = embed(query)
retrieved_chunks = index.search(query_vector, top_k=5)

# Generation
context = "\n".join(chunk.text for chunk in retrieved_chunks)
answer = llm.generate(
    prompt=f"Use the following context to answer the question:\n{context}\n\nQuestion: {query}"
)
```

Despite its simplicity, this pattern already delivers most of the benefits associated with RAG. The model is guided by retrieved evidence, answers can be traced back to source documents, and updating knowledge only requires re-ingesting data rather than retraining the model.

More advanced systems extend this basic flow with richer chunking strategies, hybrid retrieval, iterative querying, and explicit evaluation loops, but the foundational pattern remains the same: retrieval first, generation second, with a clear boundary between the two.

### References

1. Lewis, P. et al. *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*. NeurIPS, 2020. [https://arxiv.org/abs/2005.11401](https://arxiv.org/abs/2005.11401)
2. Karpukhin, V. et al. *Dense Passage Retrieval for Open-Domain Question Answering*. EMNLP, 2020. [https://arxiv.org/abs/2004.04906](https://arxiv.org/abs/2004.04906)
3. Chen, D. et al. *Reading Wikipedia to Answer Open-Domain Questions*. ACL, 2017. [https://arxiv.org/abs/1704.00051](https://arxiv.org/abs/1704.00051)
4. Izacard, G., Grave, E. *Leveraging Passage Retrieval with Generative Models for Open Domain Question Answering*. EACL, 2021. [https://arxiv.org/abs/2007.01282](https://arxiv.org/abs/2007.01282)


## Embeddings

Embeddings are the mechanism that transforms raw data (text, images, audio, etc.) into numerical vectors such that semantic similarity becomes geometric proximity.

### Historical perspective

The idea of representing language as vectors predates modern deep learning. Early information retrieval systems in the 1960s and 1970s relied on sparse vector representations such as term-frequency and TF-IDF, motivated by the *distributional hypothesis*: words that appear in similar contexts tend to have similar meanings. These approaches treated language as a high-dimensional but mostly empty space, where each dimension corresponded to a vocabulary term.

In the early 2010s, research shifted toward *dense* representations that could be learned from data. Neural language models demonstrated that low-dimensional continuous vectors could encode syntactic and semantic regularities far more effectively than sparse counts. This transition laid the foundation for modern embedding-based retrieval systems and, eventually, for Retrieval-Augmented Generation.

### From word counts to vector spaces (intuition)

A simple way to build intuition is to start with word-count vectors. Consider the sentence:

> “The cat is under the table”

If the vocabulary is `{the, cat, is, under, table}`, the sentence can be represented as a vector of counts:

```
[the: 2, cat: 1, is: 1, under: 1, table: 1]
```

This representation is easy to construct and works reasonably well for keyword matching. However, it has two fundamental limitations. First, it is *sparse* and high-dimensional, which makes storage and comparison inefficient. Second, it carries no notion of meaning: “cat” and “dog” are as unrelated as “cat” and “table” unless they literally co-occur.

Modern embeddings keep the core idea—mapping language to vectors—but replace sparse counts with dense, learned representations where proximity reflects semantics rather than surface form.

![Image](https://www.researchgate.net/publication/343595281/figure/fig4/AS%3A963538206089244%401606736818940/Visualization-of-the-word-embedding-space.png)

![Image](https://www.researchgate.net/publication/350132172/figure/fig1/AS%3A1002549867970561%401616037923375/Semantic-relevance-in-the-embedding-space-a-Global-semantic-similarity-vs-local.ppm)

### Dense semantic embeddings

Dense embeddings map words, sentences, or documents into a continuous vector space (often hundreds or thousands of dimensions). In this space, semantic relationships emerge naturally: synonyms cluster together, analogies correspond to vector offsets, and related concepts occupy nearby regions.

Early influential methods include **Word2Vec**, which learns word vectors by predicting context words, **GloVe**, which combines local context with global co-occurrence statistics, and **FastText**, which incorporates character n-grams to better handle morphology and rare words. These models marked a decisive shift from symbolic counts to geometric meaning.

Conceptually, these embeddings still rely on co-occurrence statistics, but they compress them into a dense space where distance metrics such as cosine similarity become meaningful signals for retrieval.

### Transformer-based embeddings

The next major step came with transformer architectures. Models such as **BERT** introduced *contextual embeddings*: a word’s vector depends on its surrounding words, so “bank” in “river bank” differs from “bank” in “investment bank”. This resolved a long-standing limitation of earlier static embeddings.

Transformer-based embedding models typically operate at the sentence or document level for retrieval. They encode an entire passage into a single vector that captures its overall meaning. In a RAG system, these vectors are indexed in a vector database and compared against query embeddings to retrieve semantically relevant context, even when there is little lexical overlap.

A minimal illustrative snippet for text embedding might look like:

```python
# Pseudocode: embed text into a dense vector
text = "The cat is under the table"
vector = embed(text)   # returns a dense float array
```

The key point is not the API, but the abstraction: text is projected into a semantic space where similarity search is efficient and meaningful.

### Multimodal generalization

The embedding concept generalizes naturally beyond text. Multimodal models learn a *shared* vector space for different data types, allowing cross-modal retrieval. A canonical example is **CLIP**, which aligns images and text descriptions so that an image of a “red chair” is close to the text “a red chair” in the same embedding space.

This generalization is increasingly important in modern RAG systems, where documents may include text, diagrams, tables, or images. A single embedding space enables unified retrieval across modalities, simplifying system design while expanding capability.

### Embeddings in the RAG pipeline

Within a RAG architecture, embeddings serve as the semantic interface between raw data and retrieval. During ingestion, documents are converted into vectors and indexed. At query time, the user question is embedded into the same space, and nearest-neighbor search retrieves the most relevant chunks. The quality of the embeddings directly determines recall, precision, and ultimately the factual grounding of the generated answers.

### References

1. Salton, G., Wong, A., & Yang, C. S. *A Vector Space Model for Automatic Indexing*. Communications of the ACM, 1975.
2. Mikolov, T., Chen, K., Corrado, G., & Dean, J. *Efficient Estimation of Word Representations in Vector Space*. arXiv, 2013.
3. Pennington, J., Socher, R., & Manning, C. *GloVe: Global Vectors for Word Representation*. EMNLP, 2014.
4. Bojanowski, P., Grave, E., Joulin, A., & Mikolov, T. *Enriching Word Vectors with Subword Information*. TACL, 2017.
5. Devlin, J., Chang, M.-W., Lee, K., & Toutanova, K. *BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding*. NAACL, 2019.
6. Radford, A. et al. *Learning Transferable Visual Models From Natural Language Supervision*. ICML, 2021.


## Vector Databases

Vector databases are specialized data systems designed to store high-dimensional vectors and efficiently retrieve the most similar vectors to a given query.

### Historical perspective

The foundations of vector databases lie in decades of research on similarity search and nearest-neighbor problems in information retrieval and computational geometry. Early work in the 1970s and 1980s focused on exact nearest-neighbor search in low-dimensional metric spaces, but these approaches did not scale to high dimensions. As datasets grew and feature representations became more complex, research shifted toward *approximate nearest neighbor* (ANN) methods, trading exactness for dramatic gains in speed and memory efficiency.

In the late 1990s and 2000s, algorithms such as KD-trees, ball trees, and locality-sensitive hashing (LSH) emerged as practical approximations. However, the modern resurgence of vector search was driven by machine learning and deep learning, where embeddings routinely live in hundreds or thousands of dimensions. Systems like **FAISS** (2017) and later dedicated vector databases such as **Milvus** formalized these ideas into production-ready infrastructure, making vector search a core primitive for recommender systems, semantic search, and eventually Retrieval-Augmented Generation (RAG).

### How vector databases work

At a conceptual level, a vector database manages three tightly coupled concerns: storage, indexing, and similarity search. Each document, chunk, or entity is represented as a numerical vector produced by an embedding model. These vectors are stored alongside identifiers and optional metadata, but the primary operation is not key-value lookup—it is similarity search.

When a query arrives, it is first embedded into the same vector space. The database then searches for vectors that are “close” to the query vector under a chosen similarity metric. Because naïvely comparing the query to every stored vector is prohibitively expensive at scale, vector databases rely on specialized indexes that dramatically reduce the search space while preserving good recall.

In practice, a vector database behaves less like a traditional relational database and more like a search engine optimized for continuous spaces. Insertions update both raw storage and index structures; queries traverse those indexes to produce a ranked list of candidate vectors, often combined with metadata filtering before final results are returned.

### Similarity metrics

Similarity metrics define what it means for two vectors to be “close.” The choice of metric is not incidental; it encodes assumptions about how embeddings were trained and how magnitude and direction should be interpreted.

Cosine similarity measures the angle between vectors and is invariant to vector length. It is commonly used when embeddings are normalized and direction encodes semantics. Dot product is closely related and often preferred in dense retrieval models trained with inner-product objectives. Euclidean distance measures absolute geometric distance and is natural when vector magnitudes are meaningful.

Most vector databases treat the metric as a first-class configuration, because index structures and optimizations may depend on it. A mismatch between embedding model and similarity metric can significantly degrade retrieval quality, even if the infrastructure itself is functioning correctly.

### Indexing strategies

Indexing is the defining feature that distinguishes a vector database from a simple vector store. An index organizes vectors so that nearest-neighbor queries can be answered efficiently without exhaustive comparison.

Tree-based structures, such as KD-trees or ball trees, recursively partition the space and work well in low to moderate dimensions, but they degrade rapidly as dimensionality increases. Hash-based methods, particularly locality-sensitive hashing, map nearby vectors to the same buckets with high probability, enabling fast candidate generation at the cost of approximate results.

Graph-based indexes represent vectors as nodes in a graph, with edges connecting nearby neighbors. During search, the algorithm navigates the graph starting from an entry point and greedily moves toward vectors that are closer to the query. These structures scale well to high dimensions and large datasets and are widely used in modern systems.

Quantization-based approaches compress vectors into more compact representations, reducing memory footprint and improving cache efficiency. While quantization introduces approximation error, it often yields favorable trade-offs for large-scale deployments.

### Core vector database algorithms

Most production vector databases rely on a small family of ANN algorithms, often combined or layered for better performance. Hierarchical Navigable Small World (HNSW) graphs build multi-layer proximity graphs that enable logarithmic-like search behavior in practice. Inverted file (IVF) indexes first cluster vectors and then search only within the most relevant clusters. Product quantization (PQ) decomposes vectors into subspaces and encodes them compactly, enabling fast distance estimation.

These algorithms are rarely used in isolation. A common pattern is coarse partitioning (such as IVF) followed by graph-based or quantized search within partitions. The database exposes high-level configuration knobs—index type, efSearch, nprobe, recall targets—but internally orchestrates multiple algorithmic stages to balance latency, recall, and memory usage.

### Vector databases in RAG systems

In a RAG architecture, the vector database acts as the semantic memory layer. Document chunks are embedded and indexed once during ingestion, while user queries are embedded and searched at runtime. The quality of retrieval depends jointly on embedding quality, similarity metric, index choice, and search parameters. As a result, vector databases are not passive storage components but active participants in the behavior of the overall system.

Tuning a RAG system often involves iterative adjustments to vector database configuration: choosing an index that matches data scale, increasing recall at the expense of latency, or combining vector search with metadata filters to enforce structural constraints. Understanding how vector databases work internally is therefore essential for diagnosing retrieval failures and for designing robust, scalable RAG pipelines.


## Core Vector Database Algorithms

Vector databases are fundamentally concerned with solving the *nearest neighbor search* problem in high-dimensional continuous spaces. The practical design of these systems is best understood by starting from the formal problem definition and then examining how successive algorithmic relaxations make large-scale retrieval tractable.

### Formal problem definition

Let
[
\mathcal{X} = {x_1, x_2, \dots, x_n}, \quad x_i \in \mathbb{R}^d
]
be a collection of vectors embedded in a ( d )-dimensional space, and let
[
q \in \mathbb{R}^d
]
be a query vector. Given a distance function ( \delta(\cdot, \cdot) ), the *exact nearest neighbor* problem is defined as
[
\operatorname{NN}(q) = \arg\min_{x_i \in \mathcal{X}} \delta(q, x_i)
]

For cosine similarity, this becomes
[
\operatorname{NN}(q) = \arg\max_{x_i \in \mathcal{X}} \frac{q \cdot x_i}{|q| |x_i|}
]

A brute-force solution requires ( O(nd) ) operations per query, which is computationally infeasible for large ( n ). The central challenge addressed by vector database algorithms is to reduce this complexity while preserving ranking quality.

### High-dimensional effects and approximation

As dimensionality increases, distances between points concentrate. For many distributions, the ratio
[
\frac{\min_i \delta(q, x_i)}{\max_i \delta(q, x_i)} \rightarrow 1 \quad \text{as } d \rightarrow \infty
]

This phenomenon undermines exact pruning strategies and motivates *Approximate Nearest Neighbor (ANN)* search. ANN replaces the exact objective with a relaxed one:
[
\delta(q, \hat{x}) \le (1 + \varepsilon) \cdot \delta(q, x^*)
]
where ( x^* ) is the true nearest neighbor.

All modern vector database algorithms can be understood as structured approximations to this relaxed objective.

---

## Partition-based search: Inverted File Index (IVF)

The inverted file index reduces search complexity by introducing a *coarse quantization* of the vector space. Let
[
C = {c_1, \dots, c_k}
]
be a set of centroids obtained via k-means clustering:
[
C = \arg\min_{C} \sum_{i=1}^{n} \min_{c_j \in C} |x_i - c_j|^2
]

Each vector is assigned to its closest centroid:
[
\text{bucket}(x_i) = \arg\min_{c_j \in C} |x_i - c_j|
]

At query time, the search proceeds in two stages. First, the query is compared against all centroids:
[
d_j = |q - c_j|
]
Then, only the vectors stored in the ( n_{\text{probe}} ) closest buckets are searched exhaustively.

#### IVF query algorithm (pseudo-code)

```
function IVF_SEARCH(query q, centroids C, buckets B, n_probe):
    distances = compute_distance(q, C)
    selected = argmin_n(distances, n_probe)
    candidates = union(B[c] for c in selected)
    return top_k_by_distance(q, candidates)
```

This reduces query complexity to approximately
[
O(kd + \frac{n}{k} \cdot n_{\text{probe}} \cdot d)
]
which is sublinear in ( n ) for reasonable values of ( k ) and ( n_{\text{probe}} ).

---

## Vector compression: Product Quantization (PQ)

Product Quantization further reduces computational and memory costs by compressing vectors. The original space ( \mathbb{R}^d ) is decomposed into ( m ) disjoint subspaces:
[
x = (x^{(1)}, x^{(2)}, \dots, x^{(m)})
]

Each subspace is quantized independently using a codebook:
[
Q_j : \mathbb{R}^{d/m} \rightarrow {1, \dots, k}
]

A vector is encoded as a sequence of discrete codes:
[
\text{PQ}(x) = (Q_1(x^{(1)}), \dots, Q_m(x^{(m)}))
]

Distance computation uses *asymmetric distance estimation*:
[
\delta(q, x) \approx \sum_{j=1}^{m} | q^{(j)} - c_{Q_j(x)}^{(j)} |^2
]

#### PQ distance computation (pseudo-code)

```
function PQ_DISTANCE(query q, codes c, lookup_tables T):
    dist = 0
    for j in 1..m:
        dist += T[j][c[j]]
    return dist
```

Theoretical justification comes from rate–distortion theory: PQ minimizes expected reconstruction error under constrained bit budgets. Empirically, it preserves relative ordering sufficiently well for ranking-based retrieval.

---

## Hash-based search: Locality-Sensitive Hashing (LSH)

Locality-Sensitive Hashing constructs hash functions ( h \in \mathcal{H} ) such that
[
\Pr[h(x) = h(y)] = f(\delta(x, y))
]
where ( f ) decreases monotonically with distance.

For Euclidean distance, a common family is
[
h_{a,b}(x) = \left\lfloor \frac{a \cdot x + b}{w} \right\rfloor
]
with random ( a \sim \mathcal{N}(0, I) ) and ( b \sim U(0, w) ).

By concatenating hashes and using multiple tables, LSH achieves expected query complexity
[
O(n^\rho), \quad \rho < 1
]

Despite strong theoretical guarantees, LSH often underperforms graph-based methods in dense embedding spaces typical of neural models.

---

## Graph-based search: Navigable small-world graphs and HNSW

Graph-based methods model the dataset as a proximity graph ( G = (V, E) ), where each node corresponds to a vector. Search proceeds via greedy graph traversal:
[
x_{t+1} = \arg\min_{y \in \mathcal{N}(x_t)} \delta(q, y)
]

Hierarchical Navigable Small World (HNSW) graphs extend this idea by constructing multiple graph layers. Each vector is assigned a maximum level:
[
\ell \sim \text{Geometric}(p)
]

Upper layers are sparse and provide long-range connections, while lower layers are dense and preserve local neighborhoods.

#### HNSW search algorithm (simplified)

```
function HNSW_SEARCH(query q, entry e, graph G):
    current = e
    for level from max_level down to 1:
        current = greedy_search(q, current, G[level])
    return best_neighbors(q, current, G[0])
```

Theoretical intuition comes from small-world graph theory: the presence of long-range links reduces graph diameter, while local edges enable precise refinement. Expected search complexity is close to ( O(\log n) ), with high recall even in large, high-dimensional datasets.

---

## Algorithmic composition in vector databases

In practice, vector databases compose these algorithms hierarchically. A typical pipeline applies IVF to reduce the candidate set, PQ to compress vectors and accelerate distance computation, and graph-based search to refine nearest neighbors. Each stage introduces controlled approximation while drastically reducing computational cost.

This layered structure mirrors the mathematical decomposition of the nearest neighbor problem: spatial restriction, metric approximation, and navigational optimization.

---

## Implications for RAG systems

In Retrieval-Augmented Generation, these algorithms define the semantic recall boundary of the system. Errors in retrieval are often consequences of approximation layers rather than embedding quality. Understanding the mathematical and algorithmic foundations of vector databases is therefore essential for diagnosing failure modes, tuning recall–latency trade-offs, and designing reliable RAG pipelines.

Vector databases should thus be viewed not as storage engines, but as algorithmic systems grounded in decades of research on high-dimensional geometry, probabilistic approximation, and graph navigation.

---

## References

1. Indyk, P., Motwani, R. *Approximate Nearest Neighbors: Towards Removing the Curse of Dimensionality*. STOC, 1998.
2. Jégou, H., Douze, M., Schmid, C. *Product Quantization for Nearest Neighbor Search*. IEEE TPAMI, 2011.
3. Johnson, J., Douze, M., Jégou, H. *Billion-scale similarity search with GPUs*. IEEE Transactions on Big Data, 2019.
4. Malkov, Y., Yashunin, D. *Efficient and robust approximate nearest neighbor search using Hierarchical Navigable Small World graphs*. IEEE TPAMI, 2020.
5. Andoni, A., Indyk, P. *Near-optimal hashing algorithms for approximate nearest neighbor in high dimensions*. FOCS, 2006.
6. Indyk, P., Motwani, R. *Approximate Nearest Neighbors: Towards Removing the Curse of Dimensionality*. STOC, 1998.
7. Johnson, J., Douze, M., Jégou, H. *Billion-scale similarity search with GPUs*. IEEE Transactions on Big Data, 2019.
8. Malkov, Y., Yashunin, D. *Efficient and robust approximate nearest neighbor search using Hierarchical Navigable Small World graphs*. IEEE TPAMI, 2020.
9. Jégou, H., Douze, M., Schmid, C. *Product Quantization for Nearest Neighbor Search*. IEEE TPAMI, 2011.
10. [https://ai.pydantic.dev/](https://ai.pydantic.dev/)




## Document Ingestion and Chunking

Document ingestion is the process that transforms raw, heterogeneous source material into a structured, searchable representation suitable for retrieval-augmented generation.

### Historical perspective

The roots of document ingestion predate modern RAG systems by several decades. Early information retrieval systems in the 1960s and 1970s, such as vector space models and probabilistic retrieval, already required a preprocessing pipeline that normalized documents, removed noise, and represented text in a machine-processable form. Tokenization, stop-word removal, and stemming emerged in this era as practical responses to limited storage and computation.

In the 1990s and early 2000s, large-scale search engines pushed ingestion pipelines further. Web crawling, HTML parsing, boilerplate removal, and inverted index construction became standard. Research on passage retrieval and question answering in the late 1990s introduced the idea that documents should not always be treated as indivisible units, but rather decomposed into smaller spans to improve recall and precision.

The modern RAG ingestion pipeline crystallized after the widespread adoption of neural embeddings around 2018–2020. Dense vector representations made it possible to retrieve semantically similar content, but also introduced new constraints: embedding models have context length limits, and retrieval quality degrades when vectors represent overly long or heterogeneous text. As a result, document chunking became a first-class design concern, tightly coupled with ingestion rather than an afterthought.

### The document ingestion pipeline

At a conceptual level, document ingestion is a deterministic transformation pipeline. Its purpose is not to answer queries, but to prepare a stable corpus over which retrieval can operate efficiently and reproducibly.

The pipeline typically begins with **source acquisition**. Documents may originate from files (PDFs, Word documents, Markdown), databases, web pages, APIs, or generated artifacts such as logs and reports. At this stage, ingestion systems focus on completeness and traceability: every ingested unit should retain a reference to its origin, version, and ingestion time.

Next comes **parsing and normalization**. Raw formats are converted into a canonical internal representation, usually plain text plus structural annotations. For PDFs this may involve OCR; for HTML, DOM traversal and boilerplate removal; for code or structured data, language-aware parsers. Normalization also includes character encoding fixes, whitespace normalization, and the preservation of semantic boundaries such as headings, paragraphs, tables, or code blocks.

Once text is normalized, the pipeline enriches it with **metadata**. Metadata may include document-level attributes (title, author, date, source, access control labels) and section-level attributes (heading hierarchy, page number, offsets). This metadata is critical later for filtering, ranking, and provenance tracking, even if it plays no role in embedding computation itself.

Only after these steps does **chunking** occur. Chunking transforms a single normalized document into a sequence of smaller, partially overlapping or non-overlapping text segments. Each chunk becomes the atomic unit for embedding and storage in a vector database. Importantly, chunking is not merely a technical workaround for context limits; it encodes assumptions about how information should be retrieved and recombined at generation time.

Finally, each chunk is **embedded and stored**, together with its metadata and a reference back to the source document. Although embedding and storage are sometimes discussed as part of retrieval infrastructure, from a systems perspective they conclude the ingestion phase: the corpus is now ready to be queried.

### Document chunking: motivations and constraints

Chunking addresses three fundamental constraints.

First, embedding models have finite context windows. A single vector must summarize its input text, and beyond a certain length this summary becomes lossy. Chunking bounds this loss.

Second, retrieval operates at the level of chunks, not documents. If a document contains multiple unrelated topics, a single embedding will conflate them. Chunking improves semantic locality, allowing retrieval to surface only the relevant parts.

Third, generation benefits from focused context. Passing a handful of precise chunks to a language model is generally more effective than passing an entire document, even if the model could technically accept it.

These constraints imply that chunking is an information-theoretic trade-off between context completeness and semantic specificity.

### Chunking strategies

The simplest strategy is **fixed-size chunking**, where text is split every *N* tokens or characters. This approach is easy to implement and model-agnostic, but it ignores document structure. Chunks may begin or end mid-sentence, which can reduce embedding quality.

A small refinement is **fixed-size chunking with overlap**. Consecutive chunks share a window of tokens, reducing boundary effects and preserving continuity across chunks. Overlap improves recall at the cost of storage and compute.

A more semantically informed approach is **structure-aware chunking**. Here, chunk boundaries align with natural units such as paragraphs, sections, or headings, subject to a maximum size constraint. This strategy preserves discourse coherence and is especially effective for technical documents, manuals, and academic papers.

In domains where meaning depends on logical flow, **recursive or hierarchical chunking** is often used. Large sections are split into subsections, then paragraphs, and finally sentences until size constraints are satisfied. Each chunk retains metadata describing its position in the hierarchy, enabling later aggregation or re-ranking.

Finally, **semantic chunking** attempts to split text based on topic shifts rather than explicit structure. This can be implemented using lightweight similarity checks between adjacent spans. While more computationally expensive, it can produce chunks that align closely with conceptual units.

### Illustrative chunking logic

The following pseudocode illustrates structure-aware chunking with a size constraint, without committing to a specific framework or library:

```python
def chunk_document(sections, max_tokens, overlap):
    chunks = []
    for section in sections:
        buffer = []
        token_count = 0

        for paragraph in section.paragraphs:
            p_tokens = count_tokens(paragraph)

            if token_count + p_tokens > max_tokens:
                chunks.append(join(buffer))
                buffer = buffer[-overlap:] if overlap > 0 else []
                token_count = count_tokens(buffer)

            buffer.append(paragraph)
            token_count += p_tokens

        if buffer:
            chunks.append(join(buffer))

    return chunks
```

This pattern highlights two core ideas: chunking respects document structure, and size constraints are enforced incrementally rather than by naïve slicing.

### Chunking as a design decision

Chunk size, overlap, and boundary selection are not universal constants. They depend on embedding dimensionality, model context limits, expected query granularity, and downstream re-ranking strategies. In practice, ingestion pipelines often expose these parameters explicitly, treating chunking as a tunable component rather than a fixed preprocessing step.

A well-designed ingestion pipeline therefore makes chunking reproducible, auditable, and revisable. Re-chunking a corpus with different parameters should be possible without re-ingesting raw sources, enabling systematic evaluation and iteration.

### Statistical chunking (unsupervised segmentation)

Statistical chunking refers to a family of methods that segment documents into coherent units using distributional signals derived directly from the text, without relying on predefined structure or large language models.

The origins of statistical chunking can be traced to work on **text segmentation** and **topic boundary detection** in the 1990s. Early systems sought to divide long documents into topically coherent segments by exploiting lexical cohesion: the intuition that words related to the same topic tend to recur within a segment and change abruptly at topic boundaries. This line of research emerged in parallel with probabilistic language modeling and information retrieval, well before dense embeddings were available.

A canonical example is the TextTiling algorithm, which introduced the idea of sliding a window over a document and measuring similarity between adjacent blocks of text. When similarity drops sharply, a topic boundary is inferred. Later work extended this idea using probabilistic models, such as Hidden Markov Models and Bayesian topic models, to infer latent segment structure.

In a modern ingestion pipeline, statistical chunking is best understood as a **model-light, data-driven alternative** to both rule-based and LLM-based chunking. Instead of enforcing fixed sizes or asking a model to reason about discourse, the system observes how word distributions evolve across the document and places boundaries where the statistics change.

The core mechanism typically follows a common pattern. The document is first divided into small, uniform units such as sentences or short paragraphs. Each unit is represented as a vector, often using term frequency–inverse document frequency (TF–IDF) or other bag-of-words–based representations. A similarity measure is then computed between adjacent windows of units. Low similarity indicates a potential topic shift and thus a candidate chunk boundary.

Conceptually, this can be expressed as follows:

```python
units = split_into_sentences(document)
vectors = tfidf_encode(units)

boundaries = []
for i in range(1, len(vectors)):
    sim = cosine_similarity(vectors[i-1], vectors[i])
    if sim < threshold:
        boundaries.append(i)

chunks = merge_units(units, boundaries)
```

Although simplified, this illustrates the essence of statistical chunking: segmentation emerges from local changes in distributional similarity rather than explicit semantic reasoning.

Several variations exist. Some approaches smooth similarity scores over a wider window to avoid spurious boundaries. Others apply clustering algorithms, grouping adjacent units into segments that maximize intra-segment similarity. Topic-model–based approaches, such as Latent Dirichlet Allocation, infer a latent topic mixture for each unit and place boundaries where the dominant topic changes.

Statistical chunking offers a number of practical advantages. It is deterministic, reproducible, and inexpensive compared to LLM-based methods. It also scales well to very large corpora and can be applied uniformly across domains without prompt engineering. For ingestion pipelines that prioritize stability and cost control, these properties are attractive.

However, statistical methods have well-known limitations. Lexical variation can obscure topic continuity, especially when the same concept is expressed using different terminology. Conversely, shared vocabulary can mask genuine topic shifts. As a result, statistical chunking tends to perform best on expository or technical text with consistent terminology and degrades on narrative, conversational, or highly abstract material.

In contemporary RAG systems, statistical chunking is often used as a **baseline or first-pass segmentation**. Its output may be refined by structure-aware heuristics or selectively reprocessed using LLM-based chunking. This layered approach preserves the efficiency and determinism of statistical methods while allowing higher-level semantic models to intervene where they add the most value.

From an architectural perspective, statistical chunking reinforces the idea that document ingestion is a spectrum of techniques rather than a single algorithm, with different strategies occupying different points in the trade-off space between cost, interpretability, and semantic fidelity.


### LLM-based chunking (topic-aware chunking)

An increasingly common alternative to heuristic chunking is **LLM-based chunking**, where a language model is explicitly asked to segment a document into coherent topical units.

The idea of using models to guide segmentation has roots in earlier work on text segmentation and discourse modeling, such as topic segmentation with probabilistic models or lexical cohesion methods in the late 1990s. However, these approaches were limited by shallow representations and required careful feature engineering. Large language models change the landscape by providing a strong prior over discourse structure, topic boundaries, and semantic coherence, making it possible to delegate chunking decisions to the model itself.

In LLM-based chunking, the ingestion pipeline treats the document (or a large section of it) as input to a language model and asks the model to identify topical segments. Instead of enforcing a fixed token budget upfront, the model is instructed to split the text into chunks that each represent a single topic, concept, or subtask, optionally subject to soft size constraints. Each resulting chunk is then embedded and stored like any other ingestion unit.

Conceptually, this approach reframes chunking from a syntactic operation into a semantic one. The model is no longer constrained to respect paragraph or sentence boundaries alone; it can merge multiple paragraphs into one chunk if they form a single idea, or split a long paragraph if it contains multiple distinct topics. This is particularly valuable for documents with weak or inconsistent structure, such as internal reports, design documents, meeting notes, or conversational transcripts.

A typical prompt for LLM-based chunking specifies three elements. First, the **segmentation objective**, for example “split the document into self-contained topical sections suitable for retrieval.” Second, **constraints**, such as a maximum target length per chunk or a preference for fewer, larger chunks over many small ones. Third, the **output schema**, which usually requires the model to return a list of chunks with titles, summaries, or offsets to support traceability.

The following pseudocode illustrates the pattern at a high level:

```python
prompt = """
You are given a document.
Split it into coherent topical chunks.
Each chunk should cover a single topic and be self-contained.
Prefer chunks under 300 tokens when possible.

Return a JSON list of:
- title
- chunk_text
"""

chunks = llm(prompt, document_text)

for chunk in chunks:
    vector = embed(chunk["chunk_text"])
    store(vector, metadata={
        "title": chunk["title"],
        "source_doc": doc_id
    })
```

This pattern highlights a key difference from traditional chunking: the model produces **semantic boundaries**, not just text spans. Titles or summaries generated during chunking can later be reused for retrieval diagnostics, re-ranking, or citation.

LLM-based chunking has clear advantages, but it also introduces new trade-offs. Because the model is non-deterministic, chunk boundaries may vary across runs unless temperature is tightly controlled. The process is also more expensive than rule-based chunking and may require batching or hierarchical application for very large documents. Additionally, errors at ingestion time can be harder to detect, since chunk boundaries are no longer derived from explicit document structure.

For these reasons, LLM-based chunking is often used selectively. Common patterns include applying it only to long or poorly structured documents, combining it with structure-aware pre-segmentation, or using it to refine coarse chunks produced by heuristic methods. In all cases, it should be treated as a configurable ingestion strategy rather than a default replacement for simpler approaches.

From a systems perspective, LLM-based chunking reinforces a broader theme in modern RAG pipelines: ingestion is no longer a purely mechanical preprocessing step, but an opportunity to inject semantic understanding early in the lifecycle of the data.

### References

1. Salton, G., Wong, A., Yang, C. S. *A Vector Space Model for Automatic Indexing*. Communications of the ACM, 1975.
2. Voorhees, E. M., Tice, D. M. *The TREC-8 Question Answering Track Evaluation*. TREC, 1999.
3. Karpukhin, V. et al. *Dense Passage Retrieval for Open-Domain Question Answering*. EMNLP, 2020.
4. Lewis, P. et al. *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*. NeurIPS, 2020.
5. Izacard, G., Grave, E. *Leveraging Passage Retrieval with Generative Models for Open Domain Question Answering*. EACL, 2021.


## Document Retrieval

Document retrieval is the stage in a RAG system that transforms a user query into a ranked, filtered set of candidate documents or passages that are most likely to support a correct answer.

### Historical perspective

Document retrieval predates modern language models by several decades and originates in classical Information Retrieval (IR). Early systems in the 1960s–1980s focused on Boolean retrieval and term matching, culminating in the vector space model, where documents and queries were represented as sparse term-frequency vectors. The introduction of probabilistic IR models in the 1990s, most notably BM25, provided a principled scoring framework grounded in relevance estimation rather than pure geometric similarity.

From the mid-2000s onward, learning-to-rank methods reframed retrieval as a supervised ranking problem, combining many signals into a single scoring function. The 2010s introduced neural retrieval, first through latent semantic models and later through dense embeddings learned with deep neural networks. Modern RAG systems inherit all of these ideas: symbolic query rewriting from classical IR, sparse and dense retrieval models, multi-stage ranking pipelines, and explicit filtering using structured metadata. What is new is not the individual components, but their tight integration into a single retrieval pipeline optimized to serve downstream generative models.

### Conceptual overview of document retrieval

In a RAG system, document retrieval is not a single operation but a pipeline. A raw user query is progressively transformed, evaluated, and constrained until a small, high-quality context set is produced. Each stage trades recall for precision, with early stages favoring breadth and later stages favoring accuracy and relevance.

At a high level, the retrieval process consists of query interpretation and rewriting, candidate generation, scoring, re-ranking, filtering, and combination with structured constraints. While these stages can be collapsed in small systems, large-scale RAG deployments almost always implement them explicitly to control cost, latency, and quality.

### Query interpretation and rewriting

User queries are often underspecified, ambiguous, or conversational. Before retrieval, the system may rewrite the query into one or more canonical forms that are better aligned with the indexed representation of documents. This includes expanding abbreviations, resolving coreferences, normalizing terminology, or decomposing a complex question into multiple sub-queries.

In neural systems, query rewriting is frequently performed by a language model that produces a more retrieval-friendly query while preserving intent. Importantly, rewriting does not aim to answer the question, but to maximize the likelihood that relevant documents are retrieved.

```python
# Pseudocode for query rewriting
rewritten_query = rewrite_model.generate(
    original_query,
    objective="maximize retrievability"
)
```

Multiple rewritten queries may be generated to increase recall, with their results merged downstream.

### Candidate generation

Candidate generation is the first retrieval pass over the corpus. Its purpose is to retrieve a relatively large set of potentially relevant documents with high recall and low computational cost. This stage commonly uses either sparse retrieval (e.g., inverted indexes with BM25), dense vector search over embeddings, or both.

Dense retrieval maps the rewritten query into the same embedding space as documents and retrieves nearest neighbors under a similarity metric. At this stage, approximate nearest neighbor algorithms are typically used to ensure scalability.

```python
# Dense candidate generation
query_vector = embed(rewritten_query)
candidates = vector_index.search(
    query_vector,
    top_k=K_large
)
```

The output of this stage is intentionally noisy. Precision is improved later.

### Scoring and initial ranking

Each candidate document is assigned a relevance score with respect to the query. In simple systems, this score may be the similarity returned by the vector database or the BM25 score. In more advanced systems, multiple signals are combined, such as dense similarity, sparse similarity, document freshness, or domain-specific heuristics.

Formally, scoring can be expressed as a function
( s(d, q) \rightarrow \mathbb{R} ),
where ( d ) is a document and ( q ) is the rewritten query. At this stage, the goal is to produce a reasonably ordered list, not a final ranking.

### Re-ranking with cross-encoders or task-aware models

Re-ranking refines the initial ranking using more expensive but more accurate models. Instead of independently embedding queries and documents, re-rankers jointly encode the query–document pair, allowing fine-grained interaction between their tokens. This substantially improves precision, especially at the top of the ranking.

Because re-ranking is computationally expensive, it is applied only to a small subset of top candidates from the previous stage.

```python
# Re-ranking stage
top_candidates = candidates[:K_small]
reranked = reranker.score_pairs(
    query=rewritten_query,
    documents=top_candidates
)
```

The result is a high-precision ordering optimized for downstream generation rather than generic relevance.

### Filtering and constraints

Filtering removes candidates that are irrelevant or invalid given explicit constraints. These constraints often come from metadata, such as document type, access permissions, time ranges, language, or domain tags. Filtering can be applied before retrieval to reduce the search space, after retrieval to prune results, or at both stages.

In enterprise RAG systems, filtering is critical for correctness and safety. A highly relevant document that violates a constraint is worse than a less relevant but valid one.

```python
# Metadata-based filtering
filtered = [
    d for d in reranked
    if d.metadata["access_level"] <= user_access
]
```

### Combined strategies: metadata, SQL, and embeddings

Modern retrieval pipelines frequently combine symbolic and vector-based approaches. A common pattern is to use structured queries (e.g., SQL or metadata filters) to narrow the candidate set, followed by dense similarity search within that subset. This hybrid approach exploits the strengths of both paradigms: exactness and interpretability from structured filters, and semantic generalization from embeddings.

Conceptually, this corresponds to retrieving from a conditional distribution
( p(d \mid q, m) ),
where ( m ) represents structured metadata constraints.

This combination is especially powerful in domains with rich schemas, such as scientific literature, enterprise knowledge bases, or regulatory documents.

### Retrieval as a system, not a single model

A key insight in modern RAG is that retrieval quality emerges from the interaction of stages rather than from any single algorithm. Query rewriting increases recall, candidate generation ensures coverage, scoring and re-ranking enforce relevance, and filtering guarantees validity. Treating retrieval as a modular pipeline allows systematic evaluation, targeted optimization, and controlled trade-offs between cost and quality.

### References

1. Gerard Salton, Andrew Wong, and Chung-Shu Yang. *A Vector Space Model for Automatic Indexing*. Communications of the ACM, 1975.
2. Stephen Robertson and Hugo Zaragoza. *The Probabilistic Relevance Framework: BM25 and Beyond*. Foundations and Trends in Information Retrieval, 2009.
3. Omar Khattab and Matei Zaharia. *ColBERT: Efficient and Effective Passage Search via Contextualized Late Interaction*. SIGIR, 2020.
4. Lee et al. *Dense Passage Retrieval for Open-Domain Question Answering*. EMNLP, 2019.
5. Nogueira and Cho. *Passage Re-ranking with BERT*. arXiv, 2019.
6. Litschko et al. *Evaluating Hybrid Retrieval Approaches for Retrieval-Augmented Generation*. arXiv, 2023.


# Chapter 7: RAG

## Evaluating RAG Systems

**Evaluating a Retrieval-Augmented Generation (RAG) system means measuring, in a principled way, how well retrieval and generation jointly support factual, relevant, and grounded answers.**

### Historical perspective

Evaluation of RAG systems sits at the intersection of two older research traditions: information retrieval (IR) and natural language generation. Long before RAG, classical IR research in the 1960s–1990s focused on evaluating document retrieval quality using relevance judgments and set-based metrics such as precision and recall, formalized in early test collections like Cranfield and later standardized through TREC. These methods assumed a human reader as the final consumer of retrieved documents, not a generative model.

In parallel, natural language generation and question answering research developed its own evaluation practices, often relying on string-overlap metrics such as BLEU and ROUGE, or task-specific accuracy measures. With the emergence of neural open-domain QA in the 2010s, retrieval and generation began to merge, but evaluation was still typically split: retrieval was evaluated independently, and generation was evaluated against gold answers.

The first RAG-style systems, appearing around 2020 with dense retrieval and pretrained language models, exposed the limitations of this separation. A system could retrieve highly relevant documents yet fail to use them correctly, or produce fluent answers that were weakly grounded or even hallucinated. This led to a shift toward multi-level evaluation: measuring vector search quality, document retrieval effectiveness, and end-to-end answer quality together. More recent work emphasizes faithfulness, attribution, and robustness, reflecting the use of RAG in high-stakes and enterprise settings where correctness and traceability matter as much as surface-level answer quality.

---

## Evaluation layers in RAG systems

A modern RAG system is best evaluated as a pipeline with interacting components rather than a single black box. Each layer answers a different question: *are we retrieving the right things, are we selecting the right evidence, and does the final answer correctly use that evidence?*

### Metrics for vector search

Vector search evaluation focuses on the quality of nearest-neighbor retrieval in embedding space, independent of any downstream generation. The goal is to assess whether semantically relevant items are geometrically close to the query embedding.

Typical metrics are based on ranked retrieval. Recall@k measures whether at least one relevant item appears in the top-k results, which is particularly important in RAG because downstream components only see a small retrieved set. Precision@k captures how many of the retrieved items are relevant, but is often secondary to recall in early retrieval stages. Mean Reciprocal Rank (MRR) emphasizes how early the first relevant item appears, reflecting latency-sensitive pipelines. Normalized Discounted Cumulative Gain (nDCG) generalizes these ideas when relevance is graded rather than binary.

In practice, vector search evaluation requires a labeled dataset of queries paired with relevant documents or passages. These labels are often incomplete or noisy, which is why recall-oriented metrics are preferred: they are more robust to missing judgments.

```python
def recall_at_k(retrieved_ids, relevant_ids, k):
    top_k = set(retrieved_ids[:k])
    return int(len(top_k & relevant_ids) > 0)
```

This level of evaluation answers the question: *given a query embedding, does the vector index surface semantically relevant candidates?* It does not tell us whether these candidates are actually useful for answering the question.

---

### Metrics for document retrieval

Document retrieval metrics evaluate the effectiveness of the full retrieval stack, which may include query rewriting, filtering, hybrid search, and re-ranking. Unlike pure vector search, this level is concerned with the *final set of documents passed to the generator*.

The same families of metrics—Recall@k, MRR, and nDCG—are commonly used, but the unit of relevance is often more task-specific. Relevance may be defined as containing sufficient evidence to answer the question, not merely semantic similarity. This distinction is critical: a document can be topically related yet useless for grounding an answer.

Evaluation at this level often relies on human annotation or weak supervision, such as matching retrieved passages against known supporting facts. In enterprise systems, retrieval quality is frequently evaluated by measuring coverage over authoritative sources, policy documents, or curated knowledge bases.

Conceptually, this layer answers: *does the system retrieve the right evidence, in the right form, for generation?*

---

### End-to-end RAG metrics

End-to-end evaluation treats the RAG system as a whole and measures the quality of the final answer. This is the most user-visible layer and the hardest to evaluate reliably.

Traditional generation metrics such as exact match, F1, BLEU, or ROUGE are sometimes used when gold answers are available, but they are poorly aligned with the goals of RAG. A correct answer phrased differently may score poorly, while an answer that matches the gold text but is unsupported by retrieved evidence may score well.

As a result, modern RAG evaluation increasingly emphasizes three complementary properties. **Answer correctness** measures whether the answer is factually correct with respect to a reference or authoritative source. **Groundedness or faithfulness** measures whether the answer can be directly supported by the retrieved documents. **Attribution quality** measures whether the system correctly cites or points to the evidence it used.

LLM-based judges are often used to operationalize these criteria by comparing the answer against retrieved context and scoring dimensions such as correctness and support. While imperfect, this approach scales better than manual evaluation and aligns more closely with real-world usage.

```python
def judge_groundedness(answer, context):
    prompt = f"""
    Is the answer fully supported by the context?
    Answer: {answer}
    Context: {context}
    """
    return call_llm(prompt)
```

This level answers the question users actually care about: *does the system produce a correct, well-supported answer?*

---

## Measuring improvements in RAG systems

Evaluating a single snapshot of a RAG system is rarely sufficient. What matters in practice is measuring *improvement* as the system evolves.

A common baseline is a non-RAG model that answers questions without retrieval. Comparing end-to-end performance against this baseline isolates the value added by retrieval. If RAG does not outperform a strong non-RAG baseline, retrieval may be unnecessary or poorly integrated.

Ablation studies are equally important. By selectively disabling components—such as query rewriting, re-ranking, or metadata filtering—one can measure their marginal contribution. This helps avoid overfitting to complex pipelines whose benefits are not well understood.

Offline metrics should be complemented with online or human-in-the-loop evaluation where possible. User feedback, answer acceptance rates, and error analysis often reveal failure modes that are invisible to automated metrics, such as subtle hallucinations or missing caveats.

Taken together, these practices shift evaluation from a one-time score to a continuous measurement discipline, which is essential for maintaining reliable RAG systems in production.

---

## References

1. Voorhees, E. M., and Harman, D. *TREC: Experiment and Evaluation in Information Retrieval*. MIT Press, 2005.
2. Karpukhin, V., et al. *Dense Passage Retrieval for Open-Domain Question Answering*. EMNLP, 2020. [https://arxiv.org/abs/2004.04906](https://arxiv.org/abs/2004.04906)
3. Lewis, P., et al. *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*. NeurIPS, 2020. [https://arxiv.org/abs/2005.11401](https://arxiv.org/abs/2005.11401)
4. Thorne, J., et al. *Evidence-based Fact Checking with Retrieval-Augmented Models*. EMNLP, 2018.
5. Gao, T., et al. *RARR: Researching and Revising What Language Models Say, Using Language Models*. ACL, 2023. [https://arxiv.org/abs/2210.08726](https://arxiv.org/abs/2210.08726)


## Attribution, Citation, Provenance, and Truth Maintenance

Attribution in RAG systems concerns the ability to explicitly link generated statements to the source documents, data items, and transformations that produced them.

### Historical perspective

The roots of attribution and provenance long predate modern RAG systems. In database research of the late 1980s and 1990s, work on *data lineage* and *why-provenance* sought to explain how query results were derived from relational tables. This line of research matured in the early 2000s with formal models of provenance for SQL, XML, and workflow systems, motivated by scientific computing and data-intensive experiments where reproducibility was critical.

In parallel, information retrieval and question answering research emphasized citation and evidence extraction. Early open-domain QA systems in the 2000s already attempted to return answer snippets together with document references, but attribution was heuristic and weakly coupled to generation. With the rise of neural language models in the late 2010s, attribution became a central concern again, now framed around *hallucinations* and unverifiable model outputs. Retrieval-augmented generation, introduced as a way to ground language models in external knowledge, naturally revived provenance, citation, and truth maintenance as first-class design goals. Recent work focuses on making attribution machine-readable, auditable, and robust across multi-step retrieval and generation pipelines.

### Conceptual overview

In a RAG system, attribution spans the entire information flow. Documents are ingested, transformed, chunked, embedded, retrieved, possibly re-ranked, and finally used as conditioning context for generation. Each of these steps introduces opportunities to lose or blur the connection between an output token and its original source. Attribution mechanisms aim to preserve this connection explicitly.

Closely related but distinct concepts are often conflated. *Attribution* answers the question “which source supports this statement?”. *Citation* is the presentation layer, deciding how that source is exposed to users (for example, inline references or footnotes). *Provenance tracking* is the internal bookkeeping that records how data flowed through the system. *Truth maintenance* addresses how these links remain valid over time as documents, embeddings, or models change.

A robust RAG system treats these as complementary layers rather than a single feature.

### Attribution in RAG generation

At generation time, attribution typically operates at the level of retrieved chunks rather than entire documents. Each chunk carries stable identifiers and metadata inherited from ingestion. During retrieval, these identifiers are preserved and propagated alongside the text content. The generator is then constrained or guided to associate generated statements with one or more of these chunk identifiers.

A common pattern is to structure the model output so that answers and sources are produced together. This reduces ambiguity and allows downstream validation.

```python
# Conceptual output schema used by the generator
{
    "answer": "The BRCA1 gene is involved in DNA repair.",
    "sources": [
        {"doc_id": "oncology_review_2019", "chunk_id": "p3_c2"},
        {"doc_id": "genetics_textbook", "chunk_id": "ch5_c7"}
    ]
}
```

Even when the language model is free-form, the system can post-process token spans and align them with the retrieved chunks that were present in context. The key requirement is that attribution identifiers remain machine-readable and stable across the pipeline.

### References and citation strategies

Citation is the user-facing expression of attribution. In RAG systems, citation strategies range from coarse to fine-grained. Some systems attach a single list of documents supporting the entire answer. More advanced designs provide sentence-level or clause-level citations, which improves trust and debuggability but requires tighter coupling between generation and retrieval.

A critical design choice is whether citations are generated by the model or imposed by the system. Model-generated citations are flexible but error-prone, while system-enforced citations trade fluency for correctness. In practice, hybrid approaches are common: the system restricts the citation candidates to retrieved chunks, and the model selects among them.

### Provenance tracking across the pipeline

Provenance tracking is not limited to the final answer. It begins at ingestion and continues through retrieval and generation. Each transformation step should preserve or enrich provenance metadata rather than overwrite it.

A minimal provenance record typically includes the original document identifier, version information, chunk boundaries, and timestamps. More advanced systems also track the embedding model version, retrieval parameters, and re-ranking decisions. This allows engineers to answer questions such as whether an incorrect answer was caused by stale data, poor retrieval, or model behavior.

```python
# Example of a provenance record attached to a retrieved chunk
provenance = {
    "doc_id": "clinical_guidelines_v2",
    "doc_version": "2024-06-15",
    "chunk_id": "sec4_para1",
    "embedding_model": "text-embedding-v3",
    "retrieval_score": 0.87
}
```

Such records are rarely exposed to end users, but they are essential for auditing, debugging, and offline evaluation.

### Truth maintenance in evolving RAG systems

Truth maintenance addresses the fact that RAG systems are not static. Documents are updated, embeddings are recomputed, and models are replaced. Without explicit mechanisms, previously correct attributions can silently become invalid.

One approach is versioned provenance. Every answer is associated not just with a document identifier, but with a specific document version and ingestion timestamp. When the underlying data changes, the system can detect that an answer depends on outdated sources and either invalidate it or trigger regeneration.

Another approach borrows ideas from classical truth maintenance systems, where derived facts are linked to their supporting assumptions. When an assumption changes, all dependent conclusions are marked for review. In RAG, the “assumptions” correspond to retrieved chunks and their content. This framing is particularly useful in regulated or high-stakes domains, where stale answers are unacceptable.

### Practical implications

Attribution, provenance, and truth maintenance are often treated as optional add-ons in early RAG prototypes. In production systems, they quickly become essential. They enable explainability, support compliance requirements, and make systematic evaluation possible. More importantly, they turn RAG from a black-box augmentation trick into a transparent information system whose outputs can be inspected, trusted, and improved over time.

### References

1. Buneman, P., Khanna, S., Tan, W.-C. *Why and Where: A Characterization of Data Provenance*. ICDT, 2001.
2. Cheney, J., Chiticariu, L., Tan, W.-C. *Provenance in Databases: Why, How, and Where*. Foundations and Trends in Databases, 2009.
3. Lewis, P., et al. *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*. NeurIPS, 2020.
4. Rashkin, H., et al. *Increasing Faithfulness in Knowledge-Grounded Dialogue with Attributed Responses*. ACL, 2021.
5. Thorne, J., Vlachos, A. *Automated Fact Checking: Task Formulations, Methods and Future Directions*. COLING, 2018.



