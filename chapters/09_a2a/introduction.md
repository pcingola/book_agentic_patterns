## Introduction

A2A (Agent2Agent) is an application-layer protocol that standardizes how autonomous agents discover each other, exchange messages, and coordinate work as tasks over HTTP(S), enabling cross-framework and cross-organization interoperability.

### Historical perspective

The idea of agents communicating through standardized messages predates LLM-based systems by decades. In the early 1990s, distributed AI research emphasized interoperability among heterogeneous agents via explicit communication “performatives” rather than bespoke point-to-point integrations. KQML is a canonical artifact of this period: a message language/protocol intended to let independent systems query, inform, and coordinate knowledge exchange. In the late 1990s, efforts such as FIPA ACL pushed further toward standardizing agent communication semantics and interaction patterns, aiming to make “agent societies” feasible across implementations.

Many of these early standards were conceptually influential but operationally heavy: they assumed relatively structured symbolic agents, and they predated today’s ubiquitous web stack. The 2020s reintroduced the need for inter-agent interoperability under different constraints: LLM agents are often deployed as services, they must cooperate across vendor boundaries, and they increasingly manage long-running tasks and artifacts. Modern web primitives (HTTP(S), JSON serialization) and lightweight RPC framing (JSON-RPC 2.0) make it practical to standardize inter-agent communication without requiring a shared runtime.

A2A is best read as a pragmatic continuation of this line of work: instead of attempting to standardize internal reasoning or cognitive semantics, it standardizes the *external contract* for discovery, task-oriented interaction, and delivery of results.

### What is A2A

A2A defines how one agent (a “client agent”) communicates with another agent (a “remote agent”) over HTTP(S), using JSON-RPC 2.0 envelopes. The remote agent is intentionally treated as opaque: A2A does not prescribe how the remote agent plans, calls tools, or maintains internal state. What it *does* prescribe is how the client creates and advances work, and how the remote agent reports progress and returns outputs in a predictable, interoperable format.

This choice makes A2A suitable for delegation patterns that show up in real systems. A coordinator agent can discover specialized agents (for billing, travel planning, literature review, data cleaning), select one based on declared capabilities, and then initiate and track a task. The client doesn’t need a shared framework with the remote agent; it needs only the protocol contract.

The protocol’s use of JSON-RPC is deliberately conservative. JSON-RPC provides the framing for request/response correlation (IDs), method invocation, and standardized error handling, while A2A defines the domain concepts on top: agent metadata, tasks, message structures, and artifacts.

### Key concepts

A2A’s main abstractions are designed to match how multi-agent work actually unfolds over time.

An **Agent Card** is the discovery and capability surface: a machine-readable document published by a remote agent that describes who it is, where its endpoint is, which authentication schemes it supports, and what capabilities and skills it claims. This supports “metadata-first” routing and policy checks before any work begins.

A **Task** is a stateful unit of work with its own identity and lifecycle. Tasks exist to support multi-turn collaboration and long-running operations, so an interaction does not have to fit into one synchronous request/response. Instead, the client can start a task, send additional messages, and retrieve updates or results later.

**Messages** are how conversational turns are exchanged, and they are structured as **parts** so that text, structured data, and file references can be represented consistently. **Artifacts** are the concrete outputs attached to a task—documents, structured results, or other deliverables that can be stored, forwarded, audited, or fed into downstream workflows.

A useful mental model is: **Agent Card** answers “who are you and what can you do?”, **Task** answers “what unit of work are we coordinating?”, **Messages** carry the interaction, and **Artifacts** are the outputs worth persisting.

### Agent discovery

A2A discovery is built around retrieving the Agent Card. A common mechanism is a well-known URL under the agent’s domain (aligned with established “well-known URI” conventions), allowing clients to probe domains deterministically. Discovery is intentionally explicit: clients can validate capabilities, authentication requirements, and declared skills before initiating a task, and systems can log discovery metadata for audit and governance.

Conceptual snippet:

```python
import requests

def discover_agent_card(domain: str) -> dict:
    url = f"https://{domain}/.well-known/agent-card.json"
    r = requests.get(url, timeout=5)
    r.raise_for_status()
    return r.json()

card = discover_agent_card("billing.example.com")
# Use: card["skills"], card["authentication"], card["capabilities"], card["url"]
```

This “metadata-first” approach matters operationally: it enables capability matching, policy gating (e.g., only delegate to agents with certain auth), and safer orchestration decisions *before* sending sensitive task content.

### A2A and MCP

A2A and MCP are complementary layers rather than competing protocols. MCP standardizes how agents interact with tools and resources (structured inputs/outputs, tool schemas, permission boundaries). A2A standardizes how agents interact with *other agents* as autonomous peers (discovery, task lifecycle, messaging, artifact delivery).

A common composition is **A2A for delegation, MCP for tool-use**. A coordinator uses A2A to delegate a task to a specialist agent. The specialist agent, while executing the task, may rely on MCP internally to access databases, file systems, execution sandboxes, or enterprise services. When the specialist completes work (or makes partial progress), it returns results back to the coordinator as A2A messages and artifacts. This separation keeps each protocol focused: A2A doesn’t need to understand tool schemas, and MCP doesn’t need to standardize multi-agent collaboration.

### Touchpoints from Pydantic-ai and FastMCP ecosystems

The Pydantic ecosystem documents A2A as a practical interoperability layer and provides Python tooling to expose agents as A2A servers and to build clients that can discover agents, initiate tasks, and consume artifacts—without requiring the agent’s internal design to be rewritten around protocol internals. The emphasis is on preserving your existing agent architecture while making the boundary interoperable.

FastMCP, meanwhile, is often used as a pragmatic deployment unit for MCP tool servers. In practice, this leads to a common layered architecture: A2A connects agents across boundaries; MCP connects agents to tools/resources; and FastMCP-style servers host the tool endpoints that agents call. Bridging components can translate between A2A and MCP where needed (for example, to let an A2A-facing agent expose or consume MCP-backed capabilities behind the scenes).

A minimal task invocation at the wire level (illustrative, independent of any specific framework) looks like this:

```json
{
  "jsonrpc": "2.0",
  "id": "req_123",
  "method": "tasks/send",
  "params": {
    "message": {
      "role": "user",
      "parts": [
        { "kind": "text", "text": "Reconcile invoice #4812 and explain discrepancies." }
      ]
    }
  }
}
```

The important point is not the method name per se, but the design: JSON-RPC provides the envelope; A2A defines the task/message/artifact semantics; and implementations can remain diverse behind the boundary.


## References

1. Tim Finin, Rich Fritzson, Don McKay, Robin McEntire. *KQML – A Language and Protocol for Knowledge and Information Exchange*. AAAI Workshop, 1994. [https://www.aaai.org/Papers/Workshops/1994/WS-94-03/WS94-03-003.pdf](https://www.aaai.org/Papers/Workshops/1994/WS-94-03/WS94-03-003.pdf)
2. KQML Advisory Group. *An Overview of KQML: A Knowledge Query and Manipulation Language*. Technical report, 1992. (Commonly circulated via early KQML/UMBC technical report archives.)
3. FIPA. *FIPA ACL Message Structure Specification*. FIPA, 2002. [https://www.fipa.org/specs/fipa00061/SC00061G.html](https://www.fipa.org/specs/fipa00061/SC00061G.html)
4. JSON-RPC Working Group. *JSON-RPC 2.0 Specification*. jsonrpc.org, 2010. [https://www.jsonrpc.org/specification](https://www.jsonrpc.org/specification)
5. Pydantic. *A2A (Agent2Agent)*. ai.pydantic.dev, (latest). [https://ai.pydantic.dev/a2a/](https://ai.pydantic.dev/a2a/)
6. A2A Protocol. *What is A2A?* a2a-protocol.org, (latest). [https://a2a-protocol.org/latest/topics/what-is-a2a/](https://a2a-protocol.org/latest/topics/what-is-a2a/)
7. A2A Protocol. *Key Concepts*. a2a-protocol.org, (latest). [https://a2a-protocol.org/latest/topics/key-concepts/](https://a2a-protocol.org/latest/topics/key-concepts/)
8. A2A Protocol. *Agent Discovery*. a2a-protocol.org, (latest). [https://a2a-protocol.org/latest/topics/agent-discovery/](https://a2a-protocol.org/latest/topics/agent-discovery/)
9. A2A Protocol. *A2A and MCP*. a2a-protocol.org, (latest). [https://a2a-protocol.org/latest/topics/a2a-and-mcp/](https://a2a-protocol.org/latest/topics/a2a-and-mcp/)

