## First Steps

The five agents in this chapter share a common construction pattern: load a system prompt, collect tools from existing modules, and pass both to PydanticAI. Each version adds tools or changes the prompt -- the agent infrastructure stays the same.

The first two versions establish the foundation. The Coder (V1) combines file operations and a Docker sandbox into the simplest useful agent: one that can write code and execute it. The Planner (V2) adds todo tools and a plan-first workflow, turning a reactive write-execute loop into a structured sequence of tracked steps. Both are built from plain tool lists and a single `get_agent()` call -- no orchestrator, no configuration file, no skills.

This is deliberate. The goal is to verify that the core reasoning loop works before introducing progressive disclosure (V3), delegation (V4), or concurrency (V5). Each of those layers solves a problem that only becomes visible once the simpler agent is running.
