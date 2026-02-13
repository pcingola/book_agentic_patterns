## Hands-On: Skills and Progressive Disclosure

This hands-on explores skills through `example_skills.ipynb`, demonstrating how an agent discovers available skills, activates one based on the task, and uses its tools.

### Skill Structure

A skill is a directory containing a `SKILL.md` file with YAML frontmatter and markdown body:

```
code-review/
  SKILL.md
  references/
    REFERENCE.md
```

The frontmatter provides machine-readable metadata:

```yaml
---
name: code-review
description: Review code for quality, bugs, and security issues.
compatibility: Works with Python, JavaScript, and TypeScript files.
---
```

The body contains instructions the agent follows when the skill is activated. This separation is the foundation of progressive disclosure: frontmatter is cheap to load for all skills, while the body is loaded only on demand.

### Discovery: The Cheap Operation

The `SkillRegistry` scans skill directories and extracts only frontmatter:

```python
skills_root = Path("skills-demo")
registry = SkillRegistry()
registry.discover([skills_root])
```

After discovery, the registry holds metadata for all skills but has not loaded any instruction bodies. This is the first tier of progressive disclosure. The agent can see what capabilities exist without paying the token cost for instructions it may never use.

The `list_available_skills` function formats this metadata for injection into a system prompt:

```python
skill_catalog = list_available_skills(registry)
```

This produces a compact one-liner per skill, suitable for the agent's initial context.

### Activation: The Expensive Operation

When the agent needs a skill, it calls `activate_skill`:

```python
def activate_skill(skill_name: str) -> str:
    instructions = get_skill_instructions(registry, skill_name)
    if instructions is None:
        return f"Skill '{skill_name}' not found."
    activated_skills.add(skill_name)
    print(f"[SKILL ACTIVATED: {skill_name}]")
    return instructions
```

This loads the full `SKILL.md` body and returns it to the agent. The `[SKILL ACTIVATED]` marker makes this transition visible in the output. Activation is the second tier: the agent now has detailed instructions for this specific capability.

### Gated Tools

Skills can provide tools that only work after activation. In the example, `analyze_code` checks whether the code-review skill is active:

```python
def analyze_code(code: str) -> str:
    if "code-review" not in activated_skills:
        return "Error: You must activate the 'code-review' skill first."
    print(f"[SKILL TOOL CALLED: analyze_code]")
    # ... analysis logic
```

This gating enforces the progressive disclosure pattern at runtime. The agent cannot skip activation and jump directly to using tools. The `[SKILL TOOL CALLED]` marker shows when the skill's capability is actually exercised.

### The Agent Flow

The system prompt tells the agent about skills and how to use them:

```python
system_prompt = f"""You are an assistant with access to skills.

Available skills:
{skill_catalog}

To use a skill:
1. Call activate_skill(skill_name) to load its instructions
2. Read the instructions to understand what tools are available
3. Use the skill's tools (e.g., analyze_code for code-review)

You must activate a skill before using its tools."""
```

When the agent receives a code review task, it recognizes the match with the code-review skill, activates it to get instructions, then uses `analyze_code` to perform the actual analysis. The output shows this sequence clearly through the activation and tool call markers.

### Key Takeaways

Gating tools behind activation enforces the progressive disclosure pattern at runtime and makes skill usage visible in the execution trace. The `[SKILL ACTIVATED]` and `[SKILL TOOL CALLED]` markers demonstrate the clear boundary between discovery, activation, and execution.
