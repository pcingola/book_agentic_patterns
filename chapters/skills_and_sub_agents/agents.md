## AGENTS.md

### Background and Purpose

As autonomous coding agents became more common, teams needed a way to convey stable, project-specific expectations that go beyond what can be reliably handled through transient prompts. Runtime instructions are ephemeral, model-dependent, and often incomplete when agents explore large or unfamiliar repositories. This gap led to the emergence of a repository-level convention for guiding agent behavior.

In practice, this convention is most widely known today as **CLAUDE.md**, following its adoption and popularization by Claude Code. The more general name **AGENTS.md** reflects an effort to make the pattern model- and vendor-agnostic. Both names refer to the same underlying idea: a durable, version-controlled document that communicates how AI agents are expected to behave when operating inside a codebase.

### What the File Represents

AGENTS.md (or CLAUDE.md) is a Markdown file placed at the root of a repository that encodes expectations for AI agents. Unlike a README, which explains the project to humans, this document explains the project to machines. It captures conventions, constraints, and guidance that should always be in scope when an agent reasons about the repository.

Conceptually, it functions as a persistent system prompt tied to the workspace rather than to a specific execution. Because it lives in version control, it can be reviewed, evolved, and audited alongside code, making changes to agent behavior explicit rather than implicit.

### Passive Context versus Explicit Skills

A useful lens for understanding this pattern comes from recent evaluations comparing passive repository context to explicit, on-demand skills. In experiments reported by Vercel, embedding concise, project-specific guidance directly in AGENTS.md consistently outperformed skill-based approaches that required the agent to decide when to fetch or invoke additional instructions.

The key difference is availability. Content in AGENTS.md is always present, eliminating decision points about whether auxiliary knowledge should be loaded. This reduces failure modes related to missed skill invocation and sequencing errors, especially in routine coding tasks such as applying framework conventions, respecting architectural boundaries, or running the correct validation steps.

While this observation may not generalize to all domains, it highlights an important design principle: stable, high-value context often works best when it is passive and unavoidable, rather than conditional.

### Role in Skills and Sub-agent Architectures

Within a system composed of multiple skills or sub-agents, AGENTS.md serves as a shared behavioral contract. Instead of duplicating project norms across prompts or skill definitions, the repository itself advertises the expectations that all agents must respect. Generalist agents can specialize automatically by reading the file, while narrowly scoped sub-agents inherit the same constraints without additional configuration.

This separation keeps skills reusable and generic, while the workspace encodes project-specific policy. In that sense, AGENTS.md complements skills rather than replacing them: skills provide capabilities, while AGENTS.md defines the environment in which those capabilities are exercised.

### Limitations

AGENTS.md is intentionally lightweight. It provides guidance, not enforcement, and assumes agents are designed to respect repository conventions. It also raises practical questions around context size and maintenance discipline, especially if teams attempt to embed large amounts of documentation. Nevertheless, its simplicity is a major reason for its rapid adoption: adding a single Markdown file is far easier than designing and integrating a custom skill system.

As agentic tooling evolves, AGENTS.md represents a pragmatic pattern for externalizing stable behavioral expectations into the workspace itself, where both humans and machines can inspect and evolve them.

### References

1. Jude Gao. *AGENTS.md outperforms skills in our agent evals*. Vercel Blog, 2026. [https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals](https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals)
2. agents.md Contributors. *AGENTS.md: A Convention for Guiding AI Agents in Repositories*. GitHub, 2024. [https://agents.md](https://agents.md)
