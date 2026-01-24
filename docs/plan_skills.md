# Plan: Skills Library (`agentic_patterns/core/skills/`)

Based on the chapter's emphasis on progressive disclosure and the existing core library patterns.

## Components

### 1. `models.py`

Two Pydantic models:

- `SkillMetadata`: name, description, path (the "one-line" view for discovery/catalog)
- `Skill`: full parsed skill including frontmatter dict, body text, and lists of script/reference file paths

### 2. `registry.py`

A `SkillRegistry` class:

- `discover(roots: list[Path])` - scans skill directories, parses YAML frontmatter only, caches `SkillMetadata` list
- `list_all()` - returns cached metadata (cheap, used for catalog injection into system prompt)
- `get(name: str)` - loads and returns full `Skill` (expensive, only on activation)

The registry holds discovered metadata in memory and loads full skills lazily. This is the progressive disclosure mechanism.

### 3. `tools.py`

Two PydanticAI tool functions for agent integration:

- `list_available_skills(registry)` - returns compact one-liner per skill (name + description)
- `get_skill_instructions(registry, name: str)` - returns full SKILL.md body and references

The tools wrap the registry and provide the agent's interface to the skill system. Script execution is not handled here (that's agent integration, delegated to Bash or similar tools that the skill's `allowed-tools` specifies).

## What stays out

- Script execution logic (the agent uses existing Bash/Read tools per the skill's instructions)
- Validation/doctor logic (already exists in `doctors/skill_doctor.py`)
- Complex parsing of references/assets (keep it simple: just return paths or content)

## Key design points

- Frontmatter parsing uses existing YAML approach from `skill_doctor.py`
- Registry is instantiated once and passed to tools (or use a module-level singleton)
- Loading full skill is explicit (agent must call `get_skill_instructions` to "activate")
