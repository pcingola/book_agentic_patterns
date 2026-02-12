## Workflows

A workflow is an explicit sequence of stages that coordinates multiple agent steps into a linear execution pipeline. Rather than a single agent reasoning end-to-end, the system is decomposed into stages with well-defined responsibilities, and an orchestrator controls the order of execution.

### The workflow pattern

At its core, a workflow defines:

* **Stages**, each representing a focused task or agent invocation.
* **Sequential transitions**, where the output of one stage feeds the next.
* **Shared state**, which accumulates intermediate artifacts across stages.

Each stage produces typed output that serves as a contract with the next stage. The orchestrator runs stages in order, passing results forward. Individual agents reason within their stage; they do not decide what happens next.

```python
# A three-stage content pipeline
outline = await outline_agent.run(topic)
draft = await draft_agent.run(outline)
final = await editor_agent.run(draft)
```

### Why workflows matter

Workflows separate *what* an agent reasons about from *how* execution progresses. This makes the system predictable and auditable: when something goes wrong, you know which stage failed and what inputs it received. Each stage can be tested, logged, and retried independently.

The tradeoff is flexibility. A workflow won't decide that an earlier stage needs re-running based on later results. For that kind of conditional control flow, graphs (covered next) are a better fit. But for pipelines where the sequence is known in advance, workflows are the simplest and most reliable orchestration pattern.

