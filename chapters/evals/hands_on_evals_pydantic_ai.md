# Hands-On: Pydantic Evals Framework

The pydantic-evals library provides structured abstractions for building evaluation suites. This hands-on explores the framework through `example_evals_pydantic_ai.ipynb`, demonstrating how Cases, Evaluators, and Datasets work together to create maintainable, scalable evals.

## From Ad-Hoc Tests to Structured Evals

The basic eval approaches from the previous hands-on work for individual tests, but they don't scale. As eval suites grow, you need consistent structure: test cases with metadata, reusable evaluators, aggregated reports, and the ability to run the same dataset against different system variants.

The pydantic-evals framework addresses this through three core abstractions. A Case defines a single test scenario with typed inputs and expected outputs. An Evaluator encodes what "good" means, returning scores, assertions, or labels. A Dataset combines cases with evaluators and runs them against a task function, producing a structured report.

## Core Concepts: Case, Evaluator, Dataset

A Case captures everything about a single evaluation scenario:

```python
case1 = Case(
    name='simple_case',
    inputs='What is the capital of France?',
    expected_output='Paris',
    metadata={'difficulty': 'easy'},
)
```

The `name` identifies the case in reports. The `inputs` are passed to the task function being evaluated. The `expected_output` provides ground truth for comparison. The `metadata` enables slicing results by arbitrary dimensions - here we tag the case as "easy" so we can later filter reports by difficulty.

An Evaluator defines how to score outputs. The framework provides built-in evaluators like `IsInstance` for type checking, but custom evaluators handle domain-specific logic:

```python
@dataclass
class MyEvaluator(Evaluator):
    async def evaluate(self, ctx: EvaluatorContext[str, str]) -> float:
        if ctx.output == ctx.expected_output:
            return 1.0
        elif (
            isinstance(ctx.output, str)
            and ctx.expected_output.lower() in ctx.output.lower()
        ):
            return 0.8
        else:
            return 0.0
```

This evaluator returns a score between 0 and 1. Exact matches score 1.0. Partial matches (where the expected output appears within the actual output) score 0.8. Everything else scores 0. The `EvaluatorContext` provides access to the case's inputs, expected output, and actual output.

A Dataset combines cases with evaluators:

```python
dataset = Dataset(
    cases=[case1],
    evaluators=[IsInstance(type_name='str'), MyEvaluator()],
)
```

The evaluators apply to all cases in the dataset. Here, every case will be checked for string type (`IsInstance`) and scored by our custom evaluator.

Running the dataset against a task function produces a report:

```python
async def guess_city(question: str) -> str:
    return 'Paris'

report = await dataset.evaluate(guess_city)
report.print(include_input=True, include_output=True, include_durations=False)
```

The `evaluate` method runs each case through the task function, applies all evaluators, and aggregates results. The report shows per-case results, evaluator scores, and summary statistics.

## LLM Judge with Real Agent

The framework's power becomes clear when evaluating actual agents. The notebook demonstrates this with a recipe generation task:

```python
class CustomerOrder(BaseModel):
    dish_name: str
    dietary_restriction: str | None = None

class Recipe(BaseModel):
    ingredients: list[str]
    steps: list[str]
```

These Pydantic models define the input and output types. A customer orders a dish with optional dietary restrictions; the agent returns a structured recipe.

The agent wraps our standard infrastructure:

```python
recipe_agent = get_agent(
    output_type=Recipe,
    system_prompt='Generate a recipe to cook the dish that meets the dietary restrictions.'
)

async def transform_recipe(customer_order: CustomerOrder) -> Recipe:
    res, nodes = await run_agent(recipe_agent, format_as_xml(customer_order), verbose=True)
    return res
```

The `transform_recipe` function is the task being evaluated. It takes a typed input, runs the agent, and returns a typed output.

The dataset uses LLMJudge for semantic evaluation:

```python
recipe_dataset = Dataset[CustomerOrder, Recipe, Any](
    cases=[
        Case(
            name='vegetarian_recipe',
            inputs=CustomerOrder(dish_name='Spaghetti Bolognese', dietary_restriction='vegetarian'),
            expected_output=None,
            metadata={'focus': 'vegetarian'},
            evaluators=(
                LLMJudge(
                    rubric='Recipe should not contain meat or animal products',
                    model=model
                ),
            ),
        ),
        Case(
            name='gluten_free_recipe',
            inputs=CustomerOrder(dish_name='Chocolate Cake', dietary_restriction='gluten-free'),
            expected_output=None,
            metadata={'focus': 'gluten-free'},
            evaluators=(
                LLMJudge(
                    rubric='Recipe should not contain gluten or wheat products',
                    model=model
                ),
            ),
        ),
    ],
    evaluators=[
        IsInstance(type_name='Recipe'),
        LLMJudge(
            rubric='Recipe should have clear steps and relevant ingredients',
            include_input=True,
            model=model,
        ),
    ],
)
```

Several patterns appear here. First, `expected_output=None` signals that there's no single correct answer - we're evaluating quality rather than correctness. Second, per-case evaluators (`evaluators` on each Case) check requirements specific to that case. The vegetarian case checks for no meat; the gluten-free case checks for no gluten. Third, dataset-level evaluators apply to all cases. Every recipe should be a valid `Recipe` type and should have clear steps with relevant ingredients.

The `LLMJudge` evaluator takes a rubric describing what to check and uses a language model to assess whether the output meets that criterion. The `include_input=True` parameter gives the judge access to the original input, enabling it to check whether the recipe actually matches the requested dish.

Running the evaluation:

```python
report = await recipe_dataset.evaluate(transform_recipe)
print(report)
```

The report shows results for each case across all evaluators. You can see which cases passed type checking, whether dietary restrictions were respected, and whether recipes met general quality criteria.

## Why This Structure Matters

The framework's abstractions provide several benefits over ad-hoc testing.

Separation of concerns keeps test definitions (Cases) separate from evaluation logic (Evaluators) separate from execution (Dataset.evaluate). You can add cases without touching evaluator code, or swap evaluators without modifying cases.

Metadata enables analysis. Tags like `difficulty`, `domain`, or `focus` let you slice results to answer questions like "are we failing more on vegetarian recipes?" or "did quality drop on hard cases?"

Typed inputs and outputs catch schema mismatches early. If the task function returns the wrong type, `IsInstance` fails immediately rather than producing confusing downstream errors.

Reusable evaluators reduce duplication. The same `LLMJudge` with a quality rubric can apply across all recipe cases, while case-specific judges handle unique requirements.

Structured reports enable comparison. Running the same dataset against different agent versions produces comparable reports, enabling regression detection and performance tracking.

## Evaluator Output Types

Evaluators can return different types depending on what they measure. Numeric scores (float) work for quality metrics on a scale. Boolean assertions work for pass/fail checks. Labels (strings) work for categorical classifications. The framework handles all three consistently in reports.

The custom evaluator in the notebook returns floats (0.0, 0.8, or 1.0) representing match quality. The `IsInstance` evaluator returns a boolean. The `LLMJudge` can return scores, pass/fail, or detailed assessments depending on configuration.

## Production Considerations

When building production eval suites with this framework, consider dataset versioning. Store datasets as YAML or JSON files in version control so changes are reviewable and diffable.

Evaluator configuration affects results. Judge rubrics should be explicit and testable. Vague criteria like "good quality" produce inconsistent results; specific criteria like "recipe should not contain meat or animal products" are actionable.

Cost and latency accumulate. Each LLMJudge call invokes the model, adding time and expense. For large datasets, consider running deterministic evaluators first to filter obvious failures before expensive judge evaluation.

Flakiness requires management. LLM judges are non-deterministic. Run critical evals multiple times and aggregate results, or use low temperature settings to reduce variance.

## Key Takeaways

The pydantic-evals framework provides structured abstractions for scalable evaluation. Cases define test scenarios with typed inputs, expected outputs, and metadata. Evaluators encode what "good" means, from simple type checks to LLM-based semantic assessment. Datasets combine cases with evaluators and produce structured reports.

Per-case evaluators handle requirements specific to individual scenarios. Dataset-level evaluators apply common checks across all cases. This layering separates concerns and reduces duplication.

LLMJudge enables semantic evaluation for open-ended tasks where programmatic checking is impractical. Rubrics should be explicit and specific to produce consistent, actionable results.

The framework transforms evals from ad-hoc scripts into engineering artifacts that can be versioned, reviewed, and maintained alongside the systems they test.
