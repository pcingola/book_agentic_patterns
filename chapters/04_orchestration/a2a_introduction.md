## A2A: Agent-to-Agent

Agent-to-Agent (A2A) communication is a coordination pattern in which autonomous agents interact through a shared protocol to delegate work, exchange state, and compose system-level behavior.

### Historical perspective

The intellectual roots of A2A go back to early work on distributed artificial intelligence and multi-agent systems in the late 1980s and 1990s. At that time, researchers observed that complex problem solving could not be reduced to a single reasoning entity, but instead emerged from cooperation, negotiation, and coordination between multiple agents. This led to the first explicit agent communication languages, such as KQML, and later to standardized specifications like FIPA-ACL, which formalized the structure and semantics of messages exchanged between agents.

In parallel, research in distributed systems and software architecture shaped how independent components should interact. Message passing, remote procedure calls, and event-driven systems emphasized loose coupling, explicit interfaces, and failure isolation. The actor model reinforced the idea that independent computational entities should communicate only through messages, never by shared mutable state.

Modern LLM-based agents inherit all of these traditions. While the internal reasoning mechanisms have changed dramatically, the architectural pressures remain the same: as soon as systems involve multiple agents with different responsibilities, lifecycles, or ownership boundaries, communication must be explicit, structured, and observable. The A2A Protocol emerges in this context as a contemporary formalization of agent communication, designed for long-running, heterogeneous, and production-grade agentic systems.

### The A2A pattern

At its core, A2A treats each agent as an independent, network-addressable entity with a well-defined boundary. An agent exposes what it can do, accepts requests from other agents, and produces responses or follow-up messages, all without revealing its internal implementation. Coordination is achieved through message exchange rather than shared control flow or shared memory.

This separation has important consequences. Agents can be developed, deployed, and evolved independently. Failures are localized to agent boundaries. System behavior emerges from interaction patterns rather than from a single central orchestrator. In this sense, A2A shifts orchestration from an internal control structure to an external protocol.

Unlike workflows or graphs, which primarily describe how steps are sequenced within a bounded execution, A2A focuses on how autonomous agents relate to one another across time. It provides the connective tissue that allows multiple workflows, owned by different agents, to form a coherent system.

### Core capabilities

A2A communication relies on a small set of foundational capabilities that are intentionally minimal but powerful. Each agent has a stable identity and a way to describe its capabilities so that other agents know what kinds of requests it can handle. Communication happens through standardized message envelopes that carry not only the payload, but also metadata such as sender, recipient, intent, and correlation identifiers. This metadata makes it possible to trace interactions, reason about partial failures, and correlate responses with earlier requests.

Messages are typically intent-oriented rather than procedural. Instead of calling a specific function, an agent asks another agent to *perform an analysis*, *retrieve information*, or *review a decision*. This level of abstraction makes interactions more robust to internal refactoring and allows agents to apply their own policies, validation steps, or human-in-the-loop checks before acting.

Crucially, A2A communication is asynchronous by default. An agent may acknowledge a request immediately, process it over minutes or hours, and send intermediate updates or a final result later. This makes the pattern well suited for long-running tasks, background analysis, and real-world integrations where latency and partial completion are unavoidable.

### How A2A works in practice

From an execution standpoint, A2A introduces a thin protocol layer between agents. When one agent wants to delegate work, it constructs a message that describes the intent and provides the necessary input data. This message is sent through the A2A transport to another agent, which validates the request, performs the work according to its own logic, and replies with one or more messages.

A minimal illustration looks like the following:

```python
# Agent A: delegate a task to another agent
message = {
    "to": "research-agent",
    "intent": "analyze_document",
    "payload": {"document_id": "doc-123"},
    "correlation_id": "task-42",
}

send_message(message)
```

```python
# Agent B: handle the request and respond
def on_message(message):
    if message["intent"] == "analyze_document":
        result = analyze_document(message["payload"])
        response = {
            "to": message["from"],
            "intent": "analysis_result",
            "payload": result,
            "correlation_id": message["correlation_id"],
        }
        send_message(response)
```

The important aspect is not the syntax, but the architectural boundary. Each agent owns its execution, state, and failure handling. The protocol provides just enough structure to make coordination reliable without constraining internal design choices.

### Role of A2A in orchestration

As agentic systems scale, purely centralized orchestration becomes increasingly fragile. A2A enables a more decentralized model in which agents collaborate directly, while higher-level orchestration emerges from their interaction patterns. In practice, A2A often complements other control-flow constructs: workflows define local sequencing, graphs define structured decision paths, and A2A connects these pieces across agent boundaries.

This section intentionally remains shallow. The goal is to position A2A as a first-class orchestration pattern rather than to exhaustively specify the protocol. Later chapters will examine transports, schemas, security models, and advanced coordination strategies built on top of A2A.

### References

1. Wooldridge, M. *An Introduction to MultiAgent Systems*. Wiley, 2002.
2. Finin, T. et al. *KQML as an Agent Communication Language*. International Conference on Information and Knowledge Management, 1994.
3. FIPA. *FIPA ACL Message Structure Specification*. FIPA, 2002.
4. A2A Protocol Working Group. *A2A Protocol Specification*. 2024. [https://a2a-protocol.org/latest/](https://a2a-protocol.org/latest/)
