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

- [ ] BEST PRACTICE (single agent): Define (agent) params in '.env' (use standard variable names across projects): `get_agent()`
- [ ] BEST PRACTICE (mult-agent): Define (agent) params in '.agents.json': `get_agent()`
- [ ] BEST PRACTICE: Do not hard-code prompts (load prompts from files)
- [ ] BEST PRACTICE: Read the prompt! Assume you are a junior person, on their first day at a new job: If you cannot do the task with ONLY the information in the prompt, the agent won't be able to do it either.
- [ ] BEST PRACTICE: Doctors / reviewer
  - [ ] Prompt Doctor
  - [ ] MCP Doctor
  - [ ] A2A doctor
  - [ ] Skills doctor
  - [ ] llms.txt doctor

### Chapter 1: Foundations & Architecture

- [ ] What is an Agent / Agentic System
- [ ] Code and chapters
- [ ] Reference architectures (perception, planning, acting, feedback)
- [ ] Single-agent vs multi-agent systems
- [ ] Agent lifecycle, state management, and execution (init, execution, pause/resume, cancellation, state machines, checkpoints, idempotency, retries, partial failure)
- [ ] System boundaries and responsibility split
- [ ] Contracts and schemas (inputs, outputs, tools)
- [ ] Determinism vs stochasticity

### Chapter 2: [Core Patterns](chapters/02_core_patterns/chapter.md)

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

### Chapter 3: [Tools](chapters/03_tools/chapter.md)

"Tool Use" is the fundamental pattern

- [x] Tool Use (from Core Patterns)
- [x] Tool discovery and selection
- [x] Tool contracts and schemas
- [x] "The workspace"
- [x] Advanced topics
- [x] Tool permissions (read vs write)
- [x] MCP: Introduction

### Chapter 4: [Orchestration & Control Flow](chapters/04_orchestration/chapter.md)

Structuring agent execution at a higher level.

- [x] Workflows
- [x] Graphs
- [x] A2A: Introduction
- [x] Long-running tasks and async execution
- [x] Event-driven agents

### Chapter 5: [Code Execution Modes](chapters/05_code_execution/chapter.md)

These are agents that execute code in different ways

- [x] CodeAct
- [x] MCP-Sandbox
  - [x] BEST PRACTICE: Sandboxed using containers
  - [x] BEST PRACTICE: Limit execution time (timeout)
  - [x] BEST PRACTICE: Limit resource usage (CPU, memory)
  - [x] BEST PRACTICE: Container only has access to data in workspace
  - [x] BEST PRACTICE: Validate code before execution (linting, static analysis)
  - [x] BEST PRACTICE: Log code execution (code, stdout, stderr, exit code)
  - [x] BEST PRACTICE: Use non-root user in container
  - [x] BEST PRACTICE: Limit result size (back to agent), save STDOUT, STDERR to files in workspace
- [x] REPL
- [x] NL2SQL
  - [x] BEST PRACTICE: Create table definitions (off-line)
  - [x] BEST PRACTICE: Use commments to explain fields
  - [x] BEST PRACTICE: Add 'Enums' in table definitions comments
  - [x] BEST PRACTICE: Add "sample data" (as CSV) in table definitions comments
  - [x] BEST PRACTICE: Add example queries for complex queries
  - [x] BEST PRACTICE: Validate SQL queries before execution
  - [x] BEST PRACTICE: Query timeout
  - [x] BEST PRACTICE: Limit result size
  - [x] BEST PRACTICE: Write results to file (csv), show back sample + file path (in workspace)
  - [x] BEST PRACTICE: Read only access
  - [x] BEST PRACTICE: Access "on behalf" of users (use secrets manager to handle credentials)
- [x] Autonomous vs supervised execution (Human-in-the-loop), Approval, rollback, and reversibility

### Chapter 6: [RAG](chapters/06_rag/chapter.md)

- [x] RAG: Introduction
  - [x] How a simple RAG works
- [x] Data retrieval
  - [x] Embeddings
  - [x] Vector DBs
- [x] Document ingestion (steps and what they do)
  - [x] Document Chunking strategies
- [x] Document retrieval (steps and what they do)
  - [x] Query strategies
  - [x] Scoring strategies
  - [x] Re-ranking strategies
  - [x] Filtering
  - [x] Combined strategies (using metat-data + embeddings)
- [x] Evaluating RAG systems
  - [x] Metric for vector search / vector DBs
  - [x] End-to-end RAG metrics
- [x] References, Citation, attribution, provenance and truth maintenance
- [ ] BEST PRACTICE: Doctors / reviewer

### Chapter 7: Context & Memory

These are all about how agents manage information over time.

- [ ] Prompts: System, prompt, instructions
- [ ] Prompt engineering
- [ ] Context engineering / Context window engineering
  - [ ] DEFINITION: "The dumb zone"
  - [ ] Context compression
- [ ] Token budgeting
- [ ] Conversation history
- [ ] Short-term vs long-term memory
- [ ] Memory and state management
  - [ ] Storing conversations into database
- [ ] Write-back patterns
- [ ] Knowledge bases and consistency (Batch conversion of memory to knowledge)

--- 

### Section 2: Modularization & Composition
All about building larger systems from smaller pieces.

### Chapter 8: [MCP](chapters/08_mcp/chapter.md)

- [x] Intro
- [x] Tools
- [x] Features
- [x] Achitecture
- [x] Code snuppets

### Chapter 9: [A2A](./chapters/09_a2a/chapter.md)

- [x] Intro
- [x] Tassk: 
- [x] A2A in Detail
- [x] Security

### Chapter: [Skills](./chapters/10_skills/chapter.md)

- [x] Introduction
- [x] Specification
- [x] Engineering: Skills with A2A, and MCPs.

### Chapter: Controlled vocabularies

- [ ] Intro to controlled vocabularies
- [ ] Enums: Small controlled vocabularies
- [ ] Ontologies: RAG / Tree search / Beam search

### Chapter: Connectors
- [ ] Introduction
- [ ] Connector patterns
- [ ] SQL databases
- [ ] OpenApi / REST APIs
- [ ] File based connectors (CSV, Excel, JSON, XML, etc)
- [ ] SaaS connectors (e.g. Google Sheets, Salesforce, etc)

### Chapter: Testing, Debugging, Evals, and Benchmarks

- [ ] Prompt and tool unit tests
- [ ] Contract tests for tools
- [ ] Deterministic replays and trace storage
- [ ] Scenario simulation and adversarial testing
- [ ] Offline evals and benchmarks
- [ ] Online evals and A/B testing
- [ ] Regression testing across model and prompt versions
- [ ] Eval creators (Agent that creates evals)

### Chapter: Modularity & Composition

- [ ] AGENTS.md and coding-agent conventions
- [ ] Subagents
- [ ] Agent hierarchies
- [ ] Agent swarms
- [ ] MCP-based composition
- [ ] A2A communication patterns

### Chapter: UI

- [ ] Chainlit
- [ ] AGUI
- [ ] ...(google's new protocol)
- [ ] Session ID -> MCP / A2A tracking
- [ ] File uploads
- [ ] Error propagation

### Chapter: Data

- [ ] Data source selection
- [ ] CodeIndex
- [ ] Document consistency
- [ ] Knowledge updating and reconciliation

### Chapter: Research & Science Agents

- [ ] Biomni
- [ ] Deep research
- [ ] ....
- [ ]

---

### Section 3: Production, Scaling & Enterprise

### Chapter: Privacy & Governance

Corporate security

- [ ] Security vs privacy boundaries
- [ ] Private vs public agents
- [ ] Data tainting and lineage
- [ ] Kill switches and containment
- [ ] Compliance and auditability

### Chapter: Security & Compliance for Agentic Systems

- [ ] Threat model for tool-using agents
- [ ] Prompt injection and retrieval attacks
- [ ] Tool sandboxing and network/file isolation
- [ ] Blocking outgoing connections
- [ ] AuthN/AuthZ for tools and data sources
- [ ] Secret management and credential scoping
- [ ] Policy enforcement (pre- [ ] and post-execution)
- [ ] Human approval gates for high-impact actions

### Chapter: Operations & Production

- [ ] Error propagation: Tool, MCP, A2A, Agent, UI
  - [ ] MCP error handling and retry different than tool error handling
- [ ] Robustness (Tool, MCP, A2A, Agent, UI)
- [ ] Failure recovery strategies
- [ ] Observability
- [ ] Monitoring
- [ ] Logging and tracing
- [ ] Incident response
- [ ] Model, prompt, and tool version management

---

### Section 4: Advanced Topics

### Chapter: Model Strategy & Runtime Economics

- [ ] Model selection and routing
- [ ] Small vs large models
- [ ] Fallbacks and ensembles
- [ ] Structured outputs and schema-first design
- [ ] Output repair strategies
- [ ] Latency vs cost tradeoffs
- [ ] Caching, memoization, batching
- [ ] Streaming and early stopping

### Chapter: Distributed Systems Concerns for Agentic Systems

- [ ] Distributed Systems Concerns for Agentic Systems
- [ ] Partial observability and belief maintenance
- [ ] Coordination and consensus in multi-agent settings
- [ ] Consistency models for shared state and memory
- [ ] Fault tolerance, partitions, and degraded operation
- [ ] Idempotency and exactly-once semantics across agents

### Chapter: Advanced Patterns

- [ ] Personas and simulation
- [ ] Role-playing and multi-perspective reasoning
- [ ] Governance boards
- [ ] Debate and arbitration agents

### Chapter: Learning, Adaptation, and Self-Improvement

- [ ] Online learning vs offline retraining
- [ ] Preference learning and user modeling
- [ ] Behavioral drift and stability control
- [ ] Self-evaluation and feedback-driven improvement
- [ ] Updating skills, tools, and policies safely
- [ ] Guardrails for self-modifying agents

### Chapter: Human Factors & Product Design

- [ ] Intent clarification
- [ ] When agents should ask questions
- [ ] Explainability and transparency
- [ ] Progress reporting and controllability
- [ ] Trust UX and user confidence
