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

Defines what agentic systems are, how they differ from traditional software, and establishes the modularity and design principles used throughout the book.

- [x] Outline -- Book structure, audience, and learning philosophy combining theory with hands-on practice
- [x] Historical Perspectives -- Evolution of AI agents from classical RL and Bellman equations to modern LLM-based systems
- [x] Agent -- Agentic systems as LLM plus tools in a decide-act loop until goal completion
- [x] Stochasticity -- Designing for reproducibility in systems between deterministic software and stochastic models
- [x] Agentic modularity -- Modularity stack from prompt fragments to inter-agent protocols for independent evolution
- [x] Best practices -- Sutton's Bitter Lesson applied to agent engineering: general mechanisms over prompt micro-surgery
- [x] Hands-on: Python Recap -- Essential Python (iterators, generators, async/await) for async agent execution and streaming
- [x] Hands-on: Understanding the OpenAI API -- The de-facto API standard, message structure, and multi-provider interface
- [x] Hands-on: Building Your First Agent -- Creating and running a simple agent with PydanticAI
- [x] Hands-on: Running Agents -- The run_agent() function with async streaming and step-by-step logging
- [x] Hands-on: System Prompt vs User Prompt -- Comparing single-prompt vs separated system/user prompts for reusability
- [x] Hands-on: Multi-Turn Conversations -- Maintaining conversation context across turns by passing message history
- [x] References

### Chapter: [Core Patterns](chapters/core_patterns/chapter.md)

Foundational reasoning patterns from zero-shot prompting through structured planning and human oversight as a progression toward full agency.

- [x] Introduction -- Overview of patterns as a coherent progression from prompting to structured, iterative agency
- [x] Historical Perspectives -- Transfer learning, pre-trained models, and the convergence of LLM-based techniques in early 2020s
- [x] Zero-shot & Few-shot -- In-context learning and task adaptation without retraining via prompting and examples
- [x] Chain-of-Thought (CoT) -- Externalizing intermediate reasoning steps for multi-step problem solving and inspection
- [x] Tree of Thought (ToT) -- Reasoning as search with branching, evaluation, and pruning of alternative paths
- [x] ReAct -- Interleaving explicit reasoning with tool/environment actions using observations as feedback
- [x] CodeAct -- Code execution as the primary action modality with program results driving iterative refinement
- [x] Self reflection -- Agents inspecting, critiquing, and revising their own outputs for improved correctness
- [x] Verification / critique -- Explicit evaluation phases checking outputs against defined criteria before acceptance
- [x] Planning and decomposition -- Breaking high-level goals into structured, ordered sub-tasks before execution
- [x] Human in the loop -- Pausing autonomous execution at structured checkpoints for human input or authorization
- [x] Hands-on: Intro -- Practical implementations demonstrating pattern mechanics and improvements over naive approaches
- [x] Hands-on: Zero-shot & Few-shot -- Contrasting examples where zero-shot works vs where few-shot is necessary
- [x] Hands-on: Chain-of-Thought -- How explicit intermediate steps improve reasoning accuracy
- [x] Hands-on: Tree of Thought -- Exploring multiple reasoning paths for complex problems like systems design
- [x] Hands-on: ReAct -- Interleaved reasoning and actions using an order tracking system environment
- [x] Hands-on: CodeAct -- Agents reasoning by writing and executing Python code in a sandboxed environment
- [x] Hands-on: Self reflection -- Code generation with critique-and-revise cycles
- [x] Hands-on: Verification / Critique -- Password generation with verification loops against enumerable constraints
- [x] Hands-on: Planning and Decomposition -- Data pipeline task with explicit plan-then-implement structure
- [x] Hands-on: Human in the Loop -- Database operations requiring human approval for irreversible actions
- [x] References

### Chapter: [Tools](chapters/tools/chapter.md)

Tool use as the fundamental agent pattern: discovery, schemas, permissions, workspaces, and introduction to MCP.

- [x] Historical Perspectives -- Evolution from symbolic AI blackboard architectures to modern LLM tool-calling with MCP
- [x] Tool Use -- The core pattern: models reasoning about capabilities, invoking them with structured inputs, and incorporating results
- [x] Structured output -- Constraining outputs to schemas for validation, decision-making, and control flow boundaries
- [x] Tool discovery and selection -- Two-stage pattern: selection agent filters tools before task-execution agent operates
- [x] Tool contracts and schemas -- Defining tool interfaces through contracts with names, inputs, outputs, and constraints
- [x] Tool permissions -- READ/WRITE/CONNECT permission boundaries to contain mistakes, prevent leaks, and enforce governance
- [x] The workspace -- Shared persistent filesystem for externalizing large artifacts and managing context limits
- [x] Advanced topics -- Approval gates, runtime toolset reshaping, deferred execution, and self-diagnostic capabilities
- [x] MCP: Introduction -- Model Context Protocol as a standardized JSON-RPC interface moving tool definitions to external servers
- [x] Hands-on: Introduction -- Overview of exercises covering tool calling, structured outputs, selection, permissions, and workspace
- [x] Hands-on: Tool Use -- How models decide when to use tools and how results flow back into reasoning
- [x] Hands-on: Structured Outputs -- Constraining responses to Pydantic schemas for typed integration and validation
- [x] Hands-on: Tool Discovery and Selection -- Manual and automated tool filtering with ToolSelector for large catalogs
- [x] Hands-on: Tool Permissions -- Annotating tools with permissions and enforcing them at construction or runtime
- [x] Hands-on: The Workspace -- Path translation, write-and-summarize patterns, and user isolation for multi-tenant security
- [x] References

### Chapter: [Orchestration & Control Flow](chapters/orchestration/chapter.md)

Structuring multi-agent execution through workflows, graphs, delegation, and asynchronous task patterns.

- [x] Historical Perspective -- From Petri nets and actor models through workflow systems to modern LLM-based orchestration
- [x] Workflows -- Explicit control structures coordinating multiple agent stages through defined transitions and hand-offs
- [x] Graphs -- Directed state machines with typed state, conditional edges, branching, cycles, and explicit control flow
- [x] A2A: Introduction -- Asynchronous agent-to-agent communication via message exchange without shared control flow
- [x] Long-running tasks and async execution -- Deep agent hierarchies, delegation without blocking, and episodic reasoning
- [x] Event-driven agents -- Agents reacting to external and internal events with handlers that update state and emit follow-ups
- [x] Hands-on: Introduction -- Four exercises demonstrating sequential workflows, graphs, delegation, and hand-off patterns
- [x] Hands-on: Sequential Workflows -- Content generation pipeline with three sequential stages using typed output contracts
- [x] Hands-on: Graph-Based Orchestration -- Document quality review loop as a state machine with conditional refinement cycles
- [x] Hands-on: Agent Delegation -- Parent research agent invoking a fact-checking specialist through a tool
- [x] Hands-on: Agent Hand-Off -- Customer support triage routing requests to specialists with enum-based classification
- [x] References

### Chapter: [RAG](chapters/rag/chapter.md)

Retrieval-Augmented Generation: embeddings, vector databases, document ingestion/retrieval pipelines, evaluation, and attribution.

- [x] Introduction -- Core RAG pattern combining retrieval with generation to ground answers in external knowledge
- [x] Historical Perspective -- From vector space models and probabilistic IR through dense embeddings to integrated RAG systems
- [x] Embeddings -- Dense semantic vectors where geometric proximity reflects semantic similarity for meaning-based retrieval
- [x] Vector Databases -- Specialized systems for storing and searching high-dimensional vectors with graph and quantization indexing
- [x] Document Ingestion -- Parsing, normalization, metadata enrichment, and chunking to prepare a corpus for embedding
- [x] Document Retrieval -- Multi-stage pipeline: query interpretation, candidate generation, scoring, re-ranking, and filtering
- [x] Evaluating RAG Systems -- Layered metrics for vector search quality, document retrieval relevance, and generation faithfulness
- [x] References and Attribution -- Provenance mechanisms linking generated statements to source documents for auditability
- [x] Hands-on: Introduction -- Overview of exercises from simple paragraph-based RAG through advanced semantic chunking
- [x] Hands-on: Simple Document Ingestion and Retrieval -- Foundational RAG with paragraph chunking, Chroma storage, and similarity retrieval
- [x] Hands-on: Advanced Document Ingestion and Retrieval -- Semantic chunking with LLM boundary detection, query expansion, and re-ranking
- [x] References

### Chapter: [Context & Memory](chapters/context_memory/chapter.md)

Prompt layering, context window engineering, compression, token budgeting, and write-back patterns for managing agent information over time.

- [x] Introduction -- Evolution from prompt engineering to systematic context management with memory and token budgeting
- [x] Historical Perspective -- In-context learning, instruction tuning, and memory networks shifting focus to prompts as programmable interfaces
- [x] Prompts -- Structure of prompt layers (system, developer, user, history) and curating them as a single effective context
- [x] Context engineering -- Shaping what agents see at inference time through inclusion, structure, and refresh patterns
- [x] Hands-on: Introduction -- Three exercises: prompt layers, tool output truncation with @context_result, and history compaction
- [x] Hands-on: Prompts -- How system prompts, developer instructions, and user prompts combine with different persistence behaviors
- [x] Hands-on: Context Result Decorator -- Truncating large tool outputs by saving full results to workspace while sending compact previews
- [x] Hands-on: History Compaction -- Summarizing older exchanges when token usage exceeds thresholds for unbounded conversations
- [x] References

### Chapter: [MCP](chapters/mcp/chapter.md)

Model Context Protocol: open standard for tool discovery, structured interaction, and transport-agnostic agent-server communication.

- [x] Introduction -- MCP as an open protocol standardizing how AI models discover and interact with external tools and context
- [x] Historical Perspective -- Agent architectures and tool-augmented LMs converging on LSP-inspired protocol design
- [x] Tools -- MCP's execution boundary where model intent becomes validated, observable actions with structured inputs/outputs
- [x] Features -- Prompts, resources, sampling, and elicitation for inspectable and scalable agent behavior
- [x] Architecture -- Client-server lifecycle, layered server architecture, capability exposure, authorization, and transport
- [x] Hands-on: Introduction -- Progressive exercises from raw protocol messages through agent integration to full feature sets
- [x] Hands-on: MCP STDIO Transport -- JSON-RPC message exchange between client and server subprocess for local development
- [x] Hands-on: MCP Tools with Agents -- Agent frameworks handling MCP mechanics to invoke server tools via STDIO or HTTP
- [x] Hands-on: MCP Features -- Exploring MCP's complete feature set (tools, resources, prompts) and how context is structured
- [x] References

### Chapter: [A2A](chapters/a2a/chapter.md)

Agent-to-Agent protocol for discovery, task exchange, and coordination of autonomous agents over HTTP/JSON-RPC.

- [x] Introduction -- A2A as an HTTP-based protocol for agent discovery, message exchange, and long-running task coordination
- [x] Historical Perspectives -- From KQML and FIPA ACL to pragmatic standardization of external contracts using modern web primitives
- [x] Tasks -- Durable, asynchronous units of work observable through streaming, polling, and notifications
- [x] Details -- Minimal operations and data models (Task, Message, Part, Artifact) mapping onto JSON-RPC/HTTP/gRPC bindings
- [x] Security -- Agent identity verification, bearer tokens, mTLS, and authorization scopes against confused-deputy attacks
- [x] Hands-on: Introduction -- Progressing from simple A2A client-server tasks to multi-agent coordinator patterns
- [x] Hands-on: A2A Client-Server -- Server exposing an agent with tools and a client discovering, sending tasks, and retrieving results
- [x] Hands-on: A2A Coordinator Agent -- Coordinator discovering specialist agents via Agent Cards and routing requests by capability
- [x] References

### Chapter: [Skills, Sub-Agents & Tasks](chapters/skills_and_sub_agents/chapter.md)

Sub-agent delegation, skill packaging and discovery, task lifecycle management, and comparing composition approaches.

- [x] Introduction -- Overview of sub-agents, skills, and tasks as patterns for managing agent complexity
- [x] Sub-agents -- Autonomous agent instances with isolated context delegated by a parent for scoped tasks
- [x] Context engineering: why sub-agents help -- Context isolation and prevention of prompt bloat through sub-agent delegation
- [x] Skills Specification -- Filesystem-based format for packaging capabilities as directories with SKILL.md and supporting files
- [x] Skills Engineering -- Integration patterns for discovery, advertising, and safe activation with progressive disclosure
- [x] Comparison: Sub-agents, Skills, MCP, and A2A -- Decision matrix with guidance on when to use each composition pattern
- [x] Agents.md -- Repository-level persistent guidance files (AGENTS.md/CLAUDE.md) for version-controlled agent behavior
- [x] Tasks -- Lifecycle management wrapping sub-agent execution with durable state, observation, and explicit control
- [x] Hands-on: Fixed Sub-Agents -- Pre-defined specialist sub-agents with coordinator delegation and structured outputs
- [x] Hands-on: Dynamic Sub-Agents -- Runtime creation of sub-agents where a coordinator spawns specialists on demand
- [x] Hands-on: Tasks -- Task lifecycle with state machine, storage, worker execution, and broker coordination
- [x] Hands-on: Skills -- Skill discovery via registry, activation, and usage with progressive disclosure
- [x] References

### Chapter: [Evals](chapters/evals/chapter.md)

Testing, debugging, and evaluating agentic systems: deterministic testing with mocks, eval frameworks, and AI-powered quality analyzers.

- [x] Introduction -- Rethinking testing by separating deterministic components from stochastic agent behavior
- [x] Historical Perspective -- Evolution from informal debugging through automated testing to non-deterministic ML system evaluation
- [x] Testing -- Classical testing layers adapted for agentic systems with property-based assertions for agent behavior
- [x] Evals -- Turning "this agent seems to work" into repeatable evidence using Cases, Evaluators, and Datasets
- [x] Hands-on: Introduction -- Layered validation: deterministic mocks, string matching, structured outputs, LLM-as-Judge, Doctors
- [x] Hands-on: Deterministic Testing -- Replacing non-deterministic LLMs with ModelMock and tool_mock for controlled testing
- [x] Hands-on: Basic Evals -- Three evaluation approaches: string matching, structured output assertions, and LLM-as-a-Judge
- [x] Hands-on: Pydantic Evals Framework -- Structured abstractions (Cases, Evaluators, Datasets) for maintainable evaluation suites
- [x] Hands-on: Doctors -- AI-powered quality analyzers assessing prompts, tools, MCP servers, A2A cards, and Skills
- [x] References

### Chapter: [Data Sources & Connectors](chapters/data_sources_and_connectors/chapter.md)

Connector abstractions for databases, APIs, and files; NL2SQL with annotated schemas; controlled vocabularies; and private data guardrails.

- [x] Introduction -- Connectors as agent-facing abstractions exposing data sources through stable, safe operations
- [x] Connectors -- Five connector archetypes (file, SQL, OpenAPI, graph, vocabulary) providing generic interfaces to external systems
- [x] NL2SQL -- Controlled execution pattern translating natural language to validated SQL using annotation-rich schemas
- [x] Private Data -- Session-level sensitivity tagging to prevent data exfiltration by blocking unsafe tool calls
- [x] Hands-on: Introduction -- Exercises using FileConnector, NL2SQL+CSV, OpenAPI, VocabularyConnector, and private data guardrails
- [x] Hands-on: File Connector -- Sandbox-isolated file operations through workspace paths managed by contextvars
- [x] Hands-on: NL2SQL with CSV Post-Processing -- Two-agent pipeline querying a database then processing CSV results
- [x] Hands-on: OpenAPI Connector -- Autonomous API discovery and invocation from an ingested OpenAPI spec
- [x] Hands-on: Controlled Vocabularies -- Resolution strategies (exact/fuzzy matching, semantic vector search) for standardized term lookup
- [x] Hands-on: Private Data Guardrails -- External connectivity disabled mid-session after confidential data is loaded
- [x] References

### Chapter: [User Interface](chapters/ui/chapter.md)

Chat UIs with Chainlit and AG-UI protocol, error propagation across distributed layers, session identity, and file uploads.

- [x] Introduction -- Two UI approaches (Chainlit for prototyping, AG-UI for interoperability) and cross-cutting concerns
- [x] Chainlit -- Python chat framework for conversational prototypes with lifecycle hooks and streaming
- [x] AG-UI -- Event-stream protocol decoupling agent backends from frontend clients through typed interaction events
- [x] Error propagation, cancellation, and human-in-the-loop -- How errors and cancellation signals translate across MCP, A2A, PydanticAI, and AG-UI layers
- [x] Session propagation -- JWT tokens propagating user identity across network boundaries (MCP, A2A)
- [x] File Uploads -- Save-to-workspace, summarize-with-context-reader, and tag-as-private-data pattern for file handling
- [x] Hands-on: Introduction -- Two projects: Chainlit chat app and AG-UI app with React frontend
- [x] Hands-on: Chainlit -- Three Chainlit versions: echo, agent, and auth+persistence+tools
- [x] Hands-on: AG-UI Introduction -- AG-UI backend/frontend architecture with three backend versions and React frontend
- [x] Hands-on: AG-UI Backend -- Minimal agent, tools, and state management using PydanticAI with AGUIApp wrapper
- [x] Hands-on: AG-UI Frontend -- React frontend implementation using @ag-ui/client SDK and HttpAgent
- [x] Hands-on: AG-UI Side-Channels -- REST side-channels for file uploads and user feedback alongside the event stream
- [x] References

### Section: Production, Scaling & Enterprise

Into: Introduction to section, what we are building and how

### Chapter: Core Agent (TODO)

- [ ] Core agent
- [ ] CodeAct
- [] Run skills
- [ ] Run sub-agents
- [x] Workspace / Userspace
- [x] MCPs:
  - [x] mcp-todo
  - [x] mcp-file-edit
  - [x] mcp-data-analysis
  - [x] mcp-data-viz
- [ ] A2A servers:
  - [ ] a2a-nl2sql
  - [ ] a2a-data-analysis
  - [ ] a2a-data-viz

### Chapter: [Execution Infrastructure](chapters/execution_infrastructure/chapter.md)

Production infrastructure for running agent-generated code safely: sandbox isolation, REPL, kill switch, MCP server isolation, and skill sandboxing.

- [x] Sandbox -- Process isolation (bubblewrap/subprocess) constraining code execution to prevent unauthorized filesystem and network access
- [x] REPL -- Jupyter-like notebook pattern for iterative code execution in shared stateful environments with persistence and isolation
- [x] Kill Switch -- Binary network isolation (Docker network_mode="none") when private data enters an agent session
- [x] MCP Server Isolation -- Dual-container routing tool calls to isolated vs unrestricted instances based on session data sensitivity
- [x] Skill Sandbox -- Read-only mounted container allowing execution of skill scripts while preventing modifications to the skill library
- [x] Hands-on: MCP Server Isolation -- Interactive notebook demonstrating dual-instance MCP isolation with workspace, permissions, and private data flagging

### Chapter: Research & Science Agents (TODO)

- [ ] A2A: Data analysis
- [ ] Deep research
- [ ] Biomni
- [ ] ....
- [ ] Personas and simulation, Role-playing and multi-perspective reasoning. Debate and arbitration agents
