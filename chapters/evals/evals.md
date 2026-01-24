## Evals

Evals are the discipline of turning “this agent seems to work” into repeatable, versioned evidence about correctness, quality, safety, and behavior.

### Evals for agents and workflows

An eval for an agentic system is rarely “input → output equals expected.” Instead, you are typically testing a workflow: retrieval, tool selection, tool execution, intermediate reasoning artifacts, and final response. A practical eval suite therefore has to handle three categories at once: outcome quality, process quality, and operational constraints (latency/cost/retries).

A useful mental model is to separate the static definition of what you want to test from the dynamic execution of running the system. In a code-first evaluation setup, you define a dataset containing cases and evaluators, then run an experiment that executes your task function (which may call an agent, a workflow graph, or a pipeline) over all cases, and finally produce a report that aggregates results. This definition/execution/results split is particularly important for agents because you will run the same dataset repeatedly against multiple variants: new prompts, different models, different tool implementations, different retrieval indexes, different guardrails. ([Pydantic AI][1])

At the case level, think of a case as a single test scenario with typed inputs and optional expected outputs plus metadata. Metadata is not decoration; it is what enables slicing and diagnosis. A case might carry tags like `domain=tax`, `language=es`, `tools=sql`, `difficulty=hard`, or `expected_behavior=no_external_calls`. Keeping these tags close to the case definition allows reports to answer questions like “did we regress only on Spanish prompts?” or “are failures concentrated in tool-using cases?”

Evaluators are the second half of the contract. They encode what “good” means for the case: sometimes as a deterministic assertion, sometimes as a numeric score, sometimes as a label, and sometimes as multiple results produced at once. Modern eval frameworks also treat the evaluator’s explanation as a first-class output, because “pass/fail” without a reason is not actionable during debugging. ([Pydantic AI][2])

A minimal abstraction set that scales from single-call LLM apps to complex agents looks like this:

```python
from dataclasses import dataclass
from typing import Any, Callable, Generic, Protocol, TypeVar

InputsT = TypeVar("InputsT")
OutputT = TypeVar("OutputT")

@dataclass(frozen=True)
class Case(Generic[InputsT, OutputT]):
    name: str
    inputs: InputsT
    expected_output: OutputT | None = None
    metadata: dict[str, Any] | None = None  # tags, difficulty, domain, etc.

# A result can be: assertion(bool), score(float), or label(str), optionally with a reason.
@dataclass(frozen=True)
class EvalResult:
    value: bool | float | str
    reason: str = ""

@dataclass(frozen=True)
class EvalContext(Generic[InputsT, OutputT]):
    case: Case[InputsT, OutputT]
    output: OutputT
    # Optional execution traces/telemetry identifiers for deeper debugging.
    trace_id: str | None = None
    span_id: str | None = None

class Evaluator(Protocol[InputsT, OutputT]):
    name: str
    def evaluate(self, ctx: EvalContext[InputsT, OutputT]) -> EvalResult | dict[str, EvalResult]:
        ...

@dataclass
class Dataset(Generic[InputsT, OutputT]):
    cases: list[Case[InputsT, OutputT]]
    evaluators: list[Evaluator[InputsT, OutputT]]
```

This structure captures the core idea: datasets describe intent, experiments execute the system, and reports summarize what happened, including per-case outputs and per-evaluation reasons, plus links back to execution traces when available. ([Pydantic AI][1])

### Structured-output evals vs free-form evals

In practice, “structured output” means your system returns a typed object with stable fields (for example: `{answer, citations, confidence, tool_calls}`) rather than an unconstrained string. The evaluation advantage is straightforward: you can write deterministic checks for structure and semantics, and you can compare to expected outputs using exact or near-exact matching. Structured outputs turn large parts of evals into normal software testing: type validation, invariant checking, and golden comparisons. ([Pydantic AI][2])

Free-form output is the default for many assistants: long natural language, flexible formatting, and variable phrasing. Free-form evals become difficult because exact matching is brittle. For free-form responses, you usually evaluate properties such as “answers the question,” “does not hallucinate,” “includes required sections,” or “uses the tool when required.” Some of these can still be checked deterministically (presence/absence of required strings, regex constraints, banned content checks), but many require semantic judgment.

A pragmatic pattern is to combine both approaches by introducing an intermediate “extraction” step: let the system respond freely, then extract a structured view for evaluation. The extraction can be deterministic (regex/JSON parsing if the response includes a machine-readable block) or model-assisted (a constrained parser that outputs a schema). The point is not to force your product UX into rigid JSON; it is to force your eval surface into something stable.

A common hybrid arrangement is:

1. Deterministic checks on structure and invariants (fast fail).
2. Numeric or label-based scoring for quality dimensions you can define precisely.
3. A judge-based evaluation for nuanced semantics, with the judge producing both a score and a reason.

This layering mirrors the “deterministic first, judge last” best practice for cost and reliability. ([Pydantic AI][3])

### LLM-as-a-Judge

LLM-as-a-Judge is the technique of using a capable model to grade another model’s output against a rubric. It is especially useful for open-ended tasks where you cannot write an exact oracle, such as long-form answers, multi-step reasoning explanations, summarization quality, or “helpfulness” under constraints.

Empirically, LLM judges can correlate surprisingly well with human preferences in certain settings and have become popular because they scale. Work such as MT-Bench and Chatbot Arena helped formalize judge-based evaluation for chat assistants and documented common judge biases (verbosity, position/order effects, self-enhancement), along with mitigation strategies. ([arXiv][4])

A judge must be treated like any other component: it needs a specification. The rubric should be explicit, testable, and ideally decomposed into multiple criteria rather than a single vague “quality” prompt. A strong practice is to run multiple judges (or multiple criteria prompts) and compare them, rather than assuming one judge captures everything. Another practice is to force judge consistency via low randomness and repeated trials, then aggregate. ([Pydantic AI][3])

A rubric-driven judge fits naturally into the evaluator abstraction:

```python
@dataclass
class Judge(Evaluator[InputsT, OutputT]):
    name: str
    rubric: str
    judge_model: Callable[[str], str]  # takes a prompt, returns model text

    def evaluate(self, ctx: EvalContext[InputsT, OutputT]) -> EvalResult:
        prompt = f"""
You are grading an assistant output.

Task input:
{ctx.case.inputs}

Assistant output:
{ctx.output}

Rubric:
{self.rubric}

Return:
- score: a number 0..10
- reason: one paragraph explaining the score, referencing the rubric
"""
        raw = self.judge_model(prompt)
        score = parse_score_0_to_10(raw)       # keep parsing deterministic
        reason = parse_reason(raw)
        return EvalResult(value=float(score), reason=reason)
```

The critical engineering point is that judge outputs must be constrained enough to be machine-consumable. If the judge’s response cannot be parsed deterministically, you have built a flaky evaluator.

Judge-based evaluation also has hard limitations. The judge is non-deterministic, inherits training biases, is sensitive to prompt framing, and can be expensive. Known issues such as length bias have motivated techniques like length-controlled comparisons and careful prompt design. Research and practitioner guidance emphasizes mitigation via explicit rubrics, multiple judges, deterministic pre-checks, caching, and reviewing reasons rather than only scores. ([Pydantic AI][3])

### Regression testing across model and prompt versions

Regression testing for AI systems is not optional; it is the only way to prevent “improvements” from silently breaking important behaviors. The key difference from classic regression testing is that outputs may shift even when nothing is “broken,” so you must decide what stability means.

The definition/execution/results split enables regression work. You keep the dataset definition stable (cases, metadata, evaluators), then run multiple experiments against it, where each experiment is a specific system variant: model version, prompt version, tool implementation, retrieval index snapshot, guardrails configuration. Reports from those runs are then compared along multiple axes. ([Pydantic AI][1])

The comparison should not be only “overall pass rate.” In agentic systems, regressions often hide inside slices. You want to compare:

* Aggregate metrics (assertion rates, average scores, latency/cost metrics).
* Per-tag metrics (by domain/language/difficulty/tool-usage).
* Per-case diffs (cases that flipped from pass to fail, or score drops beyond a threshold).
* Behavioral regressions (tool calls changed, retrieval omitted, unexpected external calls).

A minimal but effective workflow is:

1. Pin a baseline report for a known-good system variant.
2. For every change (prompt/model/tools), run the same dataset and produce a candidate report.
3. Compute diffs: newly failing cases, score deltas, and slice deltas.
4. Gate deployments on thresholds appropriate to the use case (hard gate for safety invariants, soft gate for quality metrics that tolerate small variance).
5. Store all artifacts: dataset version, report, and experiment metadata.

Two details matter in production engineering.

First, you must store provenance with every report: commit hashes, prompt fingerprints, model identifiers, and environment data. Without provenance, regression data is not actionable.

Second, you must manage flakiness explicitly. If an evaluator involves an LLM judge, you should expect variance and adopt tactics like temperature control, retries for transient failures, repeated runs with aggregation, caching, and limiting judge evaluation to changed cases when feasible. ([Pydantic AI][3])

### Core concepts and abstractions

The abstractions worth copying from modern eval tooling are the ones that make evals behave like engineering assets rather than ad-hoc scripts.

A dataset is a versioned artifact, not just a Python list. Storing datasets as YAML or JSON in a repository keeps evals reviewable, diffable, and portable. In addition, generating a JSON schema for dataset files enables IDE validation and autocompletion, which prevents eval drift and makes it easier for multiple engineers to contribute. ([Pydantic AI][5])

Evaluators should support three output shapes: assertions (boolean), scores (numeric), and labels (categorical), and they should be able to return multiple results at once. This becomes important when a single evaluator computes a bundle of related checks, such as `{format_ok, cites_sources, safety_ok}`. Capturing explicit reasons (as text) for failures is what connects evals to debugging loops. ([Pydantic AI][2])

Case-specific evaluators are a pragmatic necessity. Some cases require custom rubrics or thresholds. For example, one RAG case might require exactly two citations from a given corpus, while another case might permit broad references but demand an explicit uncertainty statement. Attaching evaluators at the case level avoids global evaluators becoming a tangle of conditional logic. ([Pydantic AI][2])

Finally, for agents, output-only evaluation is often insufficient. You frequently need process-level guarantees: “the agent must call the database tool,” “the agent must not call external search,” “the agent must use retrieval before answering,” or “the agent must not exceed a cost budget.” Span-based evaluation addresses this by asserting over execution traces (OpenTelemetry spans) captured during runtime, letting you test how the system executed, not only what it returned. ([Pydantic AI][6])

A process-level evaluator is conceptually just another evaluator that can read telemetry:

```python
@dataclass
class SpanMatcher(Evaluator[InputsT, OutputT]):
    name: str
    required: list[dict]  # declarative patterns: {"op": "tool.call", "tool": "sql.query"}
    forbidden: list[dict] | None = None

    def evaluate(self, ctx: EvalContext[InputsT, OutputT]) -> EvalResult:
        spans = load_spans(trace_id=ctx.trace_id)  # your OTel backend / captured trace
        ok_required = all(match_any(spans, pattern) for pattern in self.required)
        ok_forbidden = all(not match_any(spans, pattern) for pattern in (self.forbidden or []))
        ok = ok_required and ok_forbidden
        reason = build_span_reason(spans, self.required, self.forbidden)
        return EvalResult(value=bool(ok), reason=reason)
```

This is the key bridge between evals and observability: the same telemetry you rely on in production becomes the substrate for behavioral tests, and failing cases can link directly to trace identifiers for fast diagnosis. ([Pydantic AI][6])

[1]: https://ai.pydantic.dev/evals/
[2]: https://ai.pydantic.dev/evals/#evaluators
[3]: https://ai.pydantic.dev/evals/#llm-as-a-judge
[4]: https://arxiv.org/abs/2306.05685
[5]: https://ai.pydantic.dev/evals/#datasets
[6]: https://ai.pydantic.dev/evals/#span-based-evaluation
