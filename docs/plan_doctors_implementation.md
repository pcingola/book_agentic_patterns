# Doctor Architecture Implementation Plan

The doctors module provides AI-powered review capabilities for prompts, tools, MCP servers, and A2A agent cards. Each doctor analyzes artifacts for clarity, documentation quality, proper typing, and naming conventions, providing actionable improvement suggestions.

## Directory Structure

```
agentic_patterns/core/doctors/
    __init__.py
    models.py           # Shared Pydantic models for recommendations
    base.py             # Base doctor class with batching logic
    prompt_doctor.py    # Prompt review
    tool_doctor.py      # Tool signature review
    mcp_doctor.py       # MCP server tool review
    a2a_doctor.py       # Agent-to-agent card review
    __main__.py         # Unified CLI entry point

prompts/doctors/
    tool_doctor.md
    prompt_doctor.md
    a2a_doctor.md
```

## Shared Models (`models.py`)

```python
class IssueLevel(str, Enum):
    ERROR = "error"      # Must fix
    WARNING = "warning"  # Should fix
    INFO = "info"        # Suggestion

class IssueCategory(str, Enum):
    NAMING = "naming"
    DOCUMENTATION = "documentation"
    TYPES = "types"
    ARGUMENTS = "arguments"
    RETURN_TYPE = "return_type"
    CLARITY = "clarity"
    COMPLETENESS = "completeness"
    AMBIGUITY = "ambiguity"
    CAPABILITIES = "capabilities"
    ENDPOINTS = "endpoints"

class Issue(BaseModel):
    level: IssueLevel
    category: IssueCategory
    message: str
    suggestion: str | None = None

class Recommendation(BaseModel):
    name: str
    needs_improvement: bool
    issues: list[Issue]
```

Specific models extend `Recommendation`:

- `ToolRecommendation` - adds `arguments: list[ArgumentRecommendation]`, return type details
- `PromptRecommendation` - prompt-specific fields
- `A2ARecommendation` - capability, skill, endpoint details

## Base Pattern with Batching (`base.py`)

Common batching logic that all doctors inherit:

```python
class DoctorBase:
    default_batch_size: int = 5

    async def analyze_batch(
        self,
        targets: list[Any],
        batch_size: int | None = None,
        verbose: bool = False
    ) -> list[Recommendation]:
        """Process targets in batches to avoid overwhelming the model."""
        batch_size = batch_size or self.default_batch_size
        results = []
        for i in range(0, len(targets), batch_size):
            batch = targets[i:i + batch_size]
            batch_results = await self._analyze_batch_internal(batch)
            results.extend(batch_results)
        return results

    async def _analyze_batch_internal(self, batch: list[Any]) -> list[Recommendation]:
        """Subclasses implement this for actual analysis."""
        raise NotImplementedError
```

## Doctor Implementations

### ToolDoctor (`tool_doctor.py`)

Library function: `tool_doctor(tools: list[Callable], batch_size: int = 5) -> list[ToolRecommendation]`

Accepts Python callable functions and analyzes: name, docstring, argument types/names/descriptions, return type.

### PromptDoctor (`prompt_doctor.py`)

Library function: `prompt_doctor(prompts: list[str | Path], batch_size: int = 5) -> list[PromptRecommendation]`

Analyzes: clarity, completeness, ambiguity, placeholder consistency, instruction quality.

### MCPDoctor (`mcp_doctor.py`)

Library function: `mcp_doctor(server: MCPServerHTTP | MCPServerStdio | str, batch_size: int = 5) -> list[ToolRecommendation]`

Connects to MCP server, retrieves tool schemas, analyzes them in batches. Supports both HTTP and stdio MCP servers.

### A2ADoctor (`a2a_doctor.py`)

Library function: `a2a_doctor(agents: list[str | AgentCard], batch_size: int = 5) -> list[A2ARecommendation]`

Connects to agents, retrieves agent cards, analyzes capabilities/skills in batches. Analyzes: agent name, description, capabilities, skill definitions, endpoint clarity.

## CLI Design (`__main__.py`)

Unified CLI entry point:

```bash
python -m agentic_patterns.core.doctors [SUBCOMMAND] [OPTIONS]

Common options:
    --batch-size N    Process N items per batch (default: 5)
    --verbose         Show detailed output

Subcommands:
    tool      Analyze tool functions from a Python module
    prompt    Analyze prompt file(s)
    mcp       Analyze tools from an MCP server
    a2a       Analyze agent-to-agent card(s)

Examples:
    python -m agentic_patterns.core.doctors prompt prompts/system.md
    python -m agentic_patterns.core.doctors tool my_module:my_tools --batch-size 3
    python -m agentic_patterns.core.doctors mcp --url http://localhost:8000/mcp
    python -m agentic_patterns.core.doctors mcp --stdio "uv run mcp_server.py"
    python -m agentic_patterns.core.doctors a2a http://localhost:8001/.well-known/agent.json
```

## Key Design Decisions

1. **IssueCategory enum** - Explicit enumeration of issue categories for type safety and consistency

2. **Batching in base class** - All doctors inherit batching logic with configurable batch size (default: 5)

3. **Async-first** - Following the existing pattern in the codebase

4. **Factory pattern** - Use `get_agent()` from core agents module for model creation

5. **Prompt-based** - Store prompts in markdown files, not inline strings

6. **CLI uses argparse subcommands** - Following the evals module pattern

7. **Non-nitpicky** - Focus on concrete problems (errors, warnings) rather than style preferences

## Implementation Order

1. `models.py` - Shared models (Issue, IssueLevel, IssueCategory, Recommendation, ToolRecommendation, etc.)
2. `base.py` - Base doctor class with batching
3. `tool_doctor.py` - Tool doctor implementation
4. `prompts/doctors/tool_doctor.md` - Tool doctor prompt
5. `mcp_doctor.py` - MCP doctor (reuses tool analysis)
6. `prompt_doctor.py` - Prompt doctor
7. `prompts/doctors/prompt_doctor.md` - Prompt doctor prompt
8. `a2a_doctor.py` - A2A doctor
9. `prompts/doctors/a2a_doctor.md` - A2A doctor prompt
10. `__main__.py` - Unified CLI
11. `__init__.py` - Public exports
