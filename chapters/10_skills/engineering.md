## Engineering

We discuss making skills discoverable, cheap to advertise to a model, and safe to activate and execute inside a broader agent system.

### What “engineering skills” actually means

The Agent Skills integration guide is explicit about what a skills-compatible runtime must do: it discovers skill directories, loads only metadata at startup, matches tasks to skills, activates a selected skill by loading full instructions, and then executes scripts and accesses bundled resources as needed. ([Agent Skills][64]) The important architectural point is that integration is designed around progressive disclosure: startup and routing should rely on frontmatter only, while “activation” is the moment you pay to load instructions and any additional files. ([Agent Skills][64])

The specification formalizes the artifact you are integrating. A skill is a directory with a required `SKILL.md` file and optional `scripts/`, `references/`, and `assets/` directories. ([Agent Skills][65]) The `SKILL.md` file begins with YAML frontmatter that must include `name` and `description`, and may include fields such as `compatibility`, `metadata`, and an experimental `allowed-tools` allowlist. ([Agent Skills][65]) The body is arbitrary Markdown instructions, and the spec notes that the agent loads the whole body only after it has decided to activate the skill. ([Agent Skills][65])

A minimal discovery and metadata loader therefore looks like:

```python
def discover_skills(skill_roots: list[str]) -> list[dict]:
    skills = []
    for root in skill_roots:
        for skill_dir in list_directories(root):
            if exists(f"{skill_dir}/SKILL.md"):
                fm = extract_yaml_frontmatter(read_file(f"{skill_dir}/SKILL.md"))
                skills.append(
                    {"name": fm["name"], "description": fm["description"], "path": skill_dir}
                )
    return skills
```

This is not an implementation detail; it is the core performance/safety contract. The integration guide recommends parsing only the frontmatter at startup “to keep initial context usage low.” ([Agent Skills][64]) The specification quantifies the intended disclosure tiers: metadata (name/description) is loaded for all skills, full instructions are loaded on activation, and resources are loaded only when required. ([Agent Skills][65])

### Filesystem-based integration vs tool-based integration

The Agent Skills guide describes two integration approaches.

In a filesystem-based agent, the model operates in a computer-like environment (bash/unix). A skill is “activated” when the model reads `SKILL.md` directly (the guide’s example uses a shell `cat` of the file), and bundled resources are accessed through normal file operations. ([Agent Skills][64]) This approach is “the most capable option” precisely because it does not require you to pre-invent an API for every way the skill might need to read or run something; the skill can ship scripts and references and the runtime can expose them as files.

In a tool-based agent, there is no dedicated computer environment, so the developer implements explicit tools that let the model list skills, fetch `SKILL.md`, and retrieve bundled assets. ([Agent Skills][64]) The guide deliberately does not prescribe the exact tool design (“the specific tool implementation is up to the developer”), which is a reminder not to conflate the skill format with a particular invocation API. ([Agent Skills][64])

### Injecting skill metadata into the model context

The guide says to include skill metadata in the system prompt so the model knows what skills exist, and to “follow your platform’s guidance” for how system prompts are updated. ([Agent Skills][64]) It then provides a single example: for Claude models, it shows an XML wrapper format. ([Agent Skills][64]) That example is platform-specific and should not be treated as a general recommendation for other runtimes.

The general requirement is simpler: at runtime start (or on refresh), you provide a compact catalog containing at least `name`, `description`, and a way to locate the skill so the runtime can load `SKILL.md` when selected. The integration guide’s own pseudocode returns `{ name, description, path }`, which is the essential structure. ([Agent Skills][64]) A neutral, implementation-agnostic representation could be expressed as JSON (or any equivalent internal structure) without implying any particular prompt markup language:

```json
{
  "available_skills": [
    {
      "name": "pdf-processing",
      "description": "Extract text and tables from PDF files, fill forms, merge documents.",
      "path": "/skills/pdf-processing"
    }
  ]
}
```

The skill system works because selection can be done from the metadata alone; the body is only loaded when the orchestrator commits to activation. ([Agent Skills][64])

### Security boundaries during activation

Skill integration changes the risk profile the moment `scripts/` are involved. The specification defines `scripts/` as executable code that agents can run, and explicitly notes that supported languages and execution details depend on the agent implementation. ([Agent Skills][65]) The frontmatter’s experimental `allowed-tools` field exists to help some runtimes enforce “pre-approved tools” a skill may use, but support may vary. ([Agent Skills][65])

For integration, the key design is to treat activation and execution as a controlled transition. Discovery and metadata loading are read-only operations over a directory tree; activation is when the model receives instructions that may request tool use or script execution; execution is when side effects happen. Mapping that to your agent runtime typically means (a) restricting what the model can do before activation, (b) enforcing tool/script policies during execution, and (c) logging what happened in a way that can be audited later. The Skill spec’s progressive disclosure guidance is as much about control and review as it is about context budget. ([Agent Skills][65])

### How skills relate to MCP

MCP defines a client/server protocol where servers expose primitives, and “tools” are one of those primitives: executable functions that an AI application can invoke, alongside resources and prompts. ([Model Context Protocol][66]) In MCP terms, tools are meant to be small, schema’d capabilities: file operations, API calls, database queries, and similar discrete actions. ([Model Context Protocol][66])

A skill is not a competing notion of a tool. It is a packaging format for instructions plus optional scripts and references that can orchestrate one or more tools. The clean modularization pattern is to keep MCP tools narrow and reusable, and compose them inside skills where the domain workflow lives. The skill remains stable as an interface and knowledge bundle, while the underlying tool calls are the mechanical substrate that can be reused across many skills.

A concrete way to express that separation is to have a skill instruct the agent to use a database-query tool and then post-process results, without embedding database details into the tool itself:

```markdown
# In SKILL.md body (instructions)

When you need cohort statistics:
1) Use the database query tool to fetch rows for the cohort definition.
2) Compute summary metrics.
3) If a chart is requested, call the charting tool with the computed series.
```

The reuse comes from the fact that the database-query MCP tool stays the same whether it is used by “cohort-analysis”, “data-quality-check”, or “report-generator” skills.

### How skills relate to A2A

The A2A protocol is positioned as an application-level protocol for agents to discover each other, negotiate interactions, manage tasks, and exchange conversational context and complex data as peers. ([a2a-protocol.org][4]) The A2A documentation frames MCP as the domain of “tools and resources” (primitives with structured inputs/outputs, often stateless) and A2A as the domain of “agents” (autonomous systems that reason, plan, maintain state, and conduct multi-turn interaction). ([a2a-protocol.org][4])

Skills align with this split. A skill is a capability package that is typically invoked “tool-like” from the outside: it has a clear name/description for routing, and activation loads instructions that define how to perform the task. ([Agent Skills][65]) Internally, a skill may run a complex workflow and call many tools, but the integration surface is a capability boundary. In an A2A deployment, that boundary can be hosted by a remote agent instead of a local runtime.

The A2A text even notes that an A2A server could expose some of its skills as MCP-compatible resources when they are well-defined and can be invoked in a more tool-like manner, while emphasizing that A2A’s strength is more flexible, stateful collaboration beyond typical tool invocation. ([a2a-protocol.org][4]) This gives a practical integration rule: use skills (and MCP) for capability invocation; use A2A when you need delegation to a peer that will plan, negotiate, and collaborate over time.

### Converting an A2A agent into a skill, and a skill into an A2A agent

A safe way to talk about “conversion” without inventing protocol features is to describe what must remain invariant and what changes.

What should remain invariant is the capability contract: the thing you want to be able to select by name/description, activate with full instructions, and produce outputs from. In skill terms, that contract is represented by `SKILL.md` frontmatter plus its instruction body and any referenced files. ([Agent Skills][65]) In A2A terms, the contract is represented by whatever the remote agent advertises and accepts as task input, together with the task lifecycle semantics A2A provides. ([a2a-protocol.org][4])

Converting an A2A agent into a skill is therefore a packaging move: you take one externally meaningful capability that the agent provides and express it as a skill directory whose `SKILL.md` contains the instructions that the agent previously embodied in code and prompts. The integration consequences are that (a) any long-lived statefulness must be made explicit in inputs or moved up into the orchestrator, and (b) any external dependencies must be declared via `compatibility` and/or enforced via execution policy. ([Agent Skills][65])

Converting a skill into an A2A agent is a hosting move: you take the skill as the unit of work and put it behind an A2A server that offers it to other agents. The skill still remains the internal playbook and resource bundle, while A2A provides the network-level concerns: discovery, negotiation, task lifecycle, and exchange of context/results. ([a2a-protocol.org][4])

The important point is that “conversion” is rarely a literal mechanical transform. It is an architectural refactoring where the skill remains the portable capability artifact, and A2A is the transport and collaboration wrapper when that capability needs to be offered across trust boundaries or organizational boundaries.

## References

1. AgentSkills Working Group. *Integrate skills into your agent*. AgentSkills.io, 2024. [https://agentskills.io/integrate-skills](https://agentskills.io/integrate-skills) ([Agent Skills][64])
2. AgentSkills Working Group. *Specification*. AgentSkills.io, 2024. [https://agentskills.io/specification](https://agentskills.io/specification) ([Agent Skills][65])
3. A2A Protocol Authors. *A2A and MCP*. A2A Protocol, 2025. [https://a2a-protocol.org/latest/topics/a2a-and-mcp/](https://a2a-protocol.org/latest/topics/a2a-and-mcp/) ([a2a-protocol.org][67])
4. Model Context Protocol Authors. *Architecture (Primitives)*. Model Context Protocol, 2025. [https://modelcontextprotocol.io/docs/learn/architecture](https://modelcontextprotocol.io/docs/learn/architecture) ([Model Context Protocol][66])
5. Model Context Protocol Authors. *Architecture (Specification 2025-06-18)*. Model Context Protocol, 2025. [https://modelcontextprotocol.io/specification/2025-06-18/architecture](https://modelcontextprotocol.io/specification/2025-06-18/architecture) ([Model Context Protocol][68])

[64]: https://agentskills.io/integrate-skills "Integrate skills into your agent - Agent Skills"
[65]: https://agentskills.io/specification "Specification - Agent Skills"
[66]: https://modelcontextprotocol.io/docs/learn/architecture?utm_source=chatgpt.com "Architecture overview"
[67]: https://a2a-protocol.org/latest/topics/a2a-and-mcp/ "A2A and MCP - A2A Protocol"
[68]: https://modelcontextprotocol.io/specification/2025-06-18/architecture?utm_source=chatgpt.com "Architecture"
