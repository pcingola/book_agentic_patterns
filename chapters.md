# Agentic Patterns

## Background

We are writing a book "Agentic Patterns", which explores design patterns and best practices for building agentic systems using AI technologies. 

Audience: The audience is peopl with some experience in AI/ML and software engineering, looking to build agentic systems using LLMs and related technologies.

Book Approach: This book is supposed to have a strong theoretical background, yet be "hands on" so people can actually learn and apply the concepts. 

Goal: Build a full Enterprise grade agentit platform using best practices.

## Chapters

Here are the propoed chapters (divided in to sections for clarity):

TIPS: This is a lable for tips, it should be shown in a highlighted box

BEST PRACTICE: This is a label for best practices, it should be shown in a highlighted box

## Section 1: Basics

### Chapter: [Foundations](chapters/foundations/chapter.md)

- [x] Outline
- [x] Historical Perspectives
- [x] Agent
- [x] Stochasticity
- [x] Agentic modularity
- [x] Best practices
- [x] Hands-on: Python Recap
- [x] Hands-on: Understanding the OpenAI API
- [x] Hands-on: Building Your First Agent
- [x] Hands-on: Running Agents
- [x] Hands-on: System Prompt vs User Prompt
- [x] Hands-on: Multi-Turn Conversations
- [x] References

### Chapter: [Core Patterns](chapters/core_patterns/chapter.md)

These are foundational reasoning patterns

- [x] Introduction
- [x] Historical Perspectives
- [x] Zero-shot & Few-shot
- [x] Chain-of-Thought (CoT)
- [x] Tree of Thought (ToT)
- [x] ReAct
- [x] CodeAct
- [x] Self reflection
- [x] Verification / critique
- [x] Planning and decomposition
- [x] Human in the loop
- [x] Hands-on: Intro
- [x] Hands-on: Zero-shot & Few-shot
- [x] Hands-on: Chain-of-Thought
- [x] Hands-on: Tree of Thought
- [x] Hands-on: ReAct
- [x] Hands-on: CodeAct
- [x] Hands-on: Self reflection
- [x] Hands-on: Verification / Critique
- [x] Hands-on: Planning and Decomposition
- [x] Hands-on: Human in the Loop
- [x] References

### Chapter: [Tools](chapters/tools/chapter.md)

"Tool Use" is the fundamental pattern

- [x] Historical Perspectives
- [x] Tool Use
- [x] Structured output
- [x] Tool discovery and selection
- [x] Tool contracts and schemas
- [x] Tool permissions
- [x] The workspace
- [x] Advanced topics
- [x] MCP: Introduction
- [x] Hands-on: Introduction
- [x] Hands-on: Tool Use
- [x] Hands-on: Structured Outputs
- [x] Hands-on: Tool Discovery and Selection
- [x] Hands-on: Tool Permissions
- [x] Hands-on: The Workspace
- [x] References

### Chapter: [Orchestration & Control Flow](chapters/orchestration/chapter.md)

Structuring agent execution at a higher level.

- [x] Historical Perspective
- [x] Workflows
- [x] Graphs
- [x] A2A: Introduction
- [x] Long-running tasks and async execution
- [x] Event-driven agents
- [x] Hands-on: Introduction
- [x] Hands-on: Sequential Workflows
- [x] Hands-on: Graph-Based Orchestration
- [x] Hands-on: Agent Delegation
- [x] Hands-on: Agent Hand-Off
- [x] References

### Chapter: [RAG](chapters/rag/chapter.md)

- [x] RAG: Introduction
  - [x] How a simple RAG works
- [x] Historical Perspective
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
- [x] Hands-on: Introduction
- [x] Hands-on: Simple Document Ingestion and Retrieval
- [x] Hands-on: Advanced Document Ingestion and Retrieval
- [x] References
- [ ] BEST PRACTICE: Doctors / reviewer

### Chapter: [Context & Memory](chapters/context_memory/chapter.md)

These are all about how agents manage information over time.

- [x] Introduction
- [x] Historical Perspective
- [x] Prompts
  - [x] System, prompt, instructions
  - [x] Conversation history
  - [x] Short-term vs long-term memory
  - [x] Memory and state management: Storing conversations into database
- [x] Context engineering / Context window engineering
  - [x] Prompt engineering
  - [x] DEFINITION: "The dumb zone": When the context goes over ~ 40%
  - [x] Context compression
  - [x] Token budgeting
  - [x] Write-back patterns
- [x] Hands-on: Introduction
- [x] Hands-on: Prompts
- [x] Hands-on: Context Result Decorator
- [x] Hands-on: History Compaction
- [x] References

### Chapter: [MCP](chapters/mcp/chapter.md)

- [x] Historical Perspective
- [x] Intro
- [x] Tools
- [x] Features
- [x] Architecture
- [x] Hands-on: Introduction
- [x] Hands-on: MCP STDIO Transport
- [x] Hands-on: MCP Tools with Agents
- [x] Hands-on: MCP Features
- [x] References

### Chapter: [A2A](chapters/a2a/chapter.md)

- [x] Introduction
- [x] Historical Perspectives
- [x] Tasks
- [x] Details
- [x] Security
- [x] Hands-on: Introduction
- [x] Hands-on: A2A Client-Server
- [x] Hands-on: A2A Coordinator Agent
- [x] References

### Chapter: [Skills & Sub-Agents](chapters/skills_and_sub_agents/chapter.md)

- [x] Introduction
- [x] Sub-agents
- [x] Context engineering: why sub-agents help
- [x] Skills Specification
- [x] Skills Engineering
- [x] Comparison: Sub-agents, Skills, MCP, and A2A
- [x] Hands-on: Fixed Sub-Agents
- [x] Hands-on: Dynamic Sub-Agents
- [x] Hands-on: Skills
- [x] References

### Chapter: [Evals](chapters/evals/chapter.md)

- [x] Introduction
- [x] Historical Perspective
- [x] Testing & Debugging agents
- [x] Evals
- [x] Hands-on: Introduction
- [x] Hands-on: Deterministic Testing
- [x] Hands-on: Basic Evals
- [x] Hands-on: Pydantic Evals Framework
- [x] Hands-on: Doctors
- [x] References

### Chapter: [Data Sources & Connectors](chapters/data_sources_and_connectors/chapter.md)

- [x] Introduction
- [x] Connector patterns
- [x] OpenApi / REST APIs
- [x] File based connectors (CSV, Excel, JSON, XML, etc)
- [x] NL2SQL
  - [x] BEST PRACTICE: Create table definitions (off-line)
  - [x] BEST PRACTICE: Use comments to explain fields
  - [x] BEST PRACTICE: Add 'Enums' in table definitions comments
  - [x] BEST PRACTICE: Add "sample data" (as CSV) in table definitions comments
  - [x] BEST PRACTICE: Add example queries for complex queries
  - [x] BEST PRACTICE: Validate SQL queries before execution
  - [x] BEST PRACTICE: Query timeout
  - [x] BEST PRACTICE: Limit result size
  - [x] BEST PRACTICE: Write results to file (csv), show back sample + file path (in workspace)
  - [x] BEST PRACTICE: Read only access
  - [x] BEST PRACTICE: Access "on behalf" of users (use secrets manager to handle credentials)
  - [x] BEST PRACTICE: Data source selection (which database should I use for this quesiton / user request?)
- [x] Controlled vocabularies
  - [x] Enums: Small controlled vocabularies
  - [x] Ontologies: RAG / Tree search / Beam search

### Chapter: [User Interface](chapters/ui/chapter.md)

- [x] Chainlit
- [x] AGUI
- [x] Session ID -> MCP / A2A tracking
- [ ] File uploads: Workspace and sampling the file (context management)
- [x] Cancellation and error propagation: Tool, MCP, A2A, Agent, UI
  - [x] MCP error handling and retry different than tool error handling
  - [x] Retries in tools vs MCP (PydanticAI vs FastMCP)
- [ ] User feedback: Session thumb up/down, report errors, etc.

### Section: Production, Scaling & Enterprise

Into: Introduction to section, what we are building and how

### Chapter: Core Agent

- Core agent
- CodeAct
- Run skills
- Run sub-agents
- Workspace / Userspace
- Basic MCPs:
  - mcp-todo
  - mcp-file-edit
  - mcp-sandbox

### Chapter: [Execution Infrastructure](chapters/execution_infrastructure/chapter.md)

Production infrastructure for running agent-generated code safely.

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
- [x] Autonomous vs supervised execution (Human-in-the-loop), Approval, rollback, and reversibility
- [ ] Code Deployments, static and dynamic containers (Docker + Traefic)

### Chapter: Research & Science Agents

- [ ] A2A: Data analysis
- [ ] Deep research
- [ ] Biomni
- [ ] ....
- [ ] Personas and simulation, Role-playing and multi-perspective reasoning. Debate and arbitration agents

### Chapter: Privacy & Governance

Corporate security

- [ ] Kill switch: Blocking ALL outgoing connections (whitelist)
- [ ] Security vs privacy boundaries
- [ ] Private vs public agents
- [ ] Data tainting and lineage
- [ ] Kill switches and containment
- [ ] Compliance and auditability
- [ ] Threat model for tool-using agents
- [ ] Prompt injection and retrieval attacks
- [ ] Tool sandboxing and network/file isolation
- [ ] Blocking outgoing connections
- [ ] AuthN/AuthZ for tools and data sources
- [ ] Secret management and credential scoping
- [ ] Policy enforcement (pre- [ ] and post-execution)
- [ ] Human approval gates for high-impact actions

