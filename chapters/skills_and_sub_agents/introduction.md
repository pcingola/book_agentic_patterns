## Introduction

When an agent accumulates too many tools, instructions, or conversation history, its performance degrades. The context becomes cluttered with irrelevant information, and the model struggles to focus on the task at hand. This chapter introduces three patterns that address the problem from different angles: **sub-agents** split execution across specialized agents with isolated contexts, **skills** package capability definitions so agents load instructions incrementally instead of all at once, and **tasks** wrap sub-agent execution with durable state and observation channels for long-running work.

The rest of this chapter covers sub-agents first (the runtime decomposition pattern), then the task lifecycle (durable sub-agent execution), then skills (the capability packaging pattern), and finally compares all four patterns -- including MCP and A2A -- to clarify when each is appropriate.
