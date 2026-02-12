## Introduction

Every previous chapter introduced a capability in isolation: reasoning patterns, tool use, context management, orchestration, protocols, execution infrastructure. Each was demonstrated with focused examples designed to teach one concept at a time. A real agent, however, must combine all of them. It needs tools for capabilities, skills for extensibility, a workspace for persistence, a sandbox for code execution, and sub-agents for delegation.

This chapter builds that agent. Rather than designing the final architecture upfront, we follow the same path a practitioner would: start simple, validate, then add complexity only when the current design is insufficient.

We build five progressively more capable agents, all monolithic -- a single `OrchestratorAgent` running from a Jupyter notebook with no infrastructure beyond a Python process. The first version proves that the core reasoning loop works with file and sandbox tools. Each subsequent version adds a capability layer (planning, skills, delegation, concurrent tasks) by adding tools and updating the system prompt. By the end, the agent can plan work, activate specialized skills on demand, delegate domain-specific tasks to sub-agents, and run independent tasks concurrently -- all within a single process.

The progression is deliberate. A monolithic agent that works is more valuable than a distributed system that does not. Each version adds a layer of capability, and each layer must justify itself by solving a problem the previous design could not handle.

Once the monolithic agent is complete, the chapter shifts perspective. A server requirements section consolidates the authentication, workspace, context, permissions, and compliance checklist that MCP and A2A servers must satisfy. The final section decomposes the monolithic agent into distributed MCP servers and A2A services, showing that the same architecture works whether everything runs in one process or across a network.
