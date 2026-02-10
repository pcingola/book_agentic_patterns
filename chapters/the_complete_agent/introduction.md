## Introduction

Every previous chapter introduced a capability in isolation: reasoning patterns, tool use, context management, orchestration, protocols, execution infrastructure. Each was demonstrated with focused examples designed to teach one concept at a time. A real agent, however, must combine all of them. It needs tools and MCP servers for capabilities, A2A for delegation, skills for extensibility, a workspace for persistence, a sandbox for code execution, context engineering to stay within token limits, and a user interface so someone can actually use it.

This chapter builds that agent. Rather than designing the final architecture upfront, we follow the same path a practitioner would: start simple, validate, then add complexity only when the current design is insufficient.

The first step is a monolithic agent -- a single `Agent` instance with tools registered directly, runnable from a Jupyter notebook with no infrastructure beyond a Python process. This version is deliberately constrained. It proves that the core reasoning loop works, that the tools compose correctly, and that the agent can accomplish real tasks. It also establishes a baseline: if something breaks later, we know the problem is in the infrastructure layer, not the agent logic.

The second step decomposes the monolith. Tools that benefit from isolation move behind MCP servers. Specialist capabilities become A2A sub-agents with their own context windows. The single agent becomes a coordinator that delegates rather than doing everything itself. The `OrchestratorAgent` class manages this composition: it connects to MCP servers, fetches A2A agent cards, registers delegation tools, and builds a combined system prompt -- all behind an async context manager so the coordinator code itself remains simple.

The third step adds a user interface. The AG-UI protocol turns the agent into a backend that any compliant frontend can connect to, with streaming events for text, tool calls, and state updates. This is the point where the system becomes usable by someone other than the developer who built it.

The progression is deliberate. A monolithic agent that works is more valuable than a distributed system that does not. Each step adds a layer of indirection, and each layer must justify itself by solving a problem the previous design could not handle.
