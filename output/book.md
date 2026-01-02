# Core Agentic patterns

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



## MCP

* MCP motivation and scope: Why a standardized protocol is needed to connect agents with tools, data, and context.

  * [https://www.anthropic.com/news/model-context-protocol](https://www.anthropic.com/news/model-context-protocol)
  * [https://modelcontextprotocol.io/docs/learn/introduction](https://modelcontextprotocol.io/docs/learn/introduction)

* MCP architectural model: Host, client, and server roles and how they map onto an agent execution loop.

  * [https://modelcontextprotocol.io/docs/learn/architecture](https://modelcontextprotocol.io/docs/learn/architecture)

* Protocol layers: Separation between the JSON-RPC data model and transport mechanisms.

  * [https://modelcontextprotocol.io/specification/2025-06-18/basic](https://modelcontextprotocol.io/specification/2025-06-18/basic)
  * [https://www.jsonrpc.org/specification](https://www.jsonrpc.org/specification)

* Lifecycle and capability negotiation: Initialization, versioning, and feature discovery for interoperable agents.

  * [https://modelcontextprotocol.io/specification/2025-06-18/basic/lifecycle](https://modelcontextprotocol.io/specification/2025-06-18/basic/lifecycle)

* Tools primitive: How agents invoke side-effectful actions via typed, schema-defined tools.

  * [https://modelcontextprotocol.io/specification/2025-06-18/server/tools](https://modelcontextprotocol.io/specification/2025-06-18/server/tools)

* Resources primitive: Supplying structured, addressable context (files, data, memory) to agents.

  * [https://modelcontextprotocol.io/specification/2025-06-18/server/resources](https://modelcontextprotocol.io/specification/2025-06-18/server/resources)

* Prompts primitive: Reusable prompt templates as shared cognitive scaffolding.

  * [https://modelcontextprotocol.io/specification/2025-06-18/server/prompts](https://modelcontextprotocol.io/specification/2025-06-18/server/prompts)

* Transport choices: stdio vs HTTP/Streamable HTTP and their implications for deployment and scaling.

  * [https://modelcontextprotocol.io/specification/2025-06-18/basic/transports](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports)

* Security and authorization: Threat boundaries, safe server design, and OAuth 2.1 for remote access.

  * [https://modelcontextprotocol.io/specification/2025-06-18/basic/security_best_practices](https://modelcontextprotocol.io/specification/2025-06-18/basic/security_best_practices)
  * [https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization](https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization)

* Practical agent integration: How planners and executors use MCP clients in real agent systems.

  * [https://modelcontextprotocol.io/docs/learn/client-concepts](https://modelcontextprotocol.io/docs/learn/client-concepts)



