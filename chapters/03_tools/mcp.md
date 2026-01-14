## MCP — Model Context Protocol

The Model Context Protocol (MCP) defines a standardized, long-lived interface through which models interact with external capabilities—tools, resources, and stateful services—using structured messages over well-defined transports.

### Historical perspective

The emergence of MCP is closely tied to the practical challenges encountered in early desktop and IDE-style agent deployments around 2023–2024. Systems such as Claude Desktop exposed local capabilities—files, shells, search indices, and custom utilities—to language models. Initially, these integrations relied on embedding tool descriptions directly into prompts and parsing structured outputs. While workable for short-lived interactions, this approach quickly showed its limits as sessions became longer, tools more numerous, and state more complex.

The architectural inspiration for MCP comes largely from the Language Server Protocol (LSP), introduced in 2016. LSP demonstrated that a clean separation between a client (the editor) and a capability provider (the language server) could be achieved using a small set of protocol primitives: JSON-RPC messaging, capability discovery, and long-running server processes. MCP generalizes this idea from *editor <-> language tooling* to *model <-> external environment*.

From a research perspective, MCP builds on earlier work in tool-augmented language models, program synthesis with external oracles, and agent architectures that distinguish reasoning from acting. As agents evolved from single-turn planners into systems expected to operate continuously—maintaining memory, monitoring processes, and reacting to external events—the lack of a stable interaction protocol became a bottleneck. MCP arises not as a new reasoning paradigm, but as the infrastructural layer required to make agentic behavior robust over time.

### From embedded tools to protocolized capabilities

Traditional tool use patterns treat tools as prompt-level constructs: schemas are injected into context, the model emits a structured call, and the runtime executes it. MCP reframes this interaction by moving tools out of the prompt and into **external servers** that expose capabilities through a shared protocol.

In this model, a tool is no longer a static definition bundled with the agent. It is a remotely exposed capability with its own lifecycle, versioning, and state. The agent connects to a server, queries what is available, and then reasons about which capabilities to invoke. This shift enables reuse across agents, reduces prompt size, and makes tool behavior observable and debuggable at the protocol level.

### Transport evolution and protocol design

MCP adopts JSON-RPC 2.0 as its core message format, inheriting well-understood semantics for requests, responses, notifications, and error handling. Early implementations favored persistent local transports, closely mirroring LSP. As MCP moved beyond desktop use cases, the protocol evolved to support web-native transports.

HTTP enables MCP servers to be deployed behind standard infrastructure, integrated with authentication and authorization systems, and scaled independently. Server-Sent Events (SSE) complement this by allowing servers to push asynchronous updates and streamed results back to the agent runtime. Crucially, MCP separates message semantics from transport details, allowing the same protocol concepts to operate across local, remote, and hybrid environments.

### MCP as a generalization of tool use

While tool invocation is a central use case, MCP generalizes the notion of “tools” into a broader concept of **capabilities**. These typically include callable functions, addressable resources such as files or datasets, reusable prompt fragments, and event streams emitted by long-running operations.

Rather than embedding all of this information in the model’s context window, the agent maintains a live connection to one or more MCP servers. The model focuses on reasoning and decision-making, while the protocol layer handles execution, retries, streaming, and persistence. A minimal interaction sequence illustrates the idea:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "capabilities/list"
}
```

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "search_documents",
    "arguments": {
      "query": "tool permissions in agent systems"
    }
  }
}
```

The model never needs to know where the tool runs or how it is implemented—only the contract exposed by the server.

### MCP as an architectural boundary

A key contribution of MCP is the introduction of a **hard architectural boundary** between models and execution environments. MCP makes explicit that models reason, but do not own stateful side effects. Files, caches, background tasks, and long-running computations live on the server side; the model interacts with them through identifiers and protocol messages.

This separation clarifies responsibilities. Tool servers evolve independently of agent prompts. Multiple agents can share the same capabilities. Security and permissioning can be enforced at the protocol boundary rather than through fragile prompt conventions. Conceptually, MCP plays a role similar to an operating system interface: it mediates access to resources without embedding implementation details into application logic.

### Capability discovery and late binding

MCP emphasizes late binding. Capabilities are discovered at connection time rather than fixed at agent construction. This allows agents to adapt to different environments, permission sets, or deployments without modification. The agent remains generic; specialization emerges from the servers it connects to.

This design is particularly important in enterprise and multi-tenant settings, where available tools may depend on user identity, organizational policy, or runtime context. By deferring binding decisions to the protocol layer, MCP avoids the combinatorial explosion that would result from statically encoding all possibilities into prompts.

### Stateful servers and long-running interactions

Another defining aspect of MCP is the explicit distinction between stateless models and stateful servers. Persistent context belongs with the server: open documents, indexed corpora, partial computations, or monitoring tasks. The model references this state indirectly, using handles or resource identifiers.

This inversion is essential for long-running agents. Instead of repeatedly expanding prompts to carry accumulated state, MCP allows agents to operate over compact references. Token usage is reduced, failure modes become clearer, and sessions can span far beyond what prompt-based approaches allow.

### Streaming, events, and non-blocking tools

MCP also generalizes beyond simple request–response interactions. Tools may emit incremental updates or asynchronous events, allowing agents to monitor progress, interleave reasoning, or react to external changes. This enables non-blocking patterns such as long-running analysis, background ingestion, or continuous observation of external systems.

At the protocol level, these interactions are explicit, rather than simulated through repeated polling or prompt reconstruction.

### Why MCP matters

MCP provides the connective tissue that allows all prior tool-use patterns to scale. Tool contracts define what can be called, permissions define whether it may be called, workspaces define where artifacts live, and MCP defines how these pieces interact over time. It does not replace tool use; it stabilizes it.

For modern agentic systems—especially those operating over long horizons, with many tools or multiple agents—MCP is less an optimization than a prerequisite for maintainable design.

### References

1. Microsoft. *Language Server Protocol Specification*. Microsoft, 2016–. [https://microsoft.github.io/language-server-protocol/](https://microsoft.github.io/language-server-protocol/)
2. Anthropic. *Model Context Protocol*. Technical documentation, 2024. [https://modelcontextprotocol.io/](https://modelcontextprotocol.io/)
3. Pydantic AI Team. *Model Context Protocol Overview*. Technical documentation, 2024. [https://ai.pydantic.dev/mcp/overview/](https://ai.pydantic.dev/mcp/overview/)
4. Schick et al. *Toolformer: Language Models Can Teach Themselves to Use Tools*. NeurIPS, 2023.
5. Yao et al. *ReAct: Synergizing Reasoning and Acting in Language Models*. ICLR, 2023.
