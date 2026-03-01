## Hands-On: Skills and Progressive Disclosure

This hands-on explores `example_skills.ipynb`, which demonstrates the three tiers of progressive disclosure using the core skills library. An agent discovers a `checksum` skill from a local directory, activates it to receive instructions, and then runs a bundled script to compute a SHA-256 hash — a result the model cannot produce reliably on its own.

### Setup: Discovering Skills

The `SkillRegistry` scans skill directories and loads only frontmatter at startup:

```python
skills_root = Path("skills-demo")
registry = SkillRegistry()
registry.discover([skills_root])
```

After discovery, the registry holds metadata (name and description) for all skills but has not loaded any instruction bodies. This is Tier 1: cheap enough to advertise all skills in the system prompt without bloating context.

### Tools from the Core Library

`registry.get_all_tools(allow_local=True)` returns the three tools that implement progressive disclosure:

```python
skill_tools = registry.get_all_tools(allow_local=True)
```

- `activate_skill` loads the full `SKILL.md` body into the agent's context (Tier 2)
- `run_skill_script` executes a script bundled with an activated skill (Tier 3)
- `read_skill_resource` reads a reference or asset file from an activated skill (Tier 3)

No custom tool code is needed. The `allow_local=True` flag permits direct subprocess execution for notebooks and demos; in production, a `SandboxManager` is passed instead.

### Observability with SkillEvent

The registry exposes an `on_event` hook for monitoring skill lifecycle events:

```python
def on_skill_event(event: SkillEvent) -> None:
    print(f"  [SKILL {event.event_type.value.upper()}] {event.skill_name}", end="")
    if event.payload:
        details = ", ".join(f"{k}={v}" for k, v in event.payload.items())
        print(f" ({details})")
    else:
        print()

registry.on_event = on_skill_event
```

This makes skill activation, script execution, and resource reads visible in the output, which is essential for debugging and for demonstrating the boundary between tiers.

### The Agent

`registry.system_prompt()` returns the skill catalog formatted and ready to inject into a system prompt:

```python
system_prompt = f"""You are an assistant with access to skills.

{registry.system_prompt()}"""

agent = get_agent(system_prompt=system_prompt, tools=skill_tools)
```

The agent's initial context contains only Tier 1 metadata — names and descriptions — for all discovered skills. Full instructions are not loaded until the agent calls `activate_skill`.

### Running the Agent

The agent is asked to compute a SHA-256 checksum and verify it against known test vectors:

```python
prompt = "Compute the SHA-256 checksum of 'hello world' and verify it against the known test vectors."

agent_run, nodes = await run_agent(agent, prompt, verbose=True)
```

The agent cannot produce a SHA-256 hash from its parameters alone, so it must use the skill. Watch the output for `[SKILL ACTIVATE]`, `[SKILL EXEC]`, and `[SKILL READ]` events printed by the `on_event` hook.

### Three Tiers in Action

1. **Tier 1 — Discovery**: The catalog in the system prompt tells the agent that a `checksum` skill exists and what it does. No instruction body has been loaded.

2. **Tier 2 — Activation**: The agent calls `activate_skill("checksum")`, which loads the full `SKILL.md` body. The agent now knows what scripts and references are available.

3. **Tier 3 — Execution**: The agent calls `run_skill_script("checksum", "checksum.py", "hello world")` to compute the hash, then `read_skill_resource("checksum", "reference", "test_vectors.md")` to load the known test values. It compares the computed hash against the reference and reports the result.

Context is loaded exactly when needed and not before — the progressive disclosure contract enforced at runtime by the core library rather than by custom application code.
