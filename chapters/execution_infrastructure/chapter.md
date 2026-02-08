# Chapter: Execution Infrastructure

## Introduction

Agents that only call tools operate within a controlled vocabulary: each tool has defined inputs, outputs, and permissions. But agents that generate and execute arbitrary code -- the CodeAct pattern, REPL-based reasoning, skill scripts -- need infrastructure that constrains the execution environment itself. This chapter covers the production infrastructure for running agent-generated code safely.

The progression is from general to specific. The Sandbox section introduces the core isolation primitives (process, filesystem, network). The REPL section builds on the sandbox to create a stateful, notebook-like execution environment for iterative code exploration. The Kill Switch section addresses the data-sensitivity-driven network control problem, starting with the binary implementation used in our POC and extending to a conceptual proxy-based design for finer-grained control. The MCP Server Isolation section applies the same isolation principles to MCP servers, and the Skill Sandbox section handles the distinct trust model of developer-authored skill scripts.

## Sections

[Sandbox](./sandbox.md)

[REPL](./repl.md)

[Kill Switch](./kill_switch.md)

[MCP Server Isolation](./mcp_server_isolation.md)

[Skill Sandbox](./skill_sandbox.md)

[Hands-On: MCP Server Isolation](./hands_on_mcp_isolation.md)

## References

[References](./references.md)
