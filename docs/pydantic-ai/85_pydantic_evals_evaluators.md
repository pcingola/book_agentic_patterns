# `pydantic_evals.evaluators`

### Contains

Bases: `Evaluator[object, object, object]`

Check if the output contains the expected output.

For strings, checks if expected_output is a substring of output. For lists/tuples, checks if expected_output is in output. For dicts, checks if all key-value pairs in expected_output are in output.

Note: case_sensitive only applies when both the value and output are strings.

Source code in `pydantic_evals/pydantic_evals/evaluators/common.py`

```python
@dataclass(repr=False)
class Contains(Evaluator[object, object, object]):
    """Check if the output contains the expected output.

    For strings, checks if expected_output is a substring of output.
    For lists/tuples, checks if expected_output is in output.
    For dicts, checks if all key-value pairs in expected_output are in output.

    Note: case_sensitive only applies when both the value and output are strings.
    """

    value: Any
    case_sensitive: bool = True
    as_strings: bool = False
    evaluation_name: str | None = field(default=None)

    def evaluate(
        self,
        ctx: EvaluatorContext[object, object, object],
    ) -> EvaluationReason:
        # Convert objects to strings if requested
        failure_reason: str | None = None
        as_strings = self.as_strings or (isinstance(self.value, str) and isinstance(ctx.output, str))
        if as_strings:
            output_str = str(ctx.output)
            expected_str = str(self.value)

            if not self.case_sensitive:
                output_str = output_str.lower()
                expected_str = expected_str.lower()

            failure_reason: str | None = None
            if expected_str not in output_str:
                output_trunc = _truncated_repr(output_str, max_length=100)
                expected_trunc = _truncated_repr(expected_str, max_length=100)
                failure_reason = f'Output string {output_trunc} does not contain expected string {expected_trunc}'
            return EvaluationReason(value=failure_reason is None, reason=failure_reason)

        try:
            # Handle different collection types
            if isinstance(ctx.output, dict):
                if isinstance(self.value, dict):
                    # Cast to Any to avoid type checking issues
                    output_dict = cast(dict[Any, Any], ctx.output)  # pyright: ignore[reportUnknownMemberType]
                    expected_dict = cast(dict[Any, Any], self.value)  # pyright: ignore[reportUnknownMemberType]
                    for k in expected_dict:
                        if k not in output_dict:
                            k_trunc = _truncated_repr(k, max_length=30)
                            failure_reason = f'Output dictionary does not contain expected key {k_trunc}'
                            break
                        elif output_dict[k] != expected_dict[k]:
                            k_trunc = _truncated_repr(k, max_length=30)
                            output_v_trunc = _truncated_repr(output_dict[k], max_length=100)
                            expected_v_trunc = _truncated_repr(expected_dict[k], max_length=100)
                            failure_reason = f'Output dictionary has different value for key {k_trunc}: {output_v_trunc} != {expected_v_trunc}'
                            break
                else:
                    if self.value not in ctx.output:  # pyright: ignore[reportUnknownMemberType]
                        output_trunc = _truncated_repr(ctx.output, max_length=200)  # pyright: ignore[reportUnknownMemberType]
                        failure_reason = f'Output {output_trunc} does not contain provided value as a key'
            elif self.value not in ctx.output:  # pyright: ignore[reportOperatorIssue]  # will be handled by except block
                output_trunc = _truncated_repr(ctx.output, max_length=200)
                failure_reason = f'Output {output_trunc} does not contain provided value'
        except (TypeError, ValueError) as e:
            failure_reason = f'Containment check failed: {e}'

        return EvaluationReason(value=failure_reason is None, reason=failure_reason)
```

### Equals

Bases: `Evaluator[object, object, object]`

Check if the output exactly equals the provided value.

Source code in `pydantic_evals/pydantic_evals/evaluators/common.py`

```python
@dataclass(repr=False)
class Equals(Evaluator[object, object, object]):
    """Check if the output exactly equals the provided value."""

    value: Any
    evaluation_name: str | None = field(default=None)

    def evaluate(self, ctx: EvaluatorContext[object, object, object]) -> bool:
        return ctx.output == self.value
```

### EqualsExpected

Bases: `Evaluator[object, object, object]`

Check if the output exactly equals the expected output.

Source code in `pydantic_evals/pydantic_evals/evaluators/common.py`

```python
@dataclass(repr=False)
class EqualsExpected(Evaluator[object, object, object]):
    """Check if the output exactly equals the expected output."""

    evaluation_name: str | None = field(default=None)

    def evaluate(self, ctx: EvaluatorContext[object, object, object]) -> bool | dict[str, bool]:
        if ctx.expected_output is None:
            return {}  # Only compare if expected output is provided
        return ctx.output == ctx.expected_output
```

### HasMatchingSpan

Bases: `Evaluator[object, object, object]`

Check if the span tree contains a span that matches the specified query.

Source code in `pydantic_evals/pydantic_evals/evaluators/common.py`

```python
@dataclass(repr=False)
class HasMatchingSpan(Evaluator[object, object, object]):
    """Check if the span tree contains a span that matches the specified query."""

    query: SpanQuery
    evaluation_name: str | None = field(default=None)

    def evaluate(
        self,
        ctx: EvaluatorContext[object, object, object],
    ) -> bool:
        return ctx.span_tree.any(self.query)
```

### IsInstance

Bases: `Evaluator[object, object, object]`

Check if the output is an instance of a type with the given name.

Source code in `pydantic_evals/pydantic_evals/evaluators/common.py`

```python
@dataclass(repr=False)
class IsInstance(Evaluator[object, object, object]):
    """Check if the output is an instance of a type with the given name."""

    type_name: str
    evaluation_name: str | None = field(default=None)

    def evaluate(self, ctx: EvaluatorContext[object, object, object]) -> EvaluationReason:
        output = ctx.output
        for cls in type(output).__mro__:
            if cls.__name__ == self.type_name or cls.__qualname__ == self.type_name:
                return EvaluationReason(value=True)

        reason = f'output is of type {type(output).__name__}'
        if type(output).__qualname__ != type(output).__name__:
            reason += f' (qualname: {type(output).__qualname__})'
        return EvaluationReason(value=False, reason=reason)
```

### LLMJudge

Bases: `Evaluator[object, object, object]`

Judge whether the output of a language model meets the criteria of a provided rubric.

If you do not specify a model, it uses the default model for judging. This starts as 'openai:gpt-5.2', but can be overridden by calling set_default_judge_model.

Source code in `pydantic_evals/pydantic_evals/evaluators/common.py`

```python
@dataclass(repr=False)
class LLMJudge(Evaluator[object, object, object]):
    """Judge whether the output of a language model meets the criteria of a provided rubric.

    If you do not specify a model, it uses the default model for judging. This starts as 'openai:gpt-5.2', but can be
    overridden by calling [`set_default_judge_model`][pydantic_evals.evaluators.llm_as_a_judge.set_default_judge_model].
    """

    rubric: str
    model: models.Model | models.KnownModelName | str | None = None
    include_input: bool = False
    include_expected_output: bool = False
    model_settings: ModelSettings | None = None
    score: OutputConfig | Literal[False] = False
    assertion: OutputConfig | Literal[False] = field(default_factory=lambda: OutputConfig(include_reason=True))

    async def evaluate(
        self,
        ctx: EvaluatorContext[object, object, object],
    ) -> EvaluatorOutput:
        if self.include_input:
            if self.include_expected_output:
                from .llm_as_a_judge import judge_input_output_expected

                grading_output = await judge_input_output_expected(
                    ctx.inputs, ctx.output, ctx.expected_output, self.rubric, self.model, self.model_settings
                )
            else:
                from .llm_as_a_judge import judge_input_output

                grading_output = await judge_input_output(
                    ctx.inputs, ctx.output, self.rubric, self.model, self.model_settings
                )
        else:
            if self.include_expected_output:
                from .llm_as_a_judge import judge_output_expected

                grading_output = await judge_output_expected(
                    ctx.output, ctx.expected_output, self.rubric, self.model, self.model_settings
                )
            else:
                from .llm_as_a_judge import judge_output

                grading_output = await judge_output(ctx.output, self.rubric, self.model, self.model_settings)

        output: dict[str, EvaluationScalar | EvaluationReason] = {}
        include_both = self.score is not False and self.assertion is not False
        evaluation_name = self.get_default_evaluation_name()

        if self.score is not False:
            default_name = f'{evaluation_name}_score' if include_both else evaluation_name
            _update_combined_output(output, grading_output.score, grading_output.reason, self.score, default_name)

        if self.assertion is not False:
            default_name = f'{evaluation_name}_pass' if include_both else evaluation_name
            _update_combined_output(output, grading_output.pass_, grading_output.reason, self.assertion, default_name)

        return output

    def build_serialization_arguments(self):
        result = super().build_serialization_arguments()
        # always serialize the model as a string when present; use its name if it's a KnownModelName
        if (model := result.get('model')) and isinstance(model, models.Model):  # pragma: no branch
            result['model'] = f'{model.system}:{model.model_name}'

        # Note: this may lead to confusion if you try to serialize-then-deserialize with a custom model.
        # I expect that is rare enough to be worth not solving yet, but common enough that we probably will want to
        # solve it eventually. I'm imagining some kind of model registry, but don't want to work out the details yet.
        return result
```

### MaxDuration

Bases: `Evaluator[object, object, object]`

Check if the execution time is under the specified maximum.

Source code in `pydantic_evals/pydantic_evals/evaluators/common.py`

```python
@dataclass(repr=False)
class MaxDuration(Evaluator[object, object, object]):
    """Check if the execution time is under the specified maximum."""

    seconds: float | timedelta

    def evaluate(self, ctx: EvaluatorContext[object, object, object]) -> bool:
        duration = timedelta(seconds=ctx.duration)
        seconds = self.seconds
        if not isinstance(seconds, timedelta):
            seconds = timedelta(seconds=seconds)
        return duration <= seconds
```

### OutputConfig

Bases: `TypedDict`

Configuration for the score and assertion outputs of the LLMJudge evaluator.

Source code in `pydantic_evals/pydantic_evals/evaluators/common.py`

```python
class OutputConfig(TypedDict, total=False):
    """Configuration for the score and assertion outputs of the LLMJudge evaluator."""

    evaluation_name: str
    include_reason: bool
```

### EvaluatorContext

Bases: `Generic[InputsT, OutputT, MetadataT]`

Context for evaluating a task execution.

An instance of this class is the sole input to all Evaluators. It contains all the information needed to evaluate the task execution, including inputs, outputs, metadata, and telemetry data.

Evaluators use this context to access the task inputs, actual output, expected output, and other information when evaluating the result of the task execution.

Example:

```python
from dataclasses import dataclass

from pydantic_evals.evaluators import Evaluator, EvaluatorContext


@dataclass
class ExactMatch(Evaluator):
    def evaluate(self, ctx: EvaluatorContext) -> bool:
        # Use the context to access task inputs, outputs, and expected outputs
        return ctx.output == ctx.expected_output
```

Source code in `pydantic_evals/pydantic_evals/evaluators/context.py`

````python
@dataclass(kw_only=True)
class EvaluatorContext(Generic[InputsT, OutputT, MetadataT]):
    """Context for evaluating a task execution.

    An instance of this class is the sole input to all Evaluators. It contains all the information
    needed to evaluate the task execution, including inputs, outputs, metadata, and telemetry data.

    Evaluators use this context to access the task inputs, actual output, expected output, and other
    information when evaluating the result of the task execution.

    Example:
    ```python
    from dataclasses import dataclass

    from pydantic_evals.evaluators import Evaluator, EvaluatorContext


    @dataclass
    class ExactMatch(Evaluator):
        def evaluate(self, ctx: EvaluatorContext) -> bool:
            # Use the context to access task inputs, outputs, and expected outputs
            return ctx.output == ctx.expected_output
    ```
    """

    name: str | None
    """The name of the case."""
    inputs: InputsT
    """The inputs provided to the task for this case."""
    metadata: MetadataT | None
    """Metadata associated with the case, if provided. May be None if no metadata was specified."""
    expected_output: OutputT | None
    """The expected output for the case, if provided. May be None if no expected output was specified."""

    output: OutputT
    """The actual output produced by the task for this case."""
    duration: float
    """The duration of the task run for this case."""
    _span_tree: SpanTree | SpanTreeRecordingError = field(repr=False)
    """The span tree for the task run for this case.

    This will be `None` if `logfire.configure` has not been called.
    """

    attributes: dict[str, Any]
    """Attributes associated with the task run for this case.

    These can be set by calling `pydantic_evals.dataset.set_eval_attribute` in any code executed
    during the evaluation task."""
    metrics: dict[str, int | float]
    """Metrics associated with the task run for this case.

    These can be set by calling `pydantic_evals.dataset.increment_eval_metric` in any code executed
    during the evaluation task."""

    @property
    def span_tree(self) -> SpanTree:
        """Get the `SpanTree` for this task execution.

        The span tree is a graph where each node corresponds to an OpenTelemetry span recorded during the task
        execution, including timing information and any custom spans created during execution.

        Returns:
            The span tree for the task execution.

        Raises:
            SpanTreeRecordingError: If spans were not captured during execution of the task, e.g. due to not having
                the necessary dependencies installed.
        """
        if isinstance(self._span_tree, SpanTreeRecordingError):
            # In this case, there was a reason we couldn't record the SpanTree. We raise that now
            raise self._span_tree
        return self._span_tree
````

#### name

```python
name: str | None
```

The name of the case.

#### inputs

```python
inputs: InputsT
```

The inputs provided to the task for this case.

#### metadata

```python
metadata: MetadataT | None
```

Metadata associated with the case, if provided. May be None if no metadata was specified.

#### expected_output

```python
expected_output: OutputT | None
```

The expected output for the case, if provided. May be None if no expected output was specified.

#### output

```python
output: OutputT
```

The actual output produced by the task for this case.

#### duration

```python
duration: float
```

The duration of the task run for this case.

#### attributes

```python
attributes: dict[str, Any]
```

Attributes associated with the task run for this case.

These can be set by calling `pydantic_evals.dataset.set_eval_attribute` in any code executed during the evaluation task.

#### metrics

```python
metrics: dict[str, int | float]
```

Metrics associated with the task run for this case.

These can be set by calling `pydantic_evals.dataset.increment_eval_metric` in any code executed during the evaluation task.

#### span_tree

```python
span_tree: SpanTree
```

Get the `SpanTree` for this task execution.

The span tree is a graph where each node corresponds to an OpenTelemetry span recorded during the task execution, including timing information and any custom spans created during execution.

Returns:

| Type       | Description                           |
| ---------- | ------------------------------------- |
| `SpanTree` | The span tree for the task execution. |

Raises:

| Type                     | Description                                                                                                           |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------- |
| `SpanTreeRecordingError` | If spans were not captured during execution of the task, e.g. due to not having the necessary dependencies installed. |

### EvaluationReason

The result of running an evaluator with an optional explanation.

Contains a scalar value and an optional "reason" explaining the value.

Parameters:

| Name     | Type               | Description                                                               | Default                                           |
| -------- | ------------------ | ------------------------------------------------------------------------- | ------------------------------------------------- |
| `value`  | `EvaluationScalar` | The scalar result of the evaluation (boolean, integer, float, or string). | *required*                                        |
| `reason` | \`str              | None\`                                                                    | An optional explanation of the evaluation result. |

Source code in `pydantic_evals/pydantic_evals/evaluators/evaluator.py`

```python
@dataclass
class EvaluationReason:
    """The result of running an evaluator with an optional explanation.

    Contains a scalar value and an optional "reason" explaining the value.

    Args:
        value: The scalar result of the evaluation (boolean, integer, float, or string).
        reason: An optional explanation of the evaluation result.
    """

    value: EvaluationScalar
    reason: str | None = None
```

### EvaluationResult

Bases: `Generic[EvaluationScalarT]`

The details of an individual evaluation result.

Contains the name, value, reason, and source evaluator for a single evaluation.

Parameters:

| Name     | Type                | Description                                          | Default                                           |
| -------- | ------------------- | ---------------------------------------------------- | ------------------------------------------------- |
| `name`   | `str`               | The name of the evaluation.                          | *required*                                        |
| `value`  | `EvaluationScalarT` | The scalar result of the evaluation.                 | *required*                                        |
| `reason` | \`str               | None\`                                               | An optional explanation of the evaluation result. |
| `source` | `EvaluatorSpec`     | The spec of the evaluator that produced this result. | *required*                                        |

Source code in `pydantic_evals/pydantic_evals/evaluators/evaluator.py`

```python
@dataclass
class EvaluationResult(Generic[EvaluationScalarT]):
    """The details of an individual evaluation result.

    Contains the name, value, reason, and source evaluator for a single evaluation.

    Args:
        name: The name of the evaluation.
        value: The scalar result of the evaluation.
        reason: An optional explanation of the evaluation result.
        source: The spec of the evaluator that produced this result.
    """

    name: str
    value: EvaluationScalarT
    reason: str | None
    source: EvaluatorSpec

    def downcast(self, *value_types: type[T]) -> EvaluationResult[T] | None:
        """Attempt to downcast this result to a more specific type.

        Args:
            *value_types: The types to check the value against.

        Returns:
            A downcast version of this result if the value is an instance of one of the given types,
            otherwise None.
        """
        # Check if value matches any of the target types, handling bool as a special case
        for value_type in value_types:
            if isinstance(self.value, value_type):
                # Only match bool with explicit bool type
                if isinstance(self.value, bool) and value_type is not bool:
                    continue
                return cast(EvaluationResult[T], self)
        return None
```

#### downcast

```python
downcast(
    *value_types: type[T],
) -> EvaluationResult[T] | None
```

Attempt to downcast this result to a more specific type.

Parameters:

| Name           | Type      | Description                           | Default |
| -------------- | --------- | ------------------------------------- | ------- |
| `*value_types` | `type[T]` | The types to check the value against. | `()`    |

Returns:

| Type                  | Description |
| --------------------- | ----------- |
| \`EvaluationResult[T] | None\`      |
| \`EvaluationResult[T] | None\`      |

Source code in `pydantic_evals/pydantic_evals/evaluators/evaluator.py`

```python
def downcast(self, *value_types: type[T]) -> EvaluationResult[T] | None:
    """Attempt to downcast this result to a more specific type.

    Args:
        *value_types: The types to check the value against.

    Returns:
        A downcast version of this result if the value is an instance of one of the given types,
        otherwise None.
    """
    # Check if value matches any of the target types, handling bool as a special case
    for value_type in value_types:
        if isinstance(self.value, value_type):
            # Only match bool with explicit bool type
            if isinstance(self.value, bool) and value_type is not bool:
                continue
            return cast(EvaluationResult[T], self)
    return None
```

### Evaluator

Bases: `Generic[InputsT, OutputT, MetadataT]`

Base class for all evaluators.

Evaluators can assess the performance of a task in a variety of ways, as a function of the EvaluatorContext.

Subclasses must implement the `evaluate` method. Note it can be defined with either `def` or `async def`.

Example:

```python
from dataclasses import dataclass

from pydantic_evals.evaluators import Evaluator, EvaluatorContext


@dataclass
class ExactMatch(Evaluator):
    def evaluate(self, ctx: EvaluatorContext) -> bool:
        return ctx.output == ctx.expected_output
```

Source code in `pydantic_evals/pydantic_evals/evaluators/evaluator.py`

````python
@dataclass(repr=False)
class Evaluator(Generic[InputsT, OutputT, MetadataT], metaclass=_StrictABCMeta):
    """Base class for all evaluators.

    Evaluators can assess the performance of a task in a variety of ways, as a function of the EvaluatorContext.

    Subclasses must implement the `evaluate` method. Note it can be defined with either `def` or `async def`.

    Example:
    ```python
    from dataclasses import dataclass

    from pydantic_evals.evaluators import Evaluator, EvaluatorContext


    @dataclass
    class ExactMatch(Evaluator):
        def evaluate(self, ctx: EvaluatorContext) -> bool:
            return ctx.output == ctx.expected_output
    ```
    """

    __pydantic_config__ = ConfigDict(arbitrary_types_allowed=True)

    @classmethod
    def get_serialization_name(cls) -> str:
        """Return the 'name' of this Evaluator to use during serialization.

        Returns:
            The name of the Evaluator, which is typically the class name.
        """
        return cls.__name__

    @classmethod
    @deprecated('`name` has been renamed, use `get_serialization_name` instead.')
    def name(cls) -> str:
        """`name` has been renamed, use `get_serialization_name` instead."""
        return cls.get_serialization_name()

    def get_default_evaluation_name(self) -> str:
        """Return the default name to use in reports for the output of this evaluator.

        By default, if the evaluator has an attribute called `evaluation_name` of type string, that will be used.
        Otherwise, the serialization name of the evaluator (which is usually the class name) will be used.

        This can be overridden to get a more descriptive name in evaluation reports, e.g. using instance information.

        Note that evaluators that return a mapping of results will always use the keys of that mapping as the names
        of the associated evaluation results.
        """
        evaluation_name = getattr(self, 'evaluation_name', None)
        if isinstance(evaluation_name, str):
            # If the evaluator has an attribute `name` of type string, use that
            return evaluation_name

        return self.get_serialization_name()

    @abstractmethod
    def evaluate(
        self, ctx: EvaluatorContext[InputsT, OutputT, MetadataT]
    ) -> EvaluatorOutput | Awaitable[EvaluatorOutput]:  # pragma: no cover
        """Evaluate the task output in the given context.

        This is the main evaluation method that subclasses must implement. It can be either synchronous
        or asynchronous, returning either an EvaluatorOutput directly or an Awaitable[EvaluatorOutput].

        Args:
            ctx: The context containing the inputs, outputs, and metadata for evaluation.

        Returns:
            The evaluation result, which can be a scalar value, an EvaluationReason, or a mapping
            of evaluation names to either of those. Can be returned either synchronously or as an
            awaitable for asynchronous evaluation.
        """
        raise NotImplementedError('You must implement `evaluate`.')

    def evaluate_sync(self, ctx: EvaluatorContext[InputsT, OutputT, MetadataT]) -> EvaluatorOutput:
        """Run the evaluator synchronously, handling both sync and async implementations.

        This method ensures synchronous execution by running any async evaluate implementation
        to completion using run_until_complete.

        Args:
            ctx: The context containing the inputs, outputs, and metadata for evaluation.

        Returns:
            The evaluation result, which can be a scalar value, an EvaluationReason, or a mapping
            of evaluation names to either of those.
        """
        output = self.evaluate(ctx)
        if inspect.iscoroutine(output):  # pragma: no cover
            return get_event_loop().run_until_complete(output)
        else:
            return cast(EvaluatorOutput, output)

    async def evaluate_async(self, ctx: EvaluatorContext[InputsT, OutputT, MetadataT]) -> EvaluatorOutput:
        """Run the evaluator asynchronously, handling both sync and async implementations.

        This method ensures asynchronous execution by properly awaiting any async evaluate
        implementation. For synchronous implementations, it returns the result directly.

        Args:
            ctx: The context containing the inputs, outputs, and metadata for evaluation.

        Returns:
            The evaluation result, which can be a scalar value, an EvaluationReason, or a mapping
            of evaluation names to either of those.
        """
        # Note: If self.evaluate is synchronous, but you need to prevent this from blocking, override this method with:
        # return await anyio.to_thread.run_sync(self.evaluate, ctx)
        output = self.evaluate(ctx)
        if inspect.iscoroutine(output):
            return await output
        else:
            return cast(EvaluatorOutput, output)

    @model_serializer(mode='plain')
    def serialize(self, info: SerializationInfo) -> Any:
        """Serialize this Evaluator to a JSON-serializable form.

        Returns:
            A JSON-serializable representation of this evaluator as an EvaluatorSpec.
        """
        return to_jsonable_python(
            self.as_spec(),
            context=info.context,
            serialize_unknown=True,
        )

    def as_spec(self) -> EvaluatorSpec:
        raw_arguments = self.build_serialization_arguments()

        arguments: None | tuple[Any,] | dict[str, Any]
        if len(raw_arguments) == 0:
            arguments = None
        elif len(raw_arguments) == 1:
            arguments = (next(iter(raw_arguments.values())),)
        else:
            arguments = raw_arguments

        return EvaluatorSpec(name=self.get_serialization_name(), arguments=arguments)

    def build_serialization_arguments(self) -> dict[str, Any]:
        """Build the arguments for serialization.

        Evaluators are serialized for inclusion as the "source" in an `EvaluationResult`.
        If you want to modify how the evaluator is serialized for that or other purposes, you can override this method.

        Returns:
            A dictionary of arguments to be used during serialization.
        """
        raw_arguments: dict[str, Any] = {}
        for field in fields(self):
            value = getattr(self, field.name)
            # always exclude defaults:
            if field.default is not MISSING:
                if value == field.default:
                    continue
            if field.default_factory is not MISSING:
                if value == field.default_factory():  # pragma: no branch
                    continue
            raw_arguments[field.name] = value
        return raw_arguments

    __repr__ = _utils.dataclasses_no_defaults_repr
````

#### get_serialization_name

```python
get_serialization_name() -> str
```

Return the 'name' of this Evaluator to use during serialization.

Returns:

| Type  | Description                                                   |
| ----- | ------------------------------------------------------------- |
| `str` | The name of the Evaluator, which is typically the class name. |

Source code in `pydantic_evals/pydantic_evals/evaluators/evaluator.py`

```python
@classmethod
def get_serialization_name(cls) -> str:
    """Return the 'name' of this Evaluator to use during serialization.

    Returns:
        The name of the Evaluator, which is typically the class name.
    """
    return cls.__name__
```

#### name

```python
name() -> str
```

Deprecated

`name` has been renamed, use `get_serialization_name` instead.

`name` has been renamed, use `get_serialization_name` instead.

Source code in `pydantic_evals/pydantic_evals/evaluators/evaluator.py`

```python
@classmethod
@deprecated('`name` has been renamed, use `get_serialization_name` instead.')
def name(cls) -> str:
    """`name` has been renamed, use `get_serialization_name` instead."""
    return cls.get_serialization_name()
```

#### get_default_evaluation_name

```python
get_default_evaluation_name() -> str
```

Return the default name to use in reports for the output of this evaluator.

By default, if the evaluator has an attribute called `evaluation_name` of type string, that will be used. Otherwise, the serialization name of the evaluator (which is usually the class name) will be used.

This can be overridden to get a more descriptive name in evaluation reports, e.g. using instance information.

Note that evaluators that return a mapping of results will always use the keys of that mapping as the names of the associated evaluation results.

Source code in `pydantic_evals/pydantic_evals/evaluators/evaluator.py`

```python
def get_default_evaluation_name(self) -> str:
    """Return the default name to use in reports for the output of this evaluator.

    By default, if the evaluator has an attribute called `evaluation_name` of type string, that will be used.
    Otherwise, the serialization name of the evaluator (which is usually the class name) will be used.

    This can be overridden to get a more descriptive name in evaluation reports, e.g. using instance information.

    Note that evaluators that return a mapping of results will always use the keys of that mapping as the names
    of the associated evaluation results.
    """
    evaluation_name = getattr(self, 'evaluation_name', None)
    if isinstance(evaluation_name, str):
        # If the evaluator has an attribute `name` of type string, use that
        return evaluation_name

    return self.get_serialization_name()
```

#### evaluate

```python
evaluate(
    ctx: EvaluatorContext[InputsT, OutputT, MetadataT],
) -> EvaluatorOutput | Awaitable[EvaluatorOutput]
```

Evaluate the task output in the given context.

This is the main evaluation method that subclasses must implement. It can be either synchronous or asynchronous, returning either an EvaluatorOutput directly or an Awaitable[EvaluatorOutput].

Parameters:

| Name  | Type                                            | Description                                                              | Default    |
| ----- | ----------------------------------------------- | ------------------------------------------------------------------------ | ---------- |
| `ctx` | `EvaluatorContext[InputsT, OutputT, MetadataT]` | The context containing the inputs, outputs, and metadata for evaluation. | *required* |

Returns:

| Type              | Description                  |
| ----------------- | ---------------------------- |
| \`EvaluatorOutput | Awaitable[EvaluatorOutput]\` |
| \`EvaluatorOutput | Awaitable[EvaluatorOutput]\` |
| \`EvaluatorOutput | Awaitable[EvaluatorOutput]\` |

Source code in `pydantic_evals/pydantic_evals/evaluators/evaluator.py`

```python
@abstractmethod
def evaluate(
    self, ctx: EvaluatorContext[InputsT, OutputT, MetadataT]
) -> EvaluatorOutput | Awaitable[EvaluatorOutput]:  # pragma: no cover
    """Evaluate the task output in the given context.

    This is the main evaluation method that subclasses must implement. It can be either synchronous
    or asynchronous, returning either an EvaluatorOutput directly or an Awaitable[EvaluatorOutput].

    Args:
        ctx: The context containing the inputs, outputs, and metadata for evaluation.

    Returns:
        The evaluation result, which can be a scalar value, an EvaluationReason, or a mapping
        of evaluation names to either of those. Can be returned either synchronously or as an
        awaitable for asynchronous evaluation.
    """
    raise NotImplementedError('You must implement `evaluate`.')
```

#### evaluate_sync

```python
evaluate_sync(
    ctx: EvaluatorContext[InputsT, OutputT, MetadataT],
) -> EvaluatorOutput
```

Run the evaluator synchronously, handling both sync and async implementations.

This method ensures synchronous execution by running any async evaluate implementation to completion using run_until_complete.

Parameters:

| Name  | Type                                            | Description                                                              | Default    |
| ----- | ----------------------------------------------- | ------------------------------------------------------------------------ | ---------- |
| `ctx` | `EvaluatorContext[InputsT, OutputT, MetadataT]` | The context containing the inputs, outputs, and metadata for evaluation. | *required* |

Returns:

| Type              | Description                                                                           |
| ----------------- | ------------------------------------------------------------------------------------- |
| `EvaluatorOutput` | The evaluation result, which can be a scalar value, an EvaluationReason, or a mapping |
| `EvaluatorOutput` | of evaluation names to either of those.                                               |

Source code in `pydantic_evals/pydantic_evals/evaluators/evaluator.py`

```python
def evaluate_sync(self, ctx: EvaluatorContext[InputsT, OutputT, MetadataT]) -> EvaluatorOutput:
    """Run the evaluator synchronously, handling both sync and async implementations.

    This method ensures synchronous execution by running any async evaluate implementation
    to completion using run_until_complete.

    Args:
        ctx: The context containing the inputs, outputs, and metadata for evaluation.

    Returns:
        The evaluation result, which can be a scalar value, an EvaluationReason, or a mapping
        of evaluation names to either of those.
    """
    output = self.evaluate(ctx)
    if inspect.iscoroutine(output):  # pragma: no cover
        return get_event_loop().run_until_complete(output)
    else:
        return cast(EvaluatorOutput, output)
```

#### evaluate_async

```python
evaluate_async(
    ctx: EvaluatorContext[InputsT, OutputT, MetadataT],
) -> EvaluatorOutput
```

Run the evaluator asynchronously, handling both sync and async implementations.

This method ensures asynchronous execution by properly awaiting any async evaluate implementation. For synchronous implementations, it returns the result directly.

Parameters:

| Name  | Type                                            | Description                                                              | Default    |
| ----- | ----------------------------------------------- | ------------------------------------------------------------------------ | ---------- |
| `ctx` | `EvaluatorContext[InputsT, OutputT, MetadataT]` | The context containing the inputs, outputs, and metadata for evaluation. | *required* |

Returns:

| Type              | Description                                                                           |
| ----------------- | ------------------------------------------------------------------------------------- |
| `EvaluatorOutput` | The evaluation result, which can be a scalar value, an EvaluationReason, or a mapping |
| `EvaluatorOutput` | of evaluation names to either of those.                                               |

Source code in `pydantic_evals/pydantic_evals/evaluators/evaluator.py`

```python
async def evaluate_async(self, ctx: EvaluatorContext[InputsT, OutputT, MetadataT]) -> EvaluatorOutput:
    """Run the evaluator asynchronously, handling both sync and async implementations.

    This method ensures asynchronous execution by properly awaiting any async evaluate
    implementation. For synchronous implementations, it returns the result directly.

    Args:
        ctx: The context containing the inputs, outputs, and metadata for evaluation.

    Returns:
        The evaluation result, which can be a scalar value, an EvaluationReason, or a mapping
        of evaluation names to either of those.
    """
    # Note: If self.evaluate is synchronous, but you need to prevent this from blocking, override this method with:
    # return await anyio.to_thread.run_sync(self.evaluate, ctx)
    output = self.evaluate(ctx)
    if inspect.iscoroutine(output):
        return await output
    else:
        return cast(EvaluatorOutput, output)
```

#### serialize

```python
serialize(info: SerializationInfo) -> Any
```

Serialize this Evaluator to a JSON-serializable form.

Returns:

| Type  | Description                                                               |
| ----- | ------------------------------------------------------------------------- |
| `Any` | A JSON-serializable representation of this evaluator as an EvaluatorSpec. |

Source code in `pydantic_evals/pydantic_evals/evaluators/evaluator.py`

```python
@model_serializer(mode='plain')
def serialize(self, info: SerializationInfo) -> Any:
    """Serialize this Evaluator to a JSON-serializable form.

    Returns:
        A JSON-serializable representation of this evaluator as an EvaluatorSpec.
    """
    return to_jsonable_python(
        self.as_spec(),
        context=info.context,
        serialize_unknown=True,
    )
```

#### build_serialization_arguments

```python
build_serialization_arguments() -> dict[str, Any]
```

Build the arguments for serialization.

Evaluators are serialized for inclusion as the "source" in an `EvaluationResult`. If you want to modify how the evaluator is serialized for that or other purposes, you can override this method.

Returns:

| Type             | Description                                                |
| ---------------- | ---------------------------------------------------------- |
| `dict[str, Any]` | A dictionary of arguments to be used during serialization. |

Source code in `pydantic_evals/pydantic_evals/evaluators/evaluator.py`

```python
def build_serialization_arguments(self) -> dict[str, Any]:
    """Build the arguments for serialization.

    Evaluators are serialized for inclusion as the "source" in an `EvaluationResult`.
    If you want to modify how the evaluator is serialized for that or other purposes, you can override this method.

    Returns:
        A dictionary of arguments to be used during serialization.
    """
    raw_arguments: dict[str, Any] = {}
    for field in fields(self):
        value = getattr(self, field.name)
        # always exclude defaults:
        if field.default is not MISSING:
            if value == field.default:
                continue
        if field.default_factory is not MISSING:
            if value == field.default_factory():  # pragma: no branch
                continue
        raw_arguments[field.name] = value
    return raw_arguments
```

### EvaluatorFailure

Represents a failure raised during the execution of an evaluator.

Source code in `pydantic_evals/pydantic_evals/evaluators/evaluator.py`

```python
@dataclass
class EvaluatorFailure:
    """Represents a failure raised during the execution of an evaluator."""

    name: str
    error_message: str
    error_stacktrace: str
    source: EvaluatorSpec
```

### EvaluatorOutput

```python
EvaluatorOutput = (
    EvaluationScalar
    | EvaluationReason
    | Mapping[str, EvaluationScalar | EvaluationReason]
)
```

Type for the output of an evaluator, which can be a scalar, an EvaluationReason, or a mapping of names to either.

### EvaluatorSpec

Bases: `BaseModel`

The specification of an evaluator to be run.

This class is used to represent evaluators in a serializable format, supporting various short forms for convenience when defining evaluators in YAML or JSON dataset files.

In particular, each of the following forms is supported for specifying an evaluator with name `MyEvaluator`: * `'MyEvaluator'` - Just the (string) name of the Evaluator subclass is used if its `__init__` takes no arguments * `{'MyEvaluator': first_arg}` - A single argument is passed as the first positional argument to `MyEvaluator.__init__` * `{'MyEvaluator': {k1: v1, k2: v2}}` - Multiple kwargs are passed to `MyEvaluator.__init__`

Source code in `pydantic_evals/pydantic_evals/evaluators/spec.py`

```python
class EvaluatorSpec(BaseModel):
    """The specification of an evaluator to be run.

    This class is used to represent evaluators in a serializable format, supporting various
    short forms for convenience when defining evaluators in YAML or JSON dataset files.

    In particular, each of the following forms is supported for specifying an evaluator with name `MyEvaluator`:
    * `'MyEvaluator'` - Just the (string) name of the Evaluator subclass is used if its `__init__` takes no arguments
    * `{'MyEvaluator': first_arg}` - A single argument is passed as the first positional argument to `MyEvaluator.__init__`
    * `{'MyEvaluator': {k1: v1, k2: v2}}` - Multiple kwargs are passed to `MyEvaluator.__init__`
    """

    name: str
    """The name of the evaluator class; should be the value returned by `EvaluatorClass.get_serialization_name()`"""

    arguments: None | tuple[Any] | dict[str, Any]
    """The arguments to pass to the evaluator's constructor.

    Can be None (no arguments), a tuple (a single positional argument), or a dict (keyword arguments).
    """

    @property
    def args(self) -> tuple[Any, ...]:
        """Get the positional arguments for the evaluator.

        Returns:
            A tuple of positional arguments if arguments is a tuple, otherwise an empty tuple.
        """
        if isinstance(self.arguments, tuple):
            return self.arguments
        return ()

    @property
    def kwargs(self) -> dict[str, Any]:
        """Get the keyword arguments for the evaluator.

        Returns:
            A dictionary of keyword arguments if arguments is a dict, otherwise an empty dict.
        """
        if isinstance(self.arguments, dict):
            return self.arguments
        return {}

    @model_validator(mode='wrap')
    @classmethod
    def deserialize(cls, value: Any, handler: ModelWrapValidatorHandler[EvaluatorSpec]) -> EvaluatorSpec:
        """Deserialize an EvaluatorSpec from various formats.

        This validator handles the various short forms of evaluator specifications,
        converting them to a consistent EvaluatorSpec instance.

        Args:
            value: The value to deserialize.
            handler: The validator handler.

        Returns:
            The deserialized EvaluatorSpec.

        Raises:
            ValidationError: If the value cannot be deserialized.
        """
        try:
            result = handler(value)
            return result
        except ValidationError as exc:
            try:
                deserialized = _SerializedEvaluatorSpec.model_validate(value)
            except ValidationError:
                raise exc  # raise the original error
            return deserialized.to_evaluator_spec()

    @model_serializer(mode='wrap')
    def serialize(self, handler: SerializerFunctionWrapHandler, info: SerializationInfo) -> Any:
        """Serialize using the appropriate short-form if possible.

        Returns:
            The serialized evaluator specification, using the shortest form possible:
            - Just the name if there are no arguments
            - {name: first_arg} if there's a single positional argument
            - {name: {kwargs}} if there are multiple (keyword) arguments
        """
        if isinstance(info.context, dict) and info.context.get('use_short_form'):  # pyright: ignore[reportUnknownMemberType]
            if self.arguments is None:
                return self.name
            elif isinstance(self.arguments, tuple):
                return {self.name: self.arguments[0]}
            else:
                return {self.name: self.arguments}
        else:
            return handler(self)
```

#### name

```python
name: str
```

The name of the evaluator class; should be the value returned by `EvaluatorClass.get_serialization_name()`

#### arguments

```python
arguments: None | tuple[Any] | dict[str, Any]
```

The arguments to pass to the evaluator's constructor.

Can be None (no arguments), a tuple (a single positional argument), or a dict (keyword arguments).

#### args

```python
args: tuple[Any, ...]
```

Get the positional arguments for the evaluator.

Returns:

| Type              | Description                                                                        |
| ----------------- | ---------------------------------------------------------------------------------- |
| `tuple[Any, ...]` | A tuple of positional arguments if arguments is a tuple, otherwise an empty tuple. |

#### kwargs

```python
kwargs: dict[str, Any]
```

Get the keyword arguments for the evaluator.

Returns:

| Type             | Description                                                                        |
| ---------------- | ---------------------------------------------------------------------------------- |
| `dict[str, Any]` | A dictionary of keyword arguments if arguments is a dict, otherwise an empty dict. |

#### deserialize

```python
deserialize(
    value: Any,
    handler: ModelWrapValidatorHandler[EvaluatorSpec],
) -> EvaluatorSpec
```

Deserialize an EvaluatorSpec from various formats.

This validator handles the various short forms of evaluator specifications, converting them to a consistent EvaluatorSpec instance.

Parameters:

| Name      | Type                                       | Description               | Default    |
| --------- | ------------------------------------------ | ------------------------- | ---------- |
| `value`   | `Any`                                      | The value to deserialize. | *required* |
| `handler` | `ModelWrapValidatorHandler[EvaluatorSpec]` | The validator handler.    | *required* |

Returns:

| Type            | Description                     |
| --------------- | ------------------------------- |
| `EvaluatorSpec` | The deserialized EvaluatorSpec. |

Raises:

| Type              | Description                          |
| ----------------- | ------------------------------------ |
| `ValidationError` | If the value cannot be deserialized. |

Source code in `pydantic_evals/pydantic_evals/evaluators/spec.py`

```python
@model_validator(mode='wrap')
@classmethod
def deserialize(cls, value: Any, handler: ModelWrapValidatorHandler[EvaluatorSpec]) -> EvaluatorSpec:
    """Deserialize an EvaluatorSpec from various formats.

    This validator handles the various short forms of evaluator specifications,
    converting them to a consistent EvaluatorSpec instance.

    Args:
        value: The value to deserialize.
        handler: The validator handler.

    Returns:
        The deserialized EvaluatorSpec.

    Raises:
        ValidationError: If the value cannot be deserialized.
    """
    try:
        result = handler(value)
        return result
    except ValidationError as exc:
        try:
            deserialized = _SerializedEvaluatorSpec.model_validate(value)
        except ValidationError:
            raise exc  # raise the original error
        return deserialized.to_evaluator_spec()
```

#### serialize

```python
serialize(
    handler: SerializerFunctionWrapHandler,
    info: SerializationInfo,
) -> Any
```

Serialize using the appropriate short-form if possible.

Returns:

| Type  | Description                                                               |
| ----- | ------------------------------------------------------------------------- |
| `Any` | The serialized evaluator specification, using the shortest form possible: |
| `Any` | Just the name if there are no arguments                                   |
| `Any` | {name: first_arg} if there's a single positional argument                 |
| `Any` | {name: {kwargs}} if there are multiple (keyword) arguments                |

Source code in `pydantic_evals/pydantic_evals/evaluators/spec.py`

```python
@model_serializer(mode='wrap')
def serialize(self, handler: SerializerFunctionWrapHandler, info: SerializationInfo) -> Any:
    """Serialize using the appropriate short-form if possible.

    Returns:
        The serialized evaluator specification, using the shortest form possible:
        - Just the name if there are no arguments
        - {name: first_arg} if there's a single positional argument
        - {name: {kwargs}} if there are multiple (keyword) arguments
    """
    if isinstance(info.context, dict) and info.context.get('use_short_form'):  # pyright: ignore[reportUnknownMemberType]
        if self.arguments is None:
            return self.name
        elif isinstance(self.arguments, tuple):
            return {self.name: self.arguments[0]}
        else:
            return {self.name: self.arguments}
    else:
        return handler(self)
```

### GradingOutput

Bases: `BaseModel`

The output of a grading operation.

Source code in `pydantic_evals/pydantic_evals/evaluators/llm_as_a_judge.py`

```python
class GradingOutput(BaseModel, populate_by_name=True):
    """The output of a grading operation."""

    reason: str
    pass_: bool = Field(validation_alias='pass', serialization_alias='pass')
    score: float
```

### judge_output

```python
judge_output(
    output: Any,
    rubric: str,
    model: Model | KnownModelName | str | None = None,
    model_settings: ModelSettings | None = None,
) -> GradingOutput
```

Judge the output of a model based on a rubric.

If the model is not specified, a default model is used. The default model starts as 'openai:gpt-5.2', but this can be changed using the `set_default_judge_model` function.

Source code in `pydantic_evals/pydantic_evals/evaluators/llm_as_a_judge.py`

```python
async def judge_output(
    output: Any,
    rubric: str,
    model: models.Model | models.KnownModelName | str | None = None,
    model_settings: ModelSettings | None = None,
) -> GradingOutput:
    """Judge the output of a model based on a rubric.

    If the model is not specified, a default model is used. The default model starts as 'openai:gpt-5.2',
    but this can be changed using the `set_default_judge_model` function.
    """
    user_prompt = _build_prompt(output=output, rubric=rubric)
    return (
        await _judge_output_agent.run(user_prompt, model=model or _default_model, model_settings=model_settings)
    ).output
```

### judge_input_output

```python
judge_input_output(
    inputs: Any,
    output: Any,
    rubric: str,
    model: Model | KnownModelName | str | None = None,
    model_settings: ModelSettings | None = None,
) -> GradingOutput
```

Judge the output of a model based on the inputs and a rubric.

If the model is not specified, a default model is used. The default model starts as 'openai:gpt-5.2', but this can be changed using the `set_default_judge_model` function.

Source code in `pydantic_evals/pydantic_evals/evaluators/llm_as_a_judge.py`

```python
async def judge_input_output(
    inputs: Any,
    output: Any,
    rubric: str,
    model: models.Model | models.KnownModelName | str | None = None,
    model_settings: ModelSettings | None = None,
) -> GradingOutput:
    """Judge the output of a model based on the inputs and a rubric.

    If the model is not specified, a default model is used. The default model starts as 'openai:gpt-5.2',
    but this can be changed using the `set_default_judge_model` function.
    """
    user_prompt = _build_prompt(inputs=inputs, output=output, rubric=rubric)

    return (
        await _judge_input_output_agent.run(user_prompt, model=model or _default_model, model_settings=model_settings)
    ).output
```

### judge_input_output_expected

```python
judge_input_output_expected(
    inputs: Any,
    output: Any,
    expected_output: Any,
    rubric: str,
    model: Model | KnownModelName | str | None = None,
    model_settings: ModelSettings | None = None,
) -> GradingOutput
```

Judge the output of a model based on the inputs and a rubric.

If the model is not specified, a default model is used. The default model starts as 'openai:gpt-5.2', but this can be changed using the `set_default_judge_model` function.

Source code in `pydantic_evals/pydantic_evals/evaluators/llm_as_a_judge.py`

```python
async def judge_input_output_expected(
    inputs: Any,
    output: Any,
    expected_output: Any,
    rubric: str,
    model: models.Model | models.KnownModelName | str | None = None,
    model_settings: ModelSettings | None = None,
) -> GradingOutput:
    """Judge the output of a model based on the inputs and a rubric.

    If the model is not specified, a default model is used. The default model starts as 'openai:gpt-5.2',
    but this can be changed using the `set_default_judge_model` function.
    """
    user_prompt = _build_prompt(inputs=inputs, output=output, rubric=rubric, expected_output=expected_output)

    return (
        await _judge_input_output_expected_agent.run(
            user_prompt, model=model or _default_model, model_settings=model_settings
        )
    ).output
```

### judge_output_expected

```python
judge_output_expected(
    output: Any,
    expected_output: Any,
    rubric: str,
    model: Model | KnownModelName | str | None = None,
    model_settings: ModelSettings | None = None,
) -> GradingOutput
```

Judge the output of a model based on the expected output, output, and a rubric.

If the model is not specified, a default model is used. The default model starts as 'openai:gpt-5.2', but this can be changed using the `set_default_judge_model` function.

Source code in `pydantic_evals/pydantic_evals/evaluators/llm_as_a_judge.py`

```python
async def judge_output_expected(
    output: Any,
    expected_output: Any,
    rubric: str,
    model: models.Model | models.KnownModelName | str | None = None,
    model_settings: ModelSettings | None = None,
) -> GradingOutput:
    """Judge the output of a model based on the expected output, output, and a rubric.

    If the model is not specified, a default model is used. The default model starts as 'openai:gpt-5.2',
    but this can be changed using the `set_default_judge_model` function.
    """
    user_prompt = _build_prompt(output=output, rubric=rubric, expected_output=expected_output)
    return (
        await _judge_output_expected_agent.run(
            user_prompt, model=model or _default_model, model_settings=model_settings
        )
    ).output
```

### set_default_judge_model

```python
set_default_judge_model(
    model: Model | KnownModelName,
) -> None
```

Set the default model used for judging.

This model is used if `None` is passed to the `model` argument of `judge_output` and `judge_input_output`.

Source code in `pydantic_evals/pydantic_evals/evaluators/llm_as_a_judge.py`

```python
def set_default_judge_model(model: models.Model | models.KnownModelName) -> None:
    """Set the default model used for judging.

    This model is used if `None` is passed to the `model` argument of `judge_output` and `judge_input_output`.
    """
    global _default_model
    _default_model = model
```
