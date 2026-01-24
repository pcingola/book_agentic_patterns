# Hands-On: Doctors

Doctors are AI-powered quality analyzers that evaluate artifacts used in agentic systems: prompts, tools, MCP servers, A2A agent cards, and Agent Skills. Each doctor uses an LLM to assess quality, identify issues, and provide actionable recommendations. This hands-on explores the five doctor types through `example_doctors.ipynb`.

The doctor pattern addresses a common challenge: as agentic systems grow, the quality of their components becomes harder to verify manually. A prompt that seems clear to its author may confuse the model. A tool definition missing type hints forces the model to guess about expected inputs. Doctors automate this quality assessment, catching issues before they cause problems in production.

## The Doctor Architecture

All doctors share a common base class that handles batching and provides a consistent interface:

```python
class DoctorBase:
    async def analyze(self, target: Any, verbose: bool = False) -> Recommendation:
        """Analyze a single target."""

    async def analyze_batch(self, targets: list[Any], batch_size: int = 5, verbose: bool = False) -> list[Recommendation]:
        """Process targets in batches."""
```

The `analyze` method handles a single artifact. The `analyze_batch` method processes multiple artifacts efficiently by grouping them into batches, reducing the number of LLM calls. Each doctor specializes this interface for its artifact type.

Recommendations follow a structured format with severity levels (error, warning, info) and categories (naming, documentation, types, clarity, etc.). The `needs_improvement` flag provides a quick pass/fail signal for CI integration.

## PromptDoctor: Analyzing Prompts

PromptDoctor evaluates prompt templates for clarity, completeness, and potential ambiguity. It extracts placeholders (like `{variable_name}`) and assesses whether the prompt provides sufficient context for the model to produce useful outputs.

```python
bad_prompt = "do the thing with {x}"

doctor = PromptDoctor()
result = await doctor.analyze(bad_prompt)
```

This prompt fails multiple quality checks. The instruction "do the thing" is vague, `{x}` lacks semantic meaning, and there's no context about expected output format. The doctor identifies these issues and suggests improvements.

A well-crafted prompt provides context, clear instructions, and output format guidance:

```python
good_prompt = """You are a technical writer. Summarize the following document in 3 bullet points.

Document:
{document}

Respond with exactly 3 bullet points, each starting with a dash."""
```

This prompt establishes role (technical writer), defines the task (summarize), provides input structure (document placeholder), and specifies output format (3 bullet points with dashes). The doctor validates these elements and confirms the prompt is well-structured.

PromptDoctor can also analyze prompt files directly by passing a `Path` object. This integrates naturally into CI pipelines where prompts are stored as markdown files in a `prompts/` directory.

## ToolDoctor: Analyzing Tool Functions

ToolDoctor examines Python function definitions that serve as agent tools. It checks for proper naming, type hints, docstrings, and argument documentation.

```python
def do_stuff(x):
    """Does stuff."""
    return x

doctor = ToolDoctor()
result = await doctor.analyze(do_stuff)
```

This tool definition has multiple issues: the name `do_stuff` is non-descriptive, parameter `x` lacks a type hint, the docstring doesn't explain what the function actually does, and the return type is unspecified. When an LLM encounters this tool, it must guess about usage, leading to errors or misuse.

A properly defined tool provides all the information the model needs:

```python
def search_database(query: str, limit: int = 10) -> list[dict]:
    """Search the database for records matching the query.

    Returns a list of matching records, each containing 'id', 'name', and 'score' fields.
    """
    return []
```

The function name describes its purpose. Parameters have types and sensible defaults. The docstring explains both behavior and return value structure. The return type annotation completes the interface definition. The model can use this tool confidently because all necessary information is explicit.

## MCPDoctor: Analyzing MCP Server Tools

MCPDoctor connects to an MCP (Model Context Protocol) server and analyzes all exposed tools. This extends tool analysis to external services that provide tools via the MCP protocol.

```python
from pydantic_ai.mcp import MCPServerStdio

mcp_server = MCPServerStdio(command="fastmcp", args=["run", "-t", "stdio", "mcp_server_bad.py"])

doctor = MCPDoctor(mcp_server)
results = await doctor.analyze_all()
```

The doctor connects to the server, discovers its tools, and analyzes each one. The example servers demonstrate the contrast:

The poorly defined server (`mcp_server_bad.py`):
```python
@mcp.tool()
def do_thing(x):
    """Does thing."""
    return x
```

The well-defined server (`mcp_server_good.py`):
```python
@mcp.tool()
def add_numbers(a: int, b: int) -> int:
    """Add two integers and return the sum."""
    return a + b
```

MCPDoctor applies the same quality criteria as ToolDoctor, but operates on remote tools rather than local functions. This enables quality gates for third-party MCP servers before integrating them into an agent.

## A2ADoctor: Analyzing Agent Cards

A2ADoctor evaluates agent cards, the metadata that A2A (Agent-to-Agent) servers expose at `/.well-known/agent-card.json`. Agent cards describe an agent's capabilities, skills, and interface, enabling other agents to discover and interact with it.

```python
doctor = A2ADoctor()
result = await doctor.analyze("http://127.0.0.1:8001")
```

The doctor fetches the agent card from the server and analyzes its contents. A poorly defined agent card might have:

```python
app = agent.to_a2a(name="helper", description="helps")
```

This tells other agents almost nothing. The name is generic, the description is uninformative, and skills aren't explicitly defined.

A well-defined agent card provides comprehensive metadata:

```python
app = agent.to_a2a(
    name="calculator",
    description="A calculator agent that performs basic arithmetic operations: addition, subtraction, multiplication, and division.",
    skills=skills,
)
```

The description explains what the agent does. Skills are explicitly listed with their own names, descriptions, and tags. Other agents can make informed decisions about when and how to delegate tasks.

## SkillDoctor: Analyzing Agent Skills

SkillDoctor analyzes Agent Skills (agentskills.io format) for compliance and quality. Agent Skills are self-contained packages that provide agents with capabilities, similar to how MCP servers expose tools but focused on agent-executable instructions and scripts.

```python
skill_dir = Path("skill-bad")

doctor = SkillDoctor()
result = await doctor.analyze(skill_dir)
```

The doctor validates multiple aspects of a skill. First, it checks the directory structure: skills must contain a `SKILL.md` file with YAML frontmatter, and may optionally include `scripts/`, `references/`, and `assets/` directories. Files placed directly in the skill root (other than SKILL.md and LICENSE) violate the specification.

Second, it validates the frontmatter metadata. The `name` field must be lowercase alphanumeric with hyphens and match the directory name. The `description` field should explain what the skill does and when to use it. A poorly defined skill might have:

```yaml
---
name: BadSkill
description: Does stuff
---

Use this skill.
```

This fails multiple checks: the name uses incorrect casing and does not match the directory name, the description is too vague, and the body provides no useful instructions.

Third, the doctor analyzes each script in the `scripts/` directory, checking for proper documentation, error handling, and consistency with the SKILL.md description. If a script exists but is not documented in SKILL.md, or if SKILL.md references a script that does not exist, the doctor flags these inconsistencies.

A well-defined skill provides comprehensive metadata and clear instructions:

```yaml
---
name: skill-good
description: A code formatting skill that counts lines and words in text files. Use this skill when you need basic file statistics.
compatibility: Works with any text files.
---

# File Statistics Skill

This skill provides basic statistics for text files.

## Available Scripts

### stats.py

Counts lines, words, and characters in a text file. Accepts a file path as argument and prints the counts.
```

The name follows the specification format and matches the directory. The description explains both what the skill does and when to use it. Scripts are documented with usage examples and expected output. The accompanying script includes a docstring, type hints, and proper error handling.

## CLI Integration

Doctors are available as command-line tools for CI/CD integration:

```bash
# Analyze prompt files
python -m agentic_patterns.core.doctors prompt prompts/system.md

# Analyze tools from a Python module
python -m agentic_patterns.core.doctors tool my_module:my_tools

# Analyze MCP server tools
python -m agentic_patterns.core.doctors mcp --stdio "fastmcp run server.py"

# Analyze A2A agent cards
python -m agentic_patterns.core.doctors a2a http://localhost:8001

# Analyze Agent Skills
python -m agentic_patterns.core.doctors skill ./my-skill/
```

Each command returns a non-zero exit code if any artifact needs improvement, enabling use as a quality gate in CI pipelines. The `--verbose` flag provides detailed output for debugging.

## When to Use Doctors

Doctors fit naturally into development workflows at several points.

During development, run doctors interactively to get feedback on new prompts, tools, and skills. The immediate feedback loop helps catch issues early, before they propagate into agent behavior.

In code review, doctor output provides objective quality metrics. Rather than debating whether a docstring is "good enough," the doctor's structured analysis offers concrete improvement suggestions.

In CI pipelines, doctors serve as quality gates. A failing doctor check blocks deployment until the issues are addressed, preventing poorly defined artifacts from reaching production.

For third-party integrations, MCPDoctor and A2ADoctor evaluate external services before connecting them to your agents. This guards against integrating poorly documented tools that might confuse your agent or produce unreliable results.

## Limitations

Doctors use an LLM to assess quality, which introduces non-determinism. The same artifact might receive slightly different assessments across runs. For critical decisions, run doctors multiple times or use the structured `needs_improvement` flag rather than individual issue details.

The quality criteria are encoded in prompt templates (stored in `prompts/doctors/`). These templates embody opinions about what constitutes good prompts, tools, agent cards, and skills. Organizations may need to customize these templates to align with their specific standards.

Doctor analysis adds latency and cost, as each analysis requires an LLM call. For large codebases, consider running doctors only on changed files rather than the entire codebase.
