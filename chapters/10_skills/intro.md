## Skills

Skills are structured, reusable capability abstractions that encapsulate complex behavior behind a minimal, declarative interface, revealing detail only when it is needed.

### Historical perspective

The intellectual roots of skills predate large language models. Classical AI planning introduced hierarchical task decomposition, where high-level goals were achieved by invoking abstract operators that expanded into concrete actions only during execution. In parallel, software engineering converged on similar ideas through procedures, modules, and APIs, all designed to hide implementation details behind stable contracts.

With the emergence of LLM-based agents, these ideas resurfaced in a new form. Early systems relied heavily on long prompts and explicit step-by-step instructions, but this quickly proved brittle and expensive in terms of tokens. As tool use and function calling became common, practitioners observed that exposing *all* tools and instructions at once degraded model performance. Skills emerged as a response: a way to combine abstraction, modularity, and context efficiency into a single concept, tailored specifically to the constraints of probabilistic language models.

### Core concept

A skill defines **what a capability does**, **when it should be used**, and **what inputs and outputs are expected**, while deliberately omitting *how* it is implemented. The internal mechanics—scripts, heuristics, sub-tools, or even sub-agents—are hidden unless the agent explicitly needs them.

This separation has three immediate benefits. First, it reduces cognitive and token load on the model, improving reliability. Second, it creates reusable building blocks that can be shared across agents and systems. Third, it establishes clear reasoning boundaries: the model reasons about *selecting* and *composing* skills, not about low-level execution details.

### Progressive disclosure and context efficiency

Progressive disclosure is the defining design principle behind skills. Instead of loading all instructions and references into the model context upfront, information is revealed incrementally.

At discovery time, the agent may only see a skill’s name and short description. When the skill is selected, its main instructions are loaded. Only if the agent needs deeper guidance—edge cases, background knowledge, or operational details—are additional reference files consulted. This staged reveal is essential even for models with large context windows: performance degrades long before hard limits are reached.

In practice, progressive disclosure is not an optimization; it is a prerequisite for scalable agent systems.

### A spec-aligned skill example

The AgentSkills specification formalizes skills as directories with a required `SKILL.md` file written in Markdown, optionally accompanied by scripts and reference material. The Markdown file serves as the primary interface between the agent and the skill.

A minimal, spec-aligned skill layout looks like this:

```
pdf-processing/
  SKILL.md
  scripts/
    extract_text_and_tables.py
  references/
    REFERENCE.md
```

The `SKILL.md` file combines structured metadata with natural-language instructions:

```md
---
name: pdf-processing
description: Extract text and tables from PDF files.
allowed-tools: Bash(python:*) Read
---

# PDF Processing

## When to use this skill
Use this skill when the task involves reading, extracting, or transforming content from PDF documents.

## How to use
For standard extraction, run the bundled script:
`scripts/extract_text_and_tables.py <file.pdf>`

## Output
Return extracted text with page numbers and any detected tables in a structured format.

## Notes
If you encounter scanned PDFs or complex layouts, consult the reference file.
```

Several important ideas are illustrated here. The YAML frontmatter provides machine-readable metadata for discovery and policy enforcement. The Markdown body provides human-readable guidance for the agent. Crucially, implementation details are *not* embedded inline; they are delegated to scripts and references that are only loaded if needed.

A corresponding script might look like this (simplified for illustration):

```python
def extract(pdf_path: str) -> dict:
    # Implementation details live here, not in the prompt
    return {"text": [], "tables": []}
```

The agent never needs to reason about how extraction works unless explicitly instructed to inspect or modify the implementation.

### Skills versus tools and prompts

A tool is typically a thin wrapper around an external operation. A prompt is static text. A skill is neither. It is a *capability contract* that may orchestrate tools, enforce invariants, and embed domain knowledge, while remaining opaque by default.

From the agent’s perspective, invoking a skill is an act of intent: *“I want this outcome.”* The skill handles execution. This division allows planning and execution to scale independently.

### Skills as reasoning boundaries

Beyond modularity, skills act as constraints on agent reasoning. By limiting the exposed surface area of capabilities, designers reduce misuse, prompt injection risks, and accidental complexity. Planning becomes a matter of selecting and sequencing skills rather than inventing procedures on the fly, making agent behavior more interpretable and auditable.

As agent systems grow, skills increasingly define the action vocabulary of the agent.

### References

1. AgentSkills Initiative. *What Are Skills?* AgentSkills.io, 2024. [https://agentskills.io/what-are-skills](https://agentskills.io/what-are-skills)
2. AgentSkills Initiative. *Skill Specification*. AgentSkills.io, 2024. [https://agentskills.io/specification](https://agentskills.io/specification)
3. Anthropic. *Claude Skills Documentation*. Anthropic, 2024. [https://code.claude.com/docs/en/skills](https://code.claude.com/docs/en/skills)
