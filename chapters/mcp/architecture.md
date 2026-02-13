## Architecture

This section describes the architectural structure of the Model Context Protocol (MCP): how clients and servers coordinate over a well-defined lifecycle, how responsibilities are split across components, and how transport, authorization, and security concerns are handled in a principled way. The abstract architecture defined in the specification is concretely realized in implementations such as **FastMCP** and in the MCP integration patterns described by **Pydantic-AI**, which together provide practical guidance on how these concepts are applied in real systems.

#### Conceptual overview

At its core, MCP defines a **contract** between a *client* (typically an AI runtime or agent host) and one or more *servers* that expose capabilities. These capabilities are not limited to executable tools; they also include prompts, static or dynamic resources, and interaction patterns that guide how models request information or actions.

The key idea is that **context is first-class**. Instead of treating context as opaque text, MCP models it as a set of structured entities with explicit lifecycles. A client can discover what a server offers, reason about how to use it, and invoke those capabilities in a uniform way.

An MCP server advertises its capabilities declaratively. A client connects, inspects those capabilities, and then decides -- often with model assistance -- how to use them. The protocol distinguishes between different kinds of interaction: tools represent callable operations with structured inputs and outputs, prompts define reusable parameterized instructions, and resources expose read-only or versioned data that can be incorporated into model reasoning. On the client side, additional mechanisms allow the model to request clarification, sampling decisions, or user input when uncertainty arises.

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

From the client's perspective, this definition is not just documentation. It is machine-readable context that the model can reason over: when to call the tool, how to construct valid inputs, and how to interpret outputs. The client mediates execution, ensuring that permissions, transport, and lifecycle constraints are respected.

Crucially, MCP encourages **long-lived sessions**. Context accumulates over time, resources can be updated or invalidated, and tools can be dynamically enabled or disabled. This aligns naturally with agentic systems that plan, revise, and reflect rather than producing a single response.

#### FastMCP

As MCP moved from a conceptual specification into real-world use, **FastMCP** became the most well-known server implementation of the protocol. FastMCP provided an early, complete, and idiomatic implementation of MCP server semantics that closely tracked the evolving specification while remaining practical for production use. By offering clear abstractions for tools, prompts, and resources -- along with sensible defaults for lifecycle management, transport handling, and schema validation -- it dramatically lowered the barrier to building MCP-compliant servers. FastMCP was later integrated into the official MCP Python SDK, making it available as `mcp.server.fastmcp` alongside the standalone `fastmcp` package. The examples in this chapter use FastMCP for server-side code.

#### Why MCP matters

MCP addresses a structural problem that becomes unavoidable as systems scale: without a protocol, every agent framework reinvents its own notion of tools, memory, and context boundaries. This fragmentation makes systems harder to audit, secure, and evolve. By providing a shared vocabulary and lifecycle model, MCP enables interoperability across tools, agents, and runtimes.

Equally important, MCP shifts responsibility to the right layer. Models focus on reasoning and decision-making; servers focus on exposing well-defined capabilities; clients enforce policy, security, and orchestration. This separation mirrors successful patterns in distributed systems and is a prerequisite for building robust, enterprise-grade agent platforms.

#### Lifecycle

The MCP lifecycle defines the ordered phases through which a client–server session progresses. Rather than treating connections as ad-hoc request/response exchanges, MCP makes lifecycle transitions explicit, enabling both sides to reason about capabilities, permissions, and state.

The lifecycle begins with initialization. The client establishes a connection and negotiates protocol compatibility and supported features. FastMCP exposes this phase explicitly, ensuring that capability discovery and validation occur once per session. In Pydantic-AI’s MCP integration, this boundary cleanly separates agent reasoning from external interaction: no domain actions occur until initialization succeeds.

Once initialized, the session enters the active phase. During this phase, the client may invoke prompts, access resources, request sampling, or engage in elicitation flows, strictly within the capabilities that were negotiated. Implementations emphasize that this phase is stateful. FastMCP maintains session-scoped context across multiple interactions, while Pydantic-AI reinjects MCP responses into the model context over successive turns, enabling iterative and reflective agent behavior.

The lifecycle ends with shutdown. Either side may terminate the session, at which point in-flight operations are resolved, resources are released, and all session context is discarded. Both FastMCP and Pydantic-AI documentation stress that explicit teardown is essential for long-running or autonomous agents, where leaked state or lingering permissions would otherwise accumulate.

#### Server

An MCP server is the authoritative boundary between models and external systems. Architecturally, it exposes structured capabilities while enforcing protocol rules, authorization, and isolation.

FastMCP provides a reference server architecture that closely mirrors the MCP specification. The server is typically organized in layers: a transport layer for message delivery, a protocol layer that validates messages and enforces lifecycle constraints, and an application layer that implements domain-specific logic. This separation ensures that business logic is never directly exposed to unvalidated client input.

A defining characteristic of MCP servers is declarative capability exposure. Instead of executing arbitrary instructions from a client, the server advertises what it can do, under which constraints, and with which inputs and outputs. Pydantic-AI adopts the same principle in its MCP guidance, framing the server as a controlled execution boundary rather than a general command interface.

Conceptually, server request handling follows a pattern such as:

```python
def handle_message(message, session):
    enforce_lifecycle(session)
    validate_message_schema(message)
    authorize(message, session)
    dispatch(message, session)
```

The value of this structure lies in the invariant it enforces: all access to external systems is mediated by protocol rules and session state.

#### Client

The MCP client orchestrates interactions on behalf of a model or agent. While the server defines what is possible, the client decides what to request, when to request it, and how to integrate the results back into the agent’s reasoning loop.

Clients maintain session state, tracking negotiated capabilities, permissions, and accumulated context. In both FastMCP examples and Pydantic-AI integrations, the client acts as a policy and coordination layer, translating model intents into MCP requests and injecting structured responses back into the model context.

This design keeps protocol mechanics out of the model itself. Pydantic-AI explicitly promotes this separation, treating MCP as the execution boundary where agent decisions are realized in the external world.

A typical client flow is:

```python
session = connect_to_server()
capabilities = session.initialize()

if capabilities.supports_resources:
    data = session.request_resource("example")
    model_context.add(data)
```

The explicit capability check, emphasized in both FastMCP and Pydantic-AI documentation, is central to MCP’s robustness across heterogeneous servers.

#### Transport

MCP deliberately decouples protocol semantics from transport mechanisms. The specification defines message structure and behavior independently of how messages are transmitted.

FastMCP demonstrates this abstraction by supporting multiple transports, including standard input/output for local tool servers and HTTP-based transports for remote services. Pydantic-AI’s MCP documentation similarly treats transport as an implementation detail, allowing the same agent logic to operate unchanged across local development environments and production deployments.

Architecturally, this means transport can evolve without affecting higher-level agent logic, as long as MCP message semantics are preserved.

#### Authorization

Authorization in MCP is embedded directly into the protocol flow rather than being handled entirely out of band. Both the specification and FastMCP documentation emphasize fine-grained, capability-level authorization.

During initialization, clients authenticate and establish identity. During the active phase, every request is checked against the permissions associated with the session. FastMCP enforces these checks as part of request dispatch, while Pydantic-AI highlights authorization as a first-class concern when integrating MCP into agent runtimes.

This approach enables dynamic authorization. Permissions may depend on session context, negotiated features, or prior actions, supporting patterns such as staged access, scoped credentials, or human-approved escalation.

#### Security

Security in MCP is an architectural property that emerges from explicit lifecycle management, declarative capabilities, and strict validation.

A core principle is least privilege. Clients can only invoke capabilities that the server has explicitly advertised, and only within the bounds of the current session. FastMCP documentation frames MCP servers as containment boundaries, while Pydantic-AI recommends exposing narrowly scoped operations rather than general execution primitives.

Isolation is equally important. Sessions are isolated from one another, and context is never shared across lifecycles. FastMCP treats session state as ephemeral, and Pydantic-AI guidance reinforces that MCP contexts should be discarded at the end of an interaction.

Finally, defensive validation is pervasive. Messages are schema-validated, lifecycle transitions are enforced, and unexpected inputs are rejected early. These practices are critical when MCP clients may be driven by partially autonomous agents.

