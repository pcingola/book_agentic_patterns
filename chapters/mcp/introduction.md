## Introduction

The Tools chapter introduced MCP as a protocol for externalizing tool definitions to separate servers, moving from hard-coded tool functions to a standardized discovery and invocation interface. This chapter examines the protocol in depth: its architecture, lifecycle, transport mechanics, and the full range of capabilities it exposes beyond simple tool calls.

**Model Context Protocol (MCP)** is an open protocol that standardizes how AI models discover, describe, and interact with external tools, resources, and structured context across long-running sessions. Unlike earlier tool-calling APIs, MCP is deliberately transport-agnostic and model-agnostic: whether the underlying connection is local, remote, synchronous, or streaming is orthogonal to the semantics of the interaction. This enables composition -- multiple servers can be combined, swapped, or upgraded without changing the model's internal logic.

The chapter begins with the architecture (lifecycle, client-server separation, transport, and authorization), then examines tools as MCP's core execution boundary, and concludes with the full feature set: prompts, resources, sampling, and elicitation.
