# Rubric Agent

A pipeline for building evidence-backed evaluation rubrics from policy documents, refining them with historical audit data, and performing traceable assessments against those rubrics.

Located in `agents/rubric/`. Uses `get_agent()` with structured output and tools, and `load_prompt()` for each step. Prompts live in `prompts/rubric/`.


## RubricSession (primary API)

`RubricSession` is the high-level API that manages the full rubric lifecycle: chunking, indexing, extraction, merge, synthesis, and deduplication. All operations are checkpointed and scoped by content hash so nothing is ever lost or overwritten.

Two workflows are supported:

**Incremental** -- `add_document()` extracts from one document and merges into the existing rubric. Each call builds on the previous result.

```python
from agentic_patterns.agents.rubric.session import RubricSession
from agentic_patterns.agents.rubric.listener import PrintRubricListener

session = RubricSession("soc2_demo", listener=PrintRubricListener())
rubric = await session.add_document(POLICY_TEXT, source="soc2_policy")
rubric = await session.add_document(AUDIT_FINDINGS_TEXT, source="audit_findings")
```

**Batch** -- `extract()` processes documents without building. Call `build()` once to produce the rubric from the combined pool.

```python
session = RubricSession("soc2_batch", listener=PrintRubricListener())
await session.extract(POLICY_TEXT, source="soc2_policy")
await session.extract(AUDIT_FINDINGS_TEXT, source="audit_findings")
rubric = await session.build()
```

When rubrics grow large across many document sources, `deduplicate()` merges semantically equivalent items:

```python
rubric = await session.deduplicate()
```

`RubricSession` also accepts `add_index()` for power users with pre-built VectorDB indexes.


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

`add_documents` extracts requirements, then flows through `RubricBuilder.build(items, rubric)`:

**Intermediate merge passes** (while pool size > `batch_size`): cluster the pool by semantic similarity, run the merge agent on each group in parallel, collect merged and ejected items. Repeat until pool fits in one batch or no further reduction is possible.

**Synthesis phase**: run the synthesis agent on sequential batches. All batches share the same ephemeral vector index so items committed in earlier batches are visible to later ones via `rubric_find_similar_items`. When the rubric is small (< 50 items), the full current rubric is included in the prompt; when large, the agent uses `rubric_find_similar_items` to search instead.


## Checkpointing and Recovery

Every phase is checkpointed so the pipeline can resume after a crash. All checkpoint files are preserved forever as audit logs -- never deleted, never overwritten by a different operation. Re-running with the same content resumes from checkpoint. Writes are atomic (temp file + fsync + rename). All files are human-readable JSON (indent=2).

Checkpoints are scoped by content hash under `.rubric_synthesis/{rubric_id}/`:

```
.rubric_synthesis/{rubric_id}/
  extractions/{content_hash}/extraction.json   # per-document extraction results
  incremental/{content_hash}/                  # incremental build for one document
    extraction.json, merge.json, synthesis.json
  builds/{build_hash}/                         # full rebuild from all extractions
    merge.json, synthesis.json
  dedup/{dedup_hash}/                          # deduplication pass
    merge.json, synthesis.json
```

Content hash is `md5("|".join(sorted(doc_ids)))[:8]` -- deterministic, so the same content always maps to the same checkpoint directory. Build hash is computed from sorted extraction scope names. Dedup hash is computed from sorted rubric item IDs.

Each checkpoint file has a `status` field (`"in_progress"` or `"completed"`) so you can tell whether the phase finished successfully or was interrupted.

Transient errors (timeouts, connection drops, HTTP 5xx from the model provider) are retried with exponential backoff in all three phases. Configured via `max_retries` (default 3) and `retry_delay` (default 30s).


## Models

All models are in `agents/rubric/models.py`.

`RequirementLevel` enum: MUST, SHOULD, MAY.

`VerdictStatus` enum: PASS, RISK, FAIL.

`SourceRef` holds a reference to one occurrence of an item in a source document (`doc_id`, `collection_name`, `source_text`). The `source_text` field stores the original chunk text that was analyzed, providing a complete audit trail from extracted rule back to source.

`PoolItem` is the uniform type flowing through all build passes. It carries both a `text` field (used as the pipeline representation for LLM prompts and embedding) and structured extraction fields: `requirement_level`, `title`, `requirement_text`, `evidence_required`. The structured fields are populated during extraction and preserved in the extraction checkpoint. After merge passes they are cleared since the merged text may combine multiple items.

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
| `SourceRef` | Pydantic model | Source reference with audit trail (`doc_id`, `collection_name`, `source_text`) |
| `PoolItem` | Pydantic model | Pipeline item with structured extraction fields (`requirement_level`, `title`, `requirement_text`, `evidence_required`) |
| `RubricItem` | Pydantic model | Single evaluable requirement |
| `Rubric` | Pydantic model | Versioned collection of RubricItem |
| `SpanRef` | Pydantic model | Document span reference for citations |
| `RubricVerdict` | Pydantic model | Per-item assessment verdict |

### `agentic_patterns.agents.rubric.session`

| Name | Kind | Description |
|---|---|---|
| `RubricSession(name, rubric_id, listener, **builder_kwargs)` | Class | High-level API managing the full rubric lifecycle |
| `RubricSession.rubric` | Property | Current rubric |
| `RubricSession.add_document(text, source)` | Method | Extract from one document and incrementally build into rubric |
| `RubricSession.add_index(index)` | Method | Incremental build from a pre-built VectorDB index |
| `RubricSession.extract(text, source)` | Method | Extract requirements (checkpointed, no build) |
| `RubricSession.build()` | Method | Full rebuild from all completed extractions |
| `RubricSession.deduplicate()` | Method | Merge duplicate items in the current rubric |

### `agentic_patterns.agents.rubric.builder`

| Name | Kind | Description |
|---|---|---|
| `RubricBuilder(config_name, batch_size, max_passes, algorithm, listener, max_retries, retry_delay)` | Class | Low-level build pipeline engine |
| `RubricBuilder.build(items, rubric)` | Method | Merge passes + synthesis -> Rubric |
| `RubricBuilder.add_documents(rubric, index, ckpt_dir)` | Method | Extract requirements from index and merge into rubric |
| `RubricBuilder.deduplicate(rubric, ckpt_dir)` | Method | Merge duplicate items in a large rubric |

### `agentic_patterns.agents.rubric.evaluator`

| Name | Kind | Description |
|---|---|---|
| `RubricEvaluator(config_name, max_results, listener)` | Class | Evidence-backed rubric assessment |
| `RubricEvaluator.evaluate(rubric, retriever)` | Method | Stage 3: per-item PASS/RISK/FAIL with citations |

### `agentic_patterns.agents.rubric.listener`

| Name | Kind | Description |
|---|---|---|
| `RubricListener` | Class | Base listener for build pipeline (on_pass_start, on_group_done, on_checkpoint_loaded, on_retry, on_dedup_start, on_dedup_done, on_done) |
| `PrintRubricListener` | Class | Prints build progress to stdout |
| `RubricEvaluatorListener` | Class | Base listener for evaluation (on_item_start, on_item_done, on_done) |
| `PrintRubricEvaluatorListener` | Class | Prints evaluation progress to stdout |
