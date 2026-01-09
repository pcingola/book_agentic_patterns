# Chapter: Model Context Protocol (MCP)

## Introduction

**Model Context Protocol (MCP)** is an open protocol that standardizes how AI models discover, describe, and interact with external tools, resources, and structured context across long-running sessions.

### Historical perspective

The emergence of MCP is best understood as the convergence of several research and engineering threads that matured between roughly 2018 and 2024. Early neural language models were largely *stateless* and *closed*: prompts were short, tools were hard-coded, and any notion of “context” was manually injected. As models became more capable, this led to brittle integrations where each application defined its own ad-hoc conventions for tool calling, prompt templates, file access, and memory.

In parallel, earlier software ecosystems had already faced a similar problem. Language Server Protocol (LSP), introduced in the mid-2010s, demonstrated that a clean, transport-agnostic protocol could decouple editors from language tooling. Around the same time, work on agent architectures, tool-augmented language models, and function-calling APIs highlighted the need for a more principled interface between models and their environment. Research on tool use, planning, and long-horizon interaction made it clear that context could no longer be treated as a flat text prompt, but instead as a structured, evolving state.

MCP emerged from this backdrop as a unifying abstraction: rather than embedding tool logic and context management inside each application or model runtime, MCP defines a shared protocol that externalizes these concerns. The result is a system where models can operate over rich, inspectable context without being tightly coupled to any specific framework, transport, or vendor.

### Conceptual overview

At its core, MCP defines a **contract** between a *client* (typically an AI runtime or agent host) and one or more *servers* that expose capabilities. These capabilities are not limited to executable tools; they also include prompts, static or dynamic resources, and interaction patterns that guide how models request information or actions.

The key idea is that **context is first-class**. Instead of treating context as opaque text, MCP models it as a set of structured entities with explicit lifecycles. A client can discover what a server offers, reason about how to use it, and invoke those capabilities in a uniform way. This enables composition: multiple servers can be combined, swapped, or upgraded without changing the model’s internal logic.

Unlike earlier tool-calling APIs, MCP is deliberately **transport-agnostic** and **model-agnostic**. Whether the underlying connection is local, remote, synchronous, or streaming is orthogonal to the semantics of the interaction. Similarly, MCP does not assume a particular model architecture; it only specifies how context and actions are represented and exchanged.

### MCP in practice

An MCP server advertises its capabilities declaratively. A client connects, inspects those capabilities, and then decides—often with model assistance—how to use them. The protocol distinguishes between different kinds of interaction:

Tools represent callable operations with structured inputs and outputs. Prompts define reusable, parameterized instructions. Resources expose read-only or versioned data that can be incorporated into model reasoning. On the client side, additional mechanisms allow the model to request clarification, sampling decisions, or user input when uncertainty arises.

The following simplified snippet illustrates the conceptual shape of a tool definition exposed by an MCP server:

```json
{
  "name": "search_documents",
  "description": "Search indexed documents using semantic and metadata filters",
  "input_schema": {
    "query": "string",
    "filters": {
      "type": "object",
      "optional": true
    }
  }
}
```

From the client’s perspective, this definition is not just documentation. It is machine-readable context that the model can reason over: when to call the tool, how to construct valid inputs, and how to interpret outputs. The client mediates execution, ensuring that permissions, transport, and lifecycle constraints are respected.

Crucially, MCP encourages **long-lived sessions**. Context accumulates over time, resources can be updated or invalidated, and tools can be dynamically enabled or disabled. This aligns naturally with agentic systems that plan, revise, and reflect rather than producing a single response.

### FastMCP as the reference implementation

As MCP moved from a conceptual specification into real-world use, **FastMCP** emerged as the de-facto reference implementation of the protocol. Its significance was not driven by formal standardization, but by rapid adoption: FastMCP provided an early, complete, and idiomatic implementation of MCP server semantics that closely tracked the evolving specification while remaining practical for production use. By offering clear abstractions for tools, prompts, and resources—along with sensible defaults for lifecycle management, transport handling, and schema validation—it dramatically lowered the barrier to building MCP-compliant servers. As a result, many early MCP clients and examples were developed and tested against FastMCP, creating a positive feedback loop where compatibility with FastMCP effectively meant compatibility with MCP itself. Over time, this positioned FastMCP not merely as one implementation among many, but as the *behavioral reference* against which other implementations were implicitly validated, similar to how early language servers shaped expectations around LSP despite the protocol being formally independent of any single codebase.

### Why MCP matters

MCP addresses a structural problem that becomes unavoidable as systems scale: without a protocol, every agent framework reinvents its own notion of tools, memory, and context boundaries. This fragmentation makes systems harder to audit, secure, and evolve. By providing a shared vocabulary and lifecycle model, MCP enables interoperability across tools, agents, and runtimes.

Equally important, MCP shifts responsibility to the right layer. Models focus on reasoning and decision-making; servers focus on exposing well-defined capabilities; clients enforce policy, security, and orchestration. This separation mirrors successful patterns in distributed systems and is a prerequisite for building robust, enterprise-grade agent platforms.

### References

1. OpenAI et al. *Language Server Protocol*. Microsoft, 2016. [https://microsoft.github.io/language-server-protocol/](https://microsoft.github.io/language-server-protocol/)
2. Schick et al. *Toolformer: Language Models Can Teach Themselves to Use Tools*. NeurIPS, 2023.
3. Yao et al. *ReAct: Synergizing Reasoning and Acting in Language Models*. ICLR, 2023.
4. Model Context Protocol. *Getting Started: Introduction*. Model Context Protocol Documentation, 2024. [https://modelcontextprotocol.io/docs/getting-started/intro](https://modelcontextprotocol.io/docs/getting-started/intro)
