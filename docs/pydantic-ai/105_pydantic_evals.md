# Pydantic Evals

**Pydantic Evals** is a powerful evaluation framework for systematically testing and evaluating AI systems, from simple LLM calls to complex multi-agent applications.

## Design Philosophy

Code-First Approach

Pydantic Evals follows a code-first philosophy where all evaluation components are defined in Python. This differs from platforms with web-based configuration. You write and run evals in code, and can write the results to disk or view them in your terminal or in [Pydantic Logfire](https://logfire.pydantic.dev/docs/guides/web-ui/evals/).

Evals are an Emerging Practice

Unlike unit tests, evals are an emerging art/science. Anyone who claims to know exactly how your evals should be defined can safely be ignored. We've designed Pydantic Evals to be flexible and useful without being too opinionated.

## Quick Navigation

**Getting Started:**

- [Installation](#installation)
- [Quick Start](https://ai.pydantic.dev/evals/quick-start/index.md)
- [Core Concepts](https://ai.pydantic.dev/evals/core-concepts/index.md)

**Evaluators:**

- [Evaluators Overview](https://ai.pydantic.dev/evals/evaluators/overview/index.md) - Compare evaluator types and learn when to use each approach
- [Built-in Evaluators](https://ai.pydantic.dev/evals/evaluators/built-in/index.md) - Complete reference for exact match, instance checks, and other ready-to-use evaluators
- [LLM as a Judge](https://ai.pydantic.dev/evals/evaluators/llm-judge/index.md) - Use LLMs to evaluate subjective qualities, complex criteria, and natural language outputs
- [Custom Evaluators](https://ai.pydantic.dev/evals/evaluators/custom/index.md) - Implement domain-specific scoring logic and custom evaluation metrics
- [Span-Based Evaluation](https://ai.pydantic.dev/evals/evaluators/span-based/index.md) - Evaluate internal agent behavior (tool calls, execution flow) using OpenTelemetry traces. Essential for complex agents where correctness depends on *how* the answer was reached, not just the final output. Also ensures eval assertions align with production telemetry.

**How-To Guides:**

- [Logfire Integration](https://ai.pydantic.dev/evals/how-to/logfire-integration/index.md) - Visualize results
- [Dataset Management](https://ai.pydantic.dev/evals/how-to/dataset-management/index.md) - Save, load, generate
- [Concurrency & Performance](https://ai.pydantic.dev/evals/how-to/concurrency/index.md) - Control parallel execution
- [Retry Strategies](https://ai.pydantic.dev/evals/how-to/retry-strategies/index.md) - Handle transient failures
- [Metrics & Attributes](https://ai.pydantic.dev/evals/how-to/metrics-attributes/index.md) - Track custom data

**Examples:**

- [Simple Validation](https://ai.pydantic.dev/evals/examples/simple-validation/index.md) - Basic example

**Reference:**

- [API Documentation](https://ai.pydantic.dev/api/pydantic_evals/dataset/index.md)

## Code-First Evaluation

Pydantic Evals follows a **code-first approach** where you define all evaluation components (datasets, experiments, tasks, cases and evaluators) in Python code, or as serialized data loaded by Python code. This differs from platforms with fully web-based configuration.

When you run an *Experiment* you'll see a progress indicator and can print the results wherever you run your python code (IDE, terminal, etc). You also get a report object back that you can serialize and store or send to a notebook or other application for further visualization and analysis.

If you are using [Pydantic Logfire](https://logfire.pydantic.dev/docs/guides/web-ui/evals/), your experiment results automatically appear in the Logfire web interface for visualization, comparison, and collaborative analysis. Logfire serves as a observability layer - you write and run evals in code, then view and analyze results in the web UI.

## Installation

To install the Pydantic Evals package, run:

```bash
pip install pydantic-evals
```

```bash
uv add pydantic-evals
```

`pydantic-evals` does not depend on `pydantic-ai`, but has an optional dependency on `logfire` if you'd like to use OpenTelemetry traces in your evals, or send evaluation results to [logfire](https://pydantic.dev/logfire).

```bash
pip install 'pydantic-evals[logfire]'
```

```bash
uv add 'pydantic-evals[logfire]'
```

## Pydantic Evals Data Model

Pydantic Evals is built around a simple data model:

### Data Model Diagram

```text
Dataset (1) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ (Many) Case
â”‚                        â”‚
â”‚                        â”‚
â””â”€â”€â”€ (Many) Experiment â”€â”€â”´â”€â”€â”€ (Many) Case results
     â”‚
     â””â”€â”€â”€ (1) Task
     â”‚
     â””â”€â”€â”€ (Many) Evaluator
```

### Key Relationships

1. **Dataset â†’ Cases**: One Dataset contains many Cases
1. **Dataset â†’ Experiments**: One Dataset can be used across many Experiments over time
1. **Experiment â†’ Case results**: One Experiment generates results by executing each Case
1. **Experiment â†’ Task**: One Experiment evaluates one defined Task
1. **Experiment â†’ Evaluators**: One Experiment uses multiple Evaluators. Dataset-wide Evaluators are run against all Cases, and Case-specific Evaluators against their respective Cases

### Data Flow

1. **Dataset creation**: Define cases and evaluators in YAML/JSON, or directly in Python
1. **Experiment execution**: Run `dataset.evaluate_sync(task_function)`
1. **Cases run**: Each Case is executed against the Task
1. **Evaluation**: Evaluators score the Task outputs for each Case
1. **Results**: All Case results are collected into a summary report

A metaphor

A useful metaphor (although not perfect) is to think of evals like a **Unit Testing** framework:

- **Cases + Evaluators** are your individual unit tests - each one defines a specific scenario you want to test, complete with inputs and expected outcomes. Just like a unit test, a case asks: *"Given this input, does my system produce the right output?"*
- **Datasets** are like test suites - they are the scaffolding that holds your unit tests together. They group related cases and define shared evaluation criteria that should apply across all tests in the suite.
- **Experiments** are like running your entire test suite and getting a report. When you execute `dataset.evaluate_sync(my_ai_function)`, you're running all your cases against your AI system and collecting the results - just like running `pytest` and getting a summary of passes, failures, and performance metrics.

The key difference from traditional unit testing is that AI systems are probabilistic. If you're type checking you'll still get a simple pass/fail, but scores for text outputs are likely qualitative and/or categorical, and more open to interpretation.

For a deeper understanding, see [Core Concepts](https://ai.pydantic.dev/evals/core-concepts/index.md).

## Datasets and Cases

In Pydantic Evals, everything begins with Datasets and Cases:

- **Dataset**: A collection of test Cases designed for the evaluation of a specific task or function
- **Case**: A single test scenario corresponding to Task inputs, with optional expected outputs, metadata, and case-specific evaluators

simple_eval_dataset.py

```python
from pydantic_evals import Case, Dataset

case1 = Case(
    name='simple_case',
    inputs='What is the capital of France?',
    expected_output='Paris',
    metadata={'difficulty': 'easy'},
)

dataset = Dataset(cases=[case1])
```

*(This example is complete, it can be run "as is")*

See [Dataset Management](https://ai.pydantic.dev/evals/how-to/dataset-management/index.md) to learn about saving, loading, and generating datasets.

## Evaluators

Evaluators analyze and score the results of your Task when tested against a Case.

These can be deterministic, code-based checks (such as testing model output format with a regex, or checking for the appearance of PII or sensitive data), or they can assess non-deterministic model outputs for qualities like accuracy, precision/recall, hallucinations, or instruction-following.

While both kinds of testing are useful in LLM systems, classical code-based tests are cheaper and easier than tests which require either human or machine review of model outputs.

Pydantic Evals includes several [built-in evaluators](https://ai.pydantic.dev/evals/evaluators/built-in/index.md) and allows you to define [custom evaluators](https://ai.pydantic.dev/evals/evaluators/custom/index.md):

simple_eval_evaluator.py

```python
from dataclasses import dataclass

from pydantic_evals.evaluators import Evaluator, EvaluatorContext
from pydantic_evals.evaluators.common import IsInstance

from simple_eval_dataset import dataset

dataset.add_evaluator(IsInstance(type_name='str'))  # (1)!


@dataclass
class MyEvaluator(Evaluator):
    async def evaluate(self, ctx: EvaluatorContext[str, str]) -> float:  # (2)!
        if ctx.output == ctx.expected_output:
            return 1.0
        elif (
            isinstance(ctx.output, str)
            and ctx.expected_output.lower() in ctx.output.lower()
        ):
            return 0.8
        else:
            return 0.0


dataset.add_evaluator(MyEvaluator())
```

1. You can add built-in evaluators to a dataset using the add_evaluator method.
1. This custom evaluator returns a simple score based on whether the output matches the expected output.

*(This example is complete, it can be run "as is")*

Learn more:

- [Evaluators Overview](https://ai.pydantic.dev/evals/evaluators/overview/index.md) - When to use different types
- [Built-in Evaluators](https://ai.pydantic.dev/evals/evaluators/built-in/index.md) - Complete reference
- [LLM Judge](https://ai.pydantic.dev/evals/evaluators/llm-judge/index.md) - Using LLMs as evaluators
- [Custom Evaluators](https://ai.pydantic.dev/evals/evaluators/custom/index.md) - Write your own logic
- [Span-Based Evaluation](https://ai.pydantic.dev/evals/evaluators/span-based/index.md) - Analyze execution traces

## Running Experiments

Performing evaluations involves running a task against all cases in a dataset, also known as running an "experiment".

Putting the above two examples together and using the more declarative `evaluators` kwarg to Dataset:

simple_eval_complete.py

```python
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import Evaluator, EvaluatorContext, IsInstance

case1 = Case(  # (1)!
    name='simple_case',
    inputs='What is the capital of France?',
    expected_output='Paris',
    metadata={'difficulty': 'easy'},
)


class MyEvaluator(Evaluator[str, str]):
    def evaluate(self, ctx: EvaluatorContext[str, str]) -> float:
        if ctx.output == ctx.expected_output:
            return 1.0
        elif (
            isinstance(ctx.output, str)
            and ctx.expected_output.lower() in ctx.output.lower()
        ):
            return 0.8
        else:
            return 0.0


dataset = Dataset(
    cases=[case1],
    evaluators=[IsInstance(type_name='str'), MyEvaluator()],  # (2)!
)


async def guess_city(question: str) -> str:  # (3)!
    return 'Paris'


report = dataset.evaluate_sync(guess_city)  # (4)!
report.print(include_input=True, include_output=True, include_durations=False)  # (5)!
"""
                              Evaluation Summary: guess_city
â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”³â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”³â”â”â”â”â”â”â”â”â”â”³â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”³â”â”â”â”â”â”â”â”â”â”â”â”â”“
â”ƒ Case ID     â”ƒ Inputs                         â”ƒ Outputs â”ƒ Scores            â”ƒ Assertions â”ƒ
â”¡â”â”â”â”â”â”â”â”â”â”â”â”â”â•‡â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â•‡â”â”â”â”â”â”â”â”â”â•‡â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â•‡â”â”â”â”â”â”â”â”â”â”â”â”â”©
â”‚ simple_case â”‚ What is the capital of France? â”‚ Paris   â”‚ MyEvaluator: 1.00 â”‚ âœ”          â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ Averages    â”‚                                â”‚         â”‚ MyEvaluator: 1.00 â”‚ 100.0% âœ”   â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
"""
```

1. Create a test case as above
1. Create a Dataset with test cases and evaluators
1. Our function to evaluate.
1. Run the evaluation with evaluate_sync, which runs the function against all test cases in the dataset, and returns an EvaluationReport object.
1. Print the report with print, which shows the results of the evaluation. We have omitted duration here just to keep the printed output from changing from run to run.

*(This example is complete, it can be run "as is")*

See [Quick Start](https://ai.pydantic.dev/evals/quick-start/index.md) for more examples and [Concurrency & Performance](https://ai.pydantic.dev/evals/how-to/concurrency/index.md) to learn about controlling parallel execution.

## API Reference

For comprehensive coverage of all classes, methods, and configuration options, see the detailed [API Reference documentation](https://ai.pydantic.dev/api/pydantic_evals/dataset/).

## Next Steps

1. **Start with simple evaluations** using [Quick Start](https://ai.pydantic.dev/evals/quick-start/index.md)
1. **Understand the data model** with [Core Concepts](https://ai.pydantic.dev/evals/core-concepts/index.md)
1. **Explore built-in evaluators** in [Built-in Evaluators](https://ai.pydantic.dev/evals/evaluators/built-in/index.md)
1. **Integrate with Logfire** for visualization: [Logfire Integration](https://ai.pydantic.dev/evals/how-to/logfire-integration/index.md)
1. **Build comprehensive test suites** with [Dataset Management](https://ai.pydantic.dev/evals/how-to/dataset-management/index.md)
1. **Implement custom evaluators** for domain-specific metrics: [Custom Evaluators](https://ai.pydantic.dev/evals/evaluators/custom/index.md)
