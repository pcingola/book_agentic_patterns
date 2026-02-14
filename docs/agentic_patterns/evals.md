# Evals

The library provides three layers for verifying agent behavior: deterministic testing utilities for unit tests without LLM calls, an evaluation framework for measuring agent quality with real models, and doctor tools for analyzing the quality of prompts, tools, MCP servers, A2A cards, and skills.

Testing utilities live in `agentic_patterns.testing`. The eval framework lives in `agentic_patterns.core.evals`. The doctors CLI lives in `agentic_patterns.core.doctors`.


## Deterministic Testing

### ModelMock

`ModelMock` is a drop-in replacement for real LLM models that returns predefined responses sequentially. It implements the PydanticAI `Model` interface, so agents use it without modification.

```python
from pydantic_ai.messages import ToolCallPart
from agentic_patterns.testing import ModelMock

model = ModelMock(responses=[
    ToolCallPart(tool_name="search", args={"query": "test"}),
    "The answer is 42.",
])

agent = get_agent(model=model, tools=[search])
agent_run, _ = await run_agent(agent, "Find the answer")
```

Each call to the model consumes the next response from the list. The agent keeps calling the model until it receives a text response (not a `ToolCallPart`), so responses typically alternate between tool calls and text.

Response items can be: `str` (text), `TextPart`, `ToolCallPart`, `list[str | TextPart | ToolCallPart]` (multiple parts in one response), `MockFinishReason` (custom finish reason), `Exception` (raised on consumption), or `Callable` (called with `(model, messages)` to generate a response dynamically).

For agents with structured output types (`output_type=MyModel`), use `final_result_tool()` to create the tool call that PydanticAI expects:

```python
from agentic_patterns.testing import ModelMock, final_result_tool

class Analysis(BaseModel):
    summary: str

model = ModelMock(responses=[
    ToolCallPart(tool_name="analyze", args={"data": "xyz"}),
    final_result_tool(Analysis(summary="All clear")),
])
```

Properties: `last_message` (last `ModelResponse`), `last_message_part` (last part of the response).

### tool_mock

`tool_mock()` creates a mock version of a tool function that returns predefined values sequentially while tracking call statistics.

```python
from agentic_patterns.testing import tool_mock

mocked_search = tool_mock(search, return_values=[["result1"], ["result2"]])

agent = get_agent(model=model, tools=[mocked_search])
agent_run, _ = await run_agent(agent, "Search twice")

assert mocked_search.call_count == 2
assert mocked_search.was_called
assert mocked_search.call_args_list[0] == ((), {"query": "test"})
```

The returned `ToolMockWrapper` preserves the original function's name and docstring (via `functools.update_wrapper`), so PydanticAI sees it as the original tool. It supports both sync and async functions automatically.

Properties: `call_count` (int), `was_called` (bool), `call_args_list` (list of `(args, kwargs)` tuples). Call `reset()` to clear state and restore original return values. Raises `IndexError` if called more times than there are return values.

### AgentMock

`AgentMock` replays previously recorded agent nodes for testing code that iterates over agent execution without re-running the agent.

```python
from agentic_patterns.testing import AgentMock

mock = AgentMock(nodes=[node1, node2], result_output="final answer")
async with mock.iter() as run:
    async for node in run:
        process(node)
print(run.result.output)  # "final answer"
```


## Evaluation Framework

The eval framework builds on `pydantic_evals` and adds agent-specific evaluators, auto-discovery of eval files, and a CLI runner. All imports are available from `agentic_patterns.core.evals`.

### Writing an eval file

Eval files follow naming conventions for auto-discovery. Place them in an evals directory as `eval_*.py`. Each file must contain exactly one `target_*` function, one or more `dataset_*` objects, and optionally `scorer_*` functions.

```python
# evals/eval_search.py
from agentic_patterns.core.evals import Case, Dataset, Contains, ToolWasCalled

async def target_search(inputs: str) -> str:
    """The function being evaluated -- runs the agent."""
    agent_run, _ = await run_agent(agent, inputs)
    return agent_run.result.output

dataset_basic = Dataset(
    cases=[
        Case(name="simple_query", inputs="What is Python?", expected_output="programming"),
        Case(name="complex_query", inputs="Explain recursion", expected_output="function"),
    ],
    evaluators=[Contains(), ToolWasCalled(tool_name="search")],
)

def scorer_strict(report, min_assertions):
    """Custom pass/fail logic."""
    return average_assertions(report, min_assertions)
```

### Built-in evaluators (from pydantic_evals)

`EqualsExpected()` -- exact match against `expected_output`. `Contains()` -- substring check. `IsInstance(type_name=...)` -- type check. `MaxDuration(seconds=...)` -- latency constraint. `LLMJudge(rubric=...)` -- uses another model to grade the output. `HasMatchingSpan(...)` -- checks the execution span tree.

### Custom evaluators

The library provides four agent-specific evaluators:

`OutputContainsJson()` -- validates that the output is parseable JSON.

`ToolWasCalled(tool_name="search")` -- checks if a specific tool was called during execution by searching the span tree.

`NoToolErrors()` -- verifies no tool calls resulted in errors by recursively scanning the span tree for error statuses.

`OutputMatchesSchema(schema=MyModel)` -- validates output against a Pydantic model or dict schema. Accepts both `type[BaseModel]` and `dict` (checks key presence). Automatically parses JSON strings.

All evaluators implement the `Evaluator` protocol and return `EvaluationReason(value=True|False, reason="...")`.

### Running evals

**CLI:**

```bash
python -m agentic_patterns.core.evals --evals-dir evals/
python -m agentic_patterns.core.evals --filter search --min-assertions 0.8 --verbose
```

The `evals` console script (installed via pyproject.toml) provides the same interface.

Options: `--evals-dir PATH` (default: `evals`), `--filter TEXT` (match by module/file/dataset name), `--min-assertions FLOAT` (default: 1.0), `--include-input`, `--include-output`, `--include-reasons`, `--include-evaluator-failures`, `--verbose`. Exit code 0 on all pass, 1 on any failure.

**Programmatic:**

```python
from agentic_patterns.core.evals import (
    find_eval_files, discover_datasets, run_all_evaluations, PrintOptions
)

files = find_eval_files(Path("evals"))
datasets = discover_datasets(files, name_filter="search")
success = await run_all_evaluations(datasets, PrintOptions())
```

### Discovery mechanics

`find_eval_files(evals_dir)` finds all `eval_*.py` files in the directory.

`discover_datasets(eval_files, name_filter)` loads each file, finds `dataset_*` instances (must be `Dataset`), pairs them with the single `target_*` function, collects `scorer_*` functions, and returns `DiscoveredDataset` bundles. Files with zero or more than one `target_*` function are skipped.

`DiscoveredDataset` holds `dataset`, `target_func`, `scorers`, `name` (e.g., `eval_search.dataset_basic`), and `file_path`.

### Scoring

When a `DiscoveredDataset` has custom `scorer_*` functions, all must return `True` for the evaluation to pass. Each scorer receives `(report: EvaluationReport, min_assertions: float)`. When no custom scorers exist, the default `average_assertions(report, min_assertions)` checks that the average assertion score meets the threshold.


## Doctors

Doctors are CLI tools that use an LLM to analyze the quality of agent artifacts and return structured recommendations. Run via `python -m agentic_patterns.core.doctors` or the installed `doctors` console script.

### ToolDoctor

Analyzes tool function signatures, type hints, docstrings, and parameter documentation.

```bash
doctors tool my_module:my_tools
```

Programmatic:

```python
from agentic_patterns.core.doctors import ToolDoctor

doctor = ToolDoctor()
rec = await doctor.analyze(my_tool_function)
if rec.needs_improvement:
    for issue in rec.issues:
        print(f"[{issue.level}] {issue.category}: {issue.message}")
```

Returns `ToolRecommendation` with `issues`, `arguments` (list of `ArgumentRecommendation`), and `return_type_issues`.

### PromptDoctor

Analyzes prompt templates for clarity, completeness, and context.

```bash
doctors prompt prompts/coordinator.md prompts/analyst.md
```

Accepts string prompts or file paths. Returns `PromptRecommendation` with `issues` and `placeholders_found`.

### MCPDoctor

Connects to an MCP server, discovers all tools, and analyzes each one.

```bash
doctors mcp --url http://localhost:8000
doctors mcp --stdio "uv run server.py"
```

Returns a list of `ToolRecommendation` for each tool exposed by the server.

### A2ADoctor

Analyzes A2A agent cards for completeness and quality.

```bash
doctors a2a http://localhost:8001
```

Accepts agent card URLs or `AgentCard` objects. Returns `A2ARecommendation` with `capabilities` and `skills` (list of `SkillRecommendation`).

### SkillDoctor

Validates Agent Skills against the specification (directory structure, frontmatter, body, scripts).

```bash
doctors skill ./my-skill
doctors skill ./skills-dir --all
```

Returns `AgentSkillRecommendation` with `frontmatter_issues`, `body_issues`, `structure_issues`, `consistency_issues`, `scripts` (list of `ScriptRecommendation`), and `references`.

### Issue model

All doctors return recommendations containing `Issue` objects:

```python
class Issue(BaseModel):
    level: IssueLevel    # ERROR, WARNING, INFO
    category: IssueCategory  # AMBIGUITY, ARGUMENTS, CLARITY, COMPLETENESS, ...
    message: str
    suggestion: str | None
```

The `needs_improvement` field on any recommendation is `True` when issues of level `ERROR` or `WARNING` are present.

### Batch analysis

All doctors support batch analysis with configurable batch size:

```python
recs = await doctor.analyze_batch(targets, batch_size=5)
```

The convenience functions `tool_doctor()`, `prompt_doctor()`, `mcp_doctor()`, `a2a_doctor()`, and `skill_doctor()` wrap the class APIs for quick one-shot analysis.


## API Reference

### `agentic_patterns.testing`

| Name | Kind | Description |
|---|---|---|
| `ModelMock(responses, sleep_time)` | Class | Drop-in LLM model returning predefined responses |
| `MockFinishReason(reason, response)` | Class | Custom finish reason wrapper |
| `final_result_tool(result)` | Function | Create ToolCallPart for structured output |
| `FINAL_RESULT_TOOL_NAME` | Constant | `"final_result"` |
| `tool_mock(func, return_values)` | Function | Create mock tool with sequential return values |
| `ToolMockWrapper` | Class | Mock wrapper with call_count, was_called, call_args_list, reset() |
| `AgentMock(nodes, result_output)` | Class | Replay recorded agent nodes |
| `AgentRunMock` | Class | Mock agent run iterator |
| `MockResult` | Class | Mock result with output attribute |

### `agentic_patterns.core.evals`

| Name | Kind | Description |
|---|---|---|
| `Case` | Class | Test scenario (from pydantic_evals) |
| `Dataset` | Class | Cases + evaluators (from pydantic_evals) |
| `Evaluator` | Protocol | Evaluation logic interface |
| `EvaluatorContext` | Class | Context with case, output, span_tree |
| `EvaluationReason` | Class | Result with value and reason |
| `EvaluationReport` | Class | Aggregate evaluation results |
| `EqualsExpected` | Evaluator | Exact match |
| `Contains` | Evaluator | Substring presence |
| `IsInstance` | Evaluator | Type check |
| `MaxDuration` | Evaluator | Latency constraint |
| `LLMJudge` | Evaluator | LLM-graded output |
| `HasMatchingSpan` | Evaluator | Span tree check |
| `OutputContainsJson` | Evaluator | Valid JSON check |
| `ToolWasCalled(tool_name)` | Evaluator | Tool invocation check |
| `NoToolErrors` | Evaluator | No tool errors check |
| `OutputMatchesSchema(schema)` | Evaluator | Pydantic/dict schema validation |
| `find_eval_files(evals_dir)` | Function | Find eval_*.py files |
| `discover_datasets(files, filter)` | Function | Auto-discover datasets from files |
| `DiscoveredDataset` | Dataclass | Bundle of dataset, target, scorers, name, path |
| `run_evaluation(discovered, opts)` | Function | Run single evaluation |
| `run_all_evaluations(datasets, opts)` | Function | Run all evaluations |
| `average_assertions(report, min)` | Function | Check average score threshold |
| `PrintOptions` | Dataclass | Report formatting options |

### `agentic_patterns.core.doctors`

| Name | Kind | Description |
|---|---|---|
| `ToolDoctor` | Class | Analyze tool functions |
| `PromptDoctor` | Class | Analyze prompt templates |
| `MCPDoctor` | Class | Analyze MCP server tools |
| `A2ADoctor` | Class | Analyze A2A agent cards |
| `SkillDoctor` | Class | Analyze Agent Skills |
| `Issue` | Model | level, category, message, suggestion |
| `IssueLevel` | Enum | ERROR, WARNING, INFO |
| `IssueCategory` | Enum | AMBIGUITY, ARGUMENTS, CLARITY, COMPLETENESS, ... |
| `Recommendation` | Model | Base: name, needs_improvement, issues |
| `ToolRecommendation` | Model | + arguments, return_type_issues |
| `PromptRecommendation` | Model | + placeholders_found |
| `A2ARecommendation` | Model | + capabilities, skills |
| `AgentSkillRecommendation` | Model | + frontmatter/body/structure/consistency issues, scripts |


## Examples

See the files in `agentic_patterns/examples/evals/`:

- `eval_todo.py` -- eval file for the todo agent with custom evaluators
- `eval_search.py` -- eval file for the search agent with tool call checks
- `skill-bad/` and `skill-good/` -- skill directories for doctor analysis comparison
