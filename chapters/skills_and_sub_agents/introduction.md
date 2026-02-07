## Introduction

When an agent accumulates too many tools, instructions, or conversation history, its performance degrades. The context becomes cluttered with irrelevant information, and the model struggles to focus on the task at hand. Two patterns address this problem from different angles.

**Sub-agents** split execution. Instead of one agent doing everything, a coordinator delegates to specialized agents, each with its own focused context. The summarizer agent sees only summarization instructions. The risk analyst sees only risk assessment prompts. Neither is distracted by the other's concerns.

**Skills** split capability definitions. Instead of loading all instructions upfront, capabilities are packaged so agents discover what exists (cheap), activate what they need (medium cost), and load detailed resources only when required (expensive). The agent starts lean and adds context incrementally.

**Tasks** add lifecycle management. Sub-agents are fire-and-forget -- the coordinator calls, awaits, and moves on. When work is long-running, needs observation, or should survive restarts, the task lifecycle wraps sub-agent execution with durable state, event streams, and explicit control (polling, streaming, cancellation).

These patterns often work together. A coordinator agent might delegate a task to a sub-agent, and that sub-agent activates a skill to perform its work. The sub-agent provides context isolation; the skill provides packaged instructions and tools. The task lifecycle adds durability and observability when needed.

The rest of this chapter covers sub-agents first (the runtime decomposition pattern), then the task lifecycle (durable sub-agent execution), then skills (the capability packaging pattern), and finally compares all to MCP and A2A to clarify when each is appropriate.
