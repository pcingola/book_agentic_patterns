## Introduction

When an agent accumulates too many tools, instructions, or conversation history, its performance degrades. The context becomes cluttered with irrelevant information, and the model struggles to focus on the task at hand. Two patterns address this problem from different angles.

**Sub-agents** split execution. Instead of one agent doing everything, a coordinator delegates to specialized agents, each with its own focused context. The summarizer agent sees only summarization instructions. The risk analyst sees only risk assessment prompts. Neither is distracted by the other's concerns.

**Skills** split capability definitions. Instead of loading all instructions upfront, capabilities are packaged so agents discover what exists (cheap), activate what they need (medium cost), and load detailed resources only when required (expensive). The agent starts lean and adds context incrementally.

These patterns often work together. A coordinator agent might delegate a task to a sub-agent, and that sub-agent activates a skill to perform its work. The sub-agent provides context isolation; the skill provides packaged instructions and tools.

The rest of this chapter covers sub-agents first (the runtime decomposition pattern), then skills (the capability packaging pattern), and finally compares both to MCP and A2A to clarify when each is appropriate.
