# Rubric Agent

A pipeline for building evidence-backed evaluation rubrics from policy documents, refining them with historical audit data, and performing traceable assessments against those rubrics.

Located in `agents/rubric/`. Uses `get_agent()` with structured output and tools, and `load_prompt()` for each step. Prompts live in `prompts/rubric/`.


## Stage 1: Build from Policy

`RubricBuilder.build_from_policy(policy_index, rubric_name)` fetches all chunks from a `VectorDB` policy index, extracts MUST/SHOULD/MAY requirements via LLM, converts them to `PoolItem`s, and passes them through the unified `build()` pipeline. Returns a `Rubric`.

```python
from agentic_patterns.agents.rubric.builder import RubricBuilder
from agentic_patterns.agents.rubric.listener import PrintRubricListener
from agentic_patterns.core.vectordb.vectordb import get_vector_db

policy_index = get_vector_db("soc2_policies")
builder = RubricBuilder(listener=PrintRubricListener())
rubric = await builder.build_from_policy(policy_index, rubric_name="soc2")
```


## Stage 2: Refine with History

`refine_with_history(rubric, history_index)` extracts concern sentences from historical documents (meeting minutes, audit findings), converts them to `PoolItem`s, and runs them through `build()` against the existing rubric. New concerns that are not covered by existing items are promoted into new `RubricItem`s; matched concerns add their `SourceRef` to the existing item. Returns a new `Rubric`.

```python
from agentic_patterns.agents.rubric.builder import refine_with_history
from agentic_patterns.agents.rubric.listener import PrintRubricListener
from agentic_patterns.core.vectordb.vectordb import get_vector_db

history_index = get_vector_db("audit_findings")
rubric_v2 = await refine_with_history(rubric, history_index, listener=PrintRubricListener())
```


## Stage 3: Evidence-Backed Assessment

`RubricEvaluator.evaluate(rubric, retriever)` takes a `MultiSourceRetriever` spanning policy, history, and project sources. For each rubric item it retrieves evidence, then an LLM judges PASS/RISK/FAIL with citations and identifies missing evidence. Returns a list of `RubricVerdict` objects.

```python
from agentic_patterns.agents.rubric.evaluator import RubricEvaluator
from agentic_patterns.agents.rubric.listener import PrintRubricEvaluatorListener
from agentic_patterns.core.vectordb.multi_source import MultiSourceRetriever
from agentic_patterns.core.vectordb.vectordb import get_vector_db

retriever = MultiSourceRetriever(
    policy=policy_index,
    history=history_index,
    project=get_vector_db("project_docs"),
)
evaluator = RubricEvaluator(listener=PrintRubricEvaluatorListener())
verdicts = await evaluator.evaluate(rubric_v2, retriever)
```


## Unified Build Pipeline

Both Stage 1 and Stage 2 flow through `RubricBuilder.build(items, rubric)`:

**Intermediate merge passes** (while pool size > `batch_size`): cluster the pool by semantic similarity, run the merge agent on each group in parallel, collect merged and ejected items. Repeat until pool fits in one batch or no further reduction is possible.

**Synthesis phase**: run the synthesis agent on sequential batches. All batches share the same ephemeral vector index so items committed in earlier batches are visible to later ones via `rubric_find_similar_items`. When the rubric is small (< 50 items), the full current rubric is included in the prompt; when large, the agent uses `rubric_find_similar_items` to search instead.


## Models

All models are in `agents/rubric/models.py`.

`RequirementLevel` enum: MUST, SHOULD, MAY.

`VerdictStatus` enum: PASS, RISK, FAIL.

`SourceRef` holds a reference to one occurrence of an item in a source document (`doc_id`, `collection_name`).

`PoolItem` is the uniform type flowing through all build passes: `text` (the requirement or concern text) and `sources` (accumulated `SourceRef` list).

`RubricItem` holds one evaluable requirement: `item_id`, `title`, `requirement_level`, `requirement_text`, `evidence_required`, `sources` (list of `SourceRef`), optional `framework_mappings`, and `tags`.

`Rubric` is a versioned collection of items with a `rubric_id`, `name`, and `provenance` dict.

`SpanRef` points to a span within a retrieved document (index_name, doc_id, start, end) for citation purposes.

`RubricVerdict` is the per-item assessment result: `status`, `rationale`, `citations` (list of SpanRef), and `missing_evidence`.


## API Reference

### `agentic_patterns.agents.rubric.models`

| Name | Kind | Description |
|---|---|---|
| `RequirementLevel` | Enum | MUST, SHOULD, MAY |
| `VerdictStatus` | Enum | PASS, RISK, FAIL |
| `SourceRef` | Pydantic model | Reference to a source document |
| `PoolItem` | Pydantic model | Item flowing through the build pipeline |
| `RubricItem` | Pydantic model | Single evaluable requirement |
| `Rubric` | Pydantic model | Versioned collection of RubricItem |
| `SpanRef` | Pydantic model | Document span reference for citations |
| `RubricVerdict` | Pydantic model | Per-item assessment verdict |

### `agentic_patterns.agents.rubric.builder`

| Name | Kind | Description |
|---|---|---|
| `RubricBuilder(config_name, batch_size, max_passes, algorithm, listener)` | Class | Configures and runs the build pipeline |
| `RubricBuilder.build(items, rubric)` | Method | Unified pipeline: merge passes + synthesis -> Rubric |
| `RubricBuilder.build_from_policy(policy_index, rubric_name)` | Method | Stage 1: extract requirements -> build |
| `refine_with_history(rubric, history_index, ...)` | Function | Stage 2: extract concerns -> build with existing rubric |

### `agentic_patterns.agents.rubric.evaluator`

| Name | Kind | Description |
|---|---|---|
| `RubricEvaluator(config_name, max_results, listener)` | Class | Evidence-backed rubric assessment |
| `RubricEvaluator.evaluate(rubric, retriever)` | Method | Stage 3: per-item PASS/RISK/FAIL with citations |

### `agentic_patterns.agents.rubric.listener`

| Name | Kind | Description |
|---|---|---|
| `RubricListener` | Class | Base listener for build pipeline (on_pass_start, on_group_done, on_done) |
| `PrintRubricListener` | Class | Prints build progress to stdout |
| `RubricEvaluatorListener` | Class | Base listener for evaluation (on_item_start, on_item_done, on_done) |
| `PrintRubricEvaluatorListener` | Class | Prints evaluation progress to stdout |
