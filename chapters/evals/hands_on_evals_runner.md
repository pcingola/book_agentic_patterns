## Hands-On: Eval Runner and Custom Evaluators

The previous hands-on sections built evals interactively in notebooks. In practice, eval suites need to run from the command line, integrate with CI pipelines, and scale across many files. This hands-on explores the eval runner infrastructure through `example_evals_runner.ipynb`, which demonstrates auto-discovery of eval files, the custom evaluators provided by the core library, and CLI integration.

### Convention-Based Discovery

The eval runner uses naming conventions to discover and wire up evaluation components automatically. It scans a directory for `eval_*.py` files, then inside each file it finds:

- `dataset_*` objects: `Dataset` instances containing cases and evaluators.
- `target_*` functions: exactly one per file, the function being evaluated.
- `scorer_*` functions: optional, override the default pass/fail logic.

A minimal eval file looks like this:

```python
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import Contains, IsInstance

from agentic_patterns.core.agents import get_agent, run_agent

dataset_capitals = Dataset(
    cases=[
        Case(
            name="france",
            inputs="What is the capital of France?",
            expected_output="Paris",
            metadata={"difficulty": "easy"},
        ),
        Case(
            name="japan",
            inputs="What is the capital of Japan?",
            expected_output="Tokyo",
            metadata={"difficulty": "easy"},
        ),
    ],
    evaluators=[
        IsInstance(type_name="str"),
        Contains(),
    ],
)


async def target_answer(question: str) -> str:
    agent = get_agent()
    agent_run, _ = await run_agent(agent, question)
    return agent_run.result.output
```

The `Contains` evaluator checks that `expected_output` appears within the actual output, which is a natural fit for factual questions where the agent wraps the answer in a longer sentence.

Discovery wires everything together:

```python
from pathlib import Path
from agentic_patterns.core.evals import find_eval_files, discover_datasets

evals_dir = Path(".")
eval_files = find_eval_files(evals_dir)
datasets = discover_datasets(eval_files, verbose=True)
```

Each discovered dataset can then be executed individually or in batch. The runner handles reporting, scoring, and pass/fail determination.

### Custom Evaluators

The core library provides four evaluators for common agent scenarios that go beyond basic string or type checks.

`OutputContainsJson` checks whether the output is valid JSON. This is useful when agents are expected to return structured data but the output type is a raw string.

`OutputMatchesSchema` validates the output against a Pydantic model. It first parses the output as JSON (if it is a string), then validates against the schema. This combines format and content validation in a single evaluator:

```python
from pydantic import BaseModel
from agentic_patterns.core.evals import OutputContainsJson, OutputMatchesSchema

class CityInfo(BaseModel):
    city: str
    country: str

dataset_schema = Dataset(
    cases=[
        Case(name="valid", inputs="valid", expected_output='{"city": "Paris", "country": "France"}'),
        Case(name="invalid", inputs="invalid", expected_output="not json at all"),
    ],
    evaluators=[
        OutputContainsJson(),
        OutputMatchesSchema(schema=CityInfo),
    ],
)
```

The first case passes both evaluators. The second case fails both: the output is not valid JSON and does not match the schema. In a real eval, the task function would call an agent; here the pattern shows how the evaluators compose.

`ToolWasCalled` and `NoToolErrors` inspect the execution span tree to verify tool invocation patterns. `ToolWasCalled` asserts that a specific tool was invoked during the agent run, while `NoToolErrors` asserts that no tool calls resulted in errors. These evaluators address the process-level guarantees discussed in the evals section: verifying not just what the agent returned, but how it executed.

### CLI Integration

The same discovery and execution logic is available as a command-line tool:

```bash
# Run all eval_*.py files in a directory
python -m agentic_patterns.core.evals --evals-dir agentic_patterns/examples/evals --verbose

# Filter to a specific dataset
python -m agentic_patterns.core.evals --evals-dir agentic_patterns/examples/evals --filter capitals
```

The CLI returns a non-zero exit code when any evaluation fails, making it suitable as a CI gate. Options control report detail (`--include-reasons`, `--include-output`) and pass thresholds (`--min-assertions`). This is how evals move from interactive notebooks to automated regression checks that run on every commit.
