## Skills Engineering

We discuss making skills discoverable, cheap to advertise to a model, and safe to activate and execute inside a broader agent system.

#### What "engineering skills" actually means

The Agent Skills integration guide is explicit about what a skills-compatible runtime must do: it discovers skill directories, loads only metadata at startup, matches tasks to skills, activates a selected skill by loading full instructions, and then executes scripts and accesses bundled resources as needed. The important architectural point is that integration is designed around progressive disclosure: startup and routing should rely on frontmatter only, while "activation" is the moment you pay to load instructions and any additional files.

The specification formalizes the artifact you are integrating. A skill is a directory with a required `SKILL.md` file and optional `scripts/`, `references/`, and `assets/` directories. The `SKILL.md` file begins with YAML frontmatter that must include `name` and `description`, and may include fields such as `compatibility`, `metadata`, and an experimental `allowed-tools` allowlist. The body is arbitrary Markdown instructions, and the spec notes that the agent loads the whole body only after it has decided to activate the skill.

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

This is not an implementation detail; it is the core performance/safety contract. The integration guide recommends parsing only the frontmatter at startup "to keep initial context usage low." The specification quantifies the intended disclosure tiers: metadata (name/description) is loaded for all skills, full instructions are loaded on activation, and resources are loaded only when required.

#### Filesystem-based integration vs tool-based integration

The Agent Skills guide describes two integration approaches.

In a filesystem-based agent, the model operates in a computer-like environment (bash/unix). A skill is "activated" when the model reads `SKILL.md` directly (the guide's example uses a shell `cat` of the file), and bundled resources are accessed through normal file operations. This approach is "the most capable option" precisely because it does not require you to pre-invent an API for every way the skill might need to read or run something; the skill can ship scripts and references and the runtime can expose them as files.

In a tool-based agent, there is no dedicated computer environment, so the developer implements explicit tools that let the model list skills, fetch `SKILL.md`, and retrieve bundled assets. The guide deliberately does not prescribe the exact tool design ("the specific tool implementation is up to the developer"), which is a reminder not to conflate the skill format with a particular invocation API.

#### Injecting skill metadata into the model context

The guide says to include skill metadata in the system prompt so the model knows what skills exist, and to "follow your platform's guidance" for how system prompts are updated. It then provides a single example: for Claude models, it shows an XML wrapper format. That example is platform-specific and should not be treated as a general recommendation for other runtimes.

The general requirement is simpler: at runtime start (or on refresh), you provide a compact catalog containing at least `name`, `description`, and a way to locate the skill so the runtime can load `SKILL.md` when selected. The integration guide's own pseudocode returns `{ name, description, path }`, which is the essential structure. A neutral, implementation-agnostic representation could be expressed as JSON (or any equivalent internal structure) without implying any particular prompt markup language:

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

The skill system works because selection can be done from the metadata alone; the body is only loaded when the orchestrator commits to activation.

#### Security boundaries during activation

Skill integration changes the risk profile the moment `scripts/` are involved. The specification defines `scripts/` as executable code that agents can run, and explicitly notes that supported languages and execution details depend on the agent implementation. The frontmatter's experimental `allowed-tools` field exists to help some runtimes enforce "pre-approved tools" a skill may use, but support may vary.

For integration, the key design is to treat activation and execution as a controlled transition. Discovery and metadata loading are read-only operations over a directory tree; activation is when the model receives instructions that may request tool use or script execution; execution is when side effects happen. Mapping that to your agent runtime typically means (a) restricting what the model can do before activation, (b) enforcing tool/script policies during execution, and (c) logging what happened in a way that can be audited later. The Skill spec's progressive disclosure guidance is as much about control and review as it is about context budget.
