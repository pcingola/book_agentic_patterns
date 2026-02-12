## Long-running tasks and async execution

Long-running tasks and asynchronous execution allow agents to pursue goals that extend beyond a single interaction by persisting state, delegating work, and resuming execution in response to events.

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

The concepts introduced here are implemented in later chapters. The [Skills, Sub-Agents & Tasks chapter](../skills_and_sub_agents/chapter.md) covers sub-agent delegation, task lifecycle management with durable state, and the task broker that coordinates background execution. The [The Complete Agent chapter](../the_complete_agent/chapter.md) brings these patterns together into a unified agent that orchestrates sub-agents, tasks, and event-driven coordination.

