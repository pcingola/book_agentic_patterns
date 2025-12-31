# Agentic Patterns

## Background
We are writing a book "Agentic Patterns", which explores design patterns and best practices for building agentic systems using AI technologies. 

Audience: The audience is peopl with some experience in AI/ML and software engineering, looking to build agentic systems using LLMs and related technologies.

Book Approach: This book is supposed to have a strong theoretical background, yet be "hands on" so people can actually learn and apply the concepts. 

## Chapters

Here are the propoed chapters (divided in to sections for clarity):

---
### Section 1: Basics

### Chapter 1: Foundations

- [ ] What is an Agent / Agentic System
- [ ] Concepts
- [ ] Reference architectures (perception, planning, acting, feedback)
- [ ] Single-agent vs multi-agent systems
- [ ] Online vs offline agents
- [ ] Agent lifecycle (init, execution, pause/resume, cancellation)
- [ ] State machines and checkpoints
- [ ] Protocols: MCP, A2A

### Chapter 2: Agent Architecture & Lifecycle

- [ ] System boundaries and responsibility split
- [ ] State, idempotency, retries, and partial failure
- [ ] Contracts and schemas (inputs, outputs, tools)
- [ ] Capability boundaries and versioning
- [ ] Determinism vs stochasticity

### Chapter 3: Core Agentic Patterns
These are foundational reasoning patterns

- [x] Introduction
- [x] Zero-shot & Few-shot
- [x] Self reflection
- [x] Chain-of-Thought (CoT)
- [x] Tree of Thought (ToT)
- [x] ReAct
- [x] Planning and decomposition
- [x] Verification / critique

### Chapter 4: Tool Use
"Tool Use" is the fundamental pattern

- [ ] Tool Use (from Core Patterns)
- [ ] Tool discovery and selection
- [ ] Tool contracts and schemas
- [ ] Tool doctor / tool repair
- [ ] Tool permissions (read vs write)
- [ ] MCP: Introduction

### Chapter 5: Orchestration & Control Flow
Structuring agent execution at a higher level.

- [ ] Workflows
- [ ] Graphs
- [ ] Planning and replanning
- [ ] Long-running tasks and async execution
- [ ] Event-driven agents
- [ ] A2A: Introduction

### Chapter 6: Execution Modes
These are distinct operational modes that affect system design.

- [ ] Single-shot vs Planning vs Reasoning
- [ ] CodeAct & REPL
- [ ] Autonomous vs supervised execution
- [ ] Human-in-the-loop
- [ ] Approval, rollback, and reversibility

### Chapter 7: Context & Memory
Merge Context Management + Data & Knowledge. These are all about how agents manage information over time.

- [ ] Context window engineering
- [ ] Token budgeting
- [ ] Conversation history
- [ ] Short-term vs long-term memory
- [ ] Memory and state management
- [ ] Write-back patterns
- [ ] RAG: Introduction
  - [ ] Data retrieval, databases, web search, graphs
  - [ ] Embeddings and vector DBs
  - [ ] Chunking strategies
  - [ ] Query strategies
  - [ ] Re-ranking and citation
- [ ] Knowledge bases and consistency
- [ ] Provenance and truth maintenance

### Chapter 8: Model Strategy & Runtime Economics

- [ ] Model selection and routing
- [ ] Small vs large models
- [ ] Fallbacks and ensembles
- [ ] Structured outputs and schema-first design
- [ ] Output repair strategies
- [ ] Latency vs cost tradeoffs
- [ ] Caching, memoization, batching
- [ ] Streaming and early stopping

### Chapter 9: Testing, Debugging, and Evals

- [ ] Prompt and tool unit tests
- [ ] Contract tests for tools
- [ ] Deterministic replays and trace storage
- [ ] Scenario simulation and adversarial testing
- [ ] Offline evals and benchmarks
- [ ] Online evals and A/B testing
- [ ] Regression testing across model and prompt versions

---

### Section 2: Modularization & Composition
All about building larger systems from smaller pieces.

### Chapter 10: Interoperability Standards

- [ ] MCP in depth
- [ ] A2A in depth
- [ ] AGENTS.md and coding-agent conventions

### Chapter 11: Modularity & Composition

- [ ] Skills and progressive disclosure
- [ ] Subagents
- [ ] Agent hierarchies
- [ ] Agent swarms
- [ ] MCP-based composition
- [ ] A2A communication patterns

### Chapter 12: Distributed Systems Concerns for Agentic Systems
- [ ] Distributed Systems Concerns for Agentic Systems
- [ ] Partial observability and belief maintenance
- [ ] Coordination and consensus in multi-agent settings
- [ ] Consistency models for shared state and memory
- [ ] Fault tolerance, partitions, and degraded operation
- [ ] Idempotency and exactly-once semantics across agents

---

### Section 3: Advanced topics

### Chapter 13: Advanced Patterns

- [ ] Personas and simulation
- [ ] Role-playing and multi-perspective reasoning
- [ ] Governance boards
- [ ] Debate and arbitration agents

### Chapter 14: Data

- [ ] NL2SQL
- [ ] Data source selection
- [ ] CodeIndex
- [ ] Document consistency
- [ ] Knowledge updating and reconciliation

### Chapter 15: Privacy & Governance
Corporate security

- [ ] Security vs privacy boundaries
- [ ] Private vs public agents
- [ ] Data tainting and lineage
- [ ] Kill switches and containment
- [ ] Compliance and auditability

### Chapter 16: Security & Compliance for Agentic Systems

- [ ] Threat model for tool-using agents
- [ ] Prompt injection and retrieval attacks
- [ ] Tool sandboxing and network/file isolation
- [ ] Blocking outgoing connections
- [ ] AuthN/AuthZ for tools and data sources
- [ ] Secret management and credential scoping
- [ ] Policy enforcement (pre- [ ] and post-execution)
- [ ] Human approval gates for high-impact actions

### Chapter 17: Learning, Adaptation, and Self-Improvement
- [ ] Online learning vs offline retraining
- [ ] Preference learning and user modeling
- [ ] Behavioral drift and stability control
- [ ] Self-evaluation and feedback-driven improvement
- [ ] Updating skills, tools, and policies safely
- [ ] Guardrails for self-modifying agents

---

### Chapter 18: Operations & Production

- [ ] Robustness and error propagation: Tool, MCP, A2A, Agent, UI
- [ ] Failure recovery strategies
- [ ] Observability
- [ ] Monitoring
- [ ] Logging and tracing
- [ ] Incident response
- [ ] Model, prompt, and tool version management

### Chapter 19: Human Factors & Product Design

- [ ] Intent clarification
- [ ] When agents should ask questions
- [ ] Explainability and transparency
- [ ] Progress reporting and controllability
- [ ] Trust UX and user confidence
