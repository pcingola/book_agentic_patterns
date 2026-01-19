## Zero-shot / Few-shot Reasoning

Zero-shot and few-shot reasoning describe a model's ability to perform a task from a natural language description alone, or with only a small number of examples, without any task-specific training or fine-tuning.

At its core, zero-shot reasoning relies on the model's ability to interpret instructions expressed in natural language and map them to previously learned patterns. The model does not receive any explicit examples of input–output pairs; instead, it must infer what is being asked from descriptive cues such as task definitions, constraints, and desired output formats. This makes zero-shot reasoning highly dependent on prompt clarity and on the breadth of knowledge encoded during pre-training.

Few-shot reasoning extends this idea by embedding a small number of demonstrations directly into the prompt. These demonstrations serve as implicit specifications of the task. Rather than being rules in a formal sense, they act as contextual anchors that reduce ambiguity. The model infers a pattern from these examples and continues it when presented with a new input. Importantly, the model parameters remain fixed; adaptation happens entirely through conditioning on the prompt.

In agentic systems, zero-shot and few-shot reasoning are foundational because they enable rapid task acquisition. An agent can be instructed to perform a novel operation, adopt a new output schema, or follow a new decision heuristic simply by modifying its prompt. Few-shot examples are often used to stabilize behavior, enforce consistency, or encode domain-specific conventions without retraining. This makes such patterns especially suitable for dynamic environments where tasks change frequently or cannot be fully specified in advance.

There are, however, clear limitations. Zero-shot prompts can be brittle when tasks are underspecified, and few-shot prompts can be sensitive to example ordering, phrasing, and length. As tasks grow more complex, these patterns are often combined with other reasoning structures—such as Chain-of-Thought or ReAct—to provide additional scaffolding. Nevertheless, zero-shot and few-shot reasoning remain the entry point for most agent behaviors, defining the minimal mechanism by which a model is instructed to act.

