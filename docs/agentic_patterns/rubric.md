# Rubric Agent

A pipeline for building evidence-backed evaluation rubrics from policy documents, refining them with historical review data, and performing traceable assessments against those rubrics.

Located in `core/rubric/`. Uses `get_agent()` with structured output and `load_prompt()` for each step, same pattern as the deep research and adversarial agents. Prompts live in `prompts/rubric/`.


## Stage 1: Build from Policy

`RubricBuilder.build_from_policy(policy_index)` iterates all chunks in a `VectorDB` policy index, extracts MUST/SHOULD/MAY requirements via LLM, deduplicates them into a canonical set, and assigns stable content-addressed IDs. Returns a versioned `Rubric`.

```python
from agentic_patterns.core.rubric import RubricBuilder
from agentic_patterns.core.vectordb.vectordb import get_vector_db

policy_index = get_vector_db("soc2_policies")
builder = RubricBuilder(config_name="default")
rubric = await builder.build_from_policy(policy_index, rubric_name="soc2")
```


## Stage 2: Refine with History

`refine_with_history(rubric, history_index, policy_index)` extracts concern sentences from historical documents (meeting minutes, audit findings), clusters them, maps clusters to existing rubric items by cosine similarity, bumps weights for matched items, and promotes large unmatched clusters into new items when anchored by policy text. Returns a new rubric version.

```python
from agentic_patterns.core.rubric import refine_with_history
from agentic_patterns.core.vectordb.vectordb import get_vector_db

history_index = get_vector_db("audit_findings")
rubric_v2 = await refine_with_history(rubric, history_index, policy_index)
```


## Stage 3: Evidence-Backed Assessment

`RubricEvaluator.evaluate(rubric, retriever)` takes a `MultiSourceRetriever` spanning policy, history, and project sources. For each rubric item it retrieves evidence, then an LLM judges PASS/RISK/FAIL with citations and identifies missing evidence. Returns a list of `RubricVerdict` objects.

```python
from agentic_patterns.core.rubric import RubricEvaluator
from agentic_patterns.core.vectordb.multi_source import MultiSourceRetriever
from agentic_patterns.core.vectordb.vectordb import get_vector_db

retriever = MultiSourceRetriever({
    "policy": policy_index,
    "history": history_index,
    "project": get_vector_db("project_docs"),
})
evaluator = RubricEvaluator()
verdicts = await evaluator.evaluate(rubric_v2, retriever)
for v in verdicts:
    print(f"{v.item_id}: {v.status.value} -- {v.rationale}")
```


## Models

All models are in `core/rubric/models.py`.

`RequirementLevel` enum: MUST, SHOULD, MAY.

`VerdictStatus` enum: PASS, RISK, FAIL.

`RubricItem` holds one evaluable requirement with `item_id`, `title`, `requirement_level`, `requirement_text`, `evidence_required`, optional `framework_mappings` for cross-framework traceability, `weight` (bumped during refinement), and `tags`.

`Rubric` is a versioned collection of items with a `rubric_id` and `provenance` dict tracking how it was built.

`SpanRef` points to a span within a retrieved document (index_name, doc_id, start, end).

`RubricVerdict` is the per-item assessment result with `status`, `rationale`, `citations` (list of SpanRef), and `missing_evidence`.


## API Reference

### `agentic_patterns.core.rubric.models`

| Name | Kind | Description |
|---|---|---|
| `RequirementLevel` | Enum | MUST, SHOULD, MAY |
| `VerdictStatus` | Enum | PASS, RISK, FAIL |
| `RubricItem` | Pydantic model | Single evaluable requirement |
| `Rubric` | Pydantic model | Versioned collection of RubricItem |
| `SpanRef` | Pydantic model | Document span reference for citations |
| `RubricVerdict` | Pydantic model | Per-item assessment verdict |

### `agentic_patterns.core.rubric.builder`

| Name | Kind | Description |
|---|---|---|
| `RubricBuilder(config_name)` | Class | Builds rubrics from policy indexes |
| `RubricBuilder.build_from_policy(policy_index, rubric_name)` | Method | Stage 1: extract + canonicalize -> Rubric |
| `refine_with_history(rubric, history_index, policy_index, ...)` | Function | Stage 2: cluster concerns, map to items, bump weights, promote new items |

### `agentic_patterns.core.rubric.evaluator`

| Name | Kind | Description |
|---|---|---|
| `RubricEvaluator(config_name)` | Class | Evidence-backed rubric assessment |
| `RubricEvaluator.evaluate(rubric, retriever)` | Method | Stage 3: per-item PASS/RISK/FAIL with citations |
