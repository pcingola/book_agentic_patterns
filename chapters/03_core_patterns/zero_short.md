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
