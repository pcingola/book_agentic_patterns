# Agentic Patterns

## Background
We are writing a book "Agentic Patterns", which explores design patterns and best practices for building agentic systems using AI technologies. 

Audience: The audience is peopl with some experience in AI/ML and software engineering, looking to build agentic systems using LLMs and related technologies.

Book Approach: This book is supposed to have a strong theoretical background, yet be "hands on" so people can actually learn and apply the concepts. 

## Chapters

Here are the propoed chapters (divided in to sections for clarity):

---
### Section 1: Basics


TIPS: This is a lable for tips, it should be shown in a highlighted box
BEST PRACTICE: This is a label for best practices, it should be shown in a highlighted box

### To add

- [ ] Prompts: System, prompt, instructions
- [ ] Prompt doctor

- [ ] BEST PRACTICE: Define agent params in '.env' (use standard variable names across projects): `get_agent()`
- [ ] BEST PRACTICE: Do not hard-code prompts (load prompts from files)
- [ ] BEST PRACTICE: Read the prompt! Assume you are a junior person, on their first day at a new job: If you cannot do the task with ONLY the information in the prompt, the agent won't be able to do it either.
- [ ] BEST PRACTICE: Prompt Doctor

### Chapter 1: Foundations

- [ ] What is an Agent / Agentic System
- [ ] Concepts
- [ ] Code and chapters
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

### [Chapter 3: Core Patterns](./chapters/03_core_patterns/chapter.md)
These are foundational reasoning patterns

- [x] Introduction
- [x] Zero-shot & Few-shot
- [x] Self reflection
- [x] Chain-of-Thought (CoT)
- [x] Tree of Thought (ToT)
- [x] ReAct
- [x] Planning and decomposition
- [x] Verification / critique
- [x] Human in the loop

### [Chapter 4: Tools](./chapters/04_tools/chapter.md)
"Tool Use" is the fundamental pattern

- [x] Tool Use (from Core Patterns)
- [x] Tool discovery and selection
- [x] Tool contracts and schemas
- [x] "The workspace"
- [x] Advanced topics
- [x] Tool permissions (read vs write)
- [x] MCP: Introduction

### [Chapter 5: Orchestration & Control Flow](./chapters/05_orchestration/chapter.md)
Structuring agent execution at a higher level.

- [x] Workflows
- [x] Graphs
- [x] A2A: Introduction
- [x] Long-running tasks and async execution
- [x] Event-driven agents

### Chapter 6: Execution Modes
These are distinct operational modes that affect system design.

- [ ] CodeAct
- [ ] REPL
- [ ] Autonomous vs supervised execution (Human-in-the-loop)
- [ ] Approval, rollback, and reversibility

### Chapter 7: RAG
- [ ] RAG: Introduction
- [ ] Data retrieval, databases, web search, graphs
- [ ] Embeddings and vector DBs
- [ ] Chunking strategies
- [ ] Query strategies
- [ ] Re-ranking and citation
- [ ] References, Provenance and truth maintenance

### Chapter 8: Context & Memory
Merge Context Management + Data & Knowledge. These are all about how agents manage information over time.

- [ ] Prompts: System, prompt, instructions
- [ ] Prompt engineering
- [ ] Context engineering / Context window engineering
  - [ ] "The dumb zone"
  - [ ] Context compression
- [ ] Token budgeting
- [ ] Conversation history
- [ ] Short-term vs long-term memory
- [ ] Memory and state management
  - [ ] Storing conversations into database
- [ ] Write-back patterns
- [ ] Knowledge bases and consistency (Batch conversion of memory to knowledge)


### Chapter 9: Model Strategy & Runtime Economics

- [ ] Model selection and routing
- [ ] Small vs large models
- [ ] Fallbacks and ensembles
- [ ] Structured outputs and schema-first design
- [ ] Output repair strategies
- [ ] Latency vs cost tradeoffs
- [ ] Caching, memoization, batching
- [ ] Streaming and early stopping


### Chapter 10: Testing, Debugging, and Evals

- [ ] Prompt and tool unit tests
- [ ] Contract tests for tools
- [ ] Deterministic replays and trace storage
- [ ] Scenario simulation and adversarial testing
- [ ] Offline evals and benchmarks
- [ ] Online evals and A/B testing
- [ ] Regression testing across model and prompt versions

### Chapter 11: UI

- [ ] Chainlit
- [ ] AGUI
- [ ] ...(google's new protocol)
- [ ] Session ID -> MCP / A2A tracking
- [ ] File uploads
- [ ] Error propagation

---

### Section 2: Modularization & Composition
All about building larger systems from smaller pieces.

### Chapter 12: MCP

- [ ] MCP in depth

### Chapter 13: A2A

- [ ] A2A in depth

### Chapter 14: Modularity & Composition

- [ ] AGENTS.md and coding-agent conventions
- [ ] Skills and progressive disclosure
- [ ] Subagents
- [ ] Agent hierarchies
- [ ] Agent swarms
- [ ] MCP-based composition
- [ ] A2A communication patterns

---

### Section 3: Advanced topics

### Chapter 15: Distributed Systems Concerns for Agentic Systems
- [ ] Distributed Systems Concerns for Agentic Systems
- [ ] Partial observability and belief maintenance
- [ ] Coordination and consensus in multi-agent settings
- [ ] Consistency models for shared state and memory
- [ ] Fault tolerance, partitions, and degraded operation
- [ ] Idempotency and exactly-once semantics across agents

### Chapter 16: Advanced Patterns

- [ ] Personas and simulation
- [ ] Role-playing and multi-perspective reasoning
- [ ] Governance boards
- [ ] Debate and arbitration agents

### Chapter 17: Data

- [ ] NL2SQL
- [ ] Data source selection
- [ ] CodeIndex
- [ ] Document consistency
- [ ] Knowledge updating and reconciliation

### Chapter 18: Privacy & Governance
Corporate security

- [ ] Security vs privacy boundaries
- [ ] Private vs public agents
- [ ] Data tainting and lineage
- [ ] Kill switches and containment
- [ ] Compliance and auditability

### Chapter 19: Security & Compliance for Agentic Systems

- [ ] Threat model for tool-using agents
- [ ] Prompt injection and retrieval attacks
- [ ] Tool sandboxing and network/file isolation
- [ ] Blocking outgoing connections
- [ ] AuthN/AuthZ for tools and data sources
- [ ] Secret management and credential scoping
- [ ] Policy enforcement (pre- [ ] and post-execution)
- [ ] Human approval gates for high-impact actions

### Chapter 20: Learning, Adaptation, and Self-Improvement
- [ ] Online learning vs offline retraining
- [ ] Preference learning and user modeling
- [ ] Behavioral drift and stability control
- [ ] Self-evaluation and feedback-driven improvement
- [ ] Updating skills, tools, and policies safely
- [ ] Guardrails for self-modifying agents

### Chapter 21: Scientific Agents and tooling
- [ ] Biomni
- [ ] ....
- [ ] ....
- [ ]

---

### Chapter 22: Operations & Production

- [ ] Error propagation: Tool, MCP, A2A, Agent, UI
  - [ ] MCP error handling and retry different than tool error handling
- [ ] Robustness (Tool, MCP, A2A, Agent, UI)
- [ ] Failure recovery strategies
- [ ] Observability
- [ ] Monitoring
- [ ] Logging and tracing
- [ ] Incident response
- [ ] Model, prompt, and tool version management

### Chapter 23: Human Factors & Product Design

- [ ] Intent clarification
- [ ] When agents should ask questions
- [ ] Explainability and transparency
- [ ] Progress reporting and controllability
- [ ] Trust UX and user confidence
