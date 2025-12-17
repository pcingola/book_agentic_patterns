# Book "Agentic Patterns"

This is a repository for the book "Agentic Patterns", which explores design patterns and best practices for building agentic systems using AI technologies.

# Topics

- What is an Agent / Agentic System


- Basic patterns
  - REACT
  - Tree of Thought
  - Tool Use
  - Self-Reflection


- Workflows
- Graphs

Context engineering:
- tool discovery (mcp/skills)
- how we add files/attachments/knowledge into the context window
- conversation history
- Single-shot/planning/reasoning
- Subagent use
- RAG use
- Memory and state management
- Human-in-the-loop use

- Planning: To do list

- CodeAct
  - REPL
- Memory Management
- Context compresison (same as memory management?)
- Select tools (large toolsets)
  - Pre select tools: decide before execution (e.g. Biomni)
- NL2SQL
    - Select data sources
- Knowledge base
  - Knowledge base consistency (against documents)
- Tool doctor
- Document consistency
  - Iterative consistency (check + fix until there are no more changes)
- CodeIndex
- Private data
  - Blocking outgoing connections
  - Sandboxes
- Skills
  - Progressive disclosure
- Sub Agents (also A2A)
- MCP
- A2A
- Error handling:
  - Propagating from MCPs
  - Propagating from A2As
  - Tool -> MCP -> A2A -> Agent
- Personas (Person/personas simulation)
- Governancce boards: multiple "personas" reviewing actions
- 