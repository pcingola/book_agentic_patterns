## Rubric Agent

A Rubric Agent turns criteria-driven evaluation into a repeatable, auditable, evidence-backed pipeline by composing structured extraction, semantic clustering, multi-source retrieval, and adversarial probing.

### Why rubrics are different from generic LLM evaluation

Most LLM-based evaluation asks a model to "score this output" or "pick the better answer," relying on implicit criteria baked into the prompt. This works for quick comparisons but breaks down when reviewers challenge the results: which requirement failed? Where did that requirement come from? What evidence was considered? A rubric pipeline addresses these questions by making criteria first-class objects that can be versioned, diffed, and traced to source policy text. The shift from implicit judgment to explicit criteria changes both engineering and governance: you can explain not just why an item failed, but which requirement it maps to, where that requirement originated, and what evidence would flip the verdict. LLM-Rubric demonstrates that rubric-based evaluation with calibrated, multidimensional criteria significantly improves alignment with human judges compared to single-score approaches. ([ACL Anthology][1])

### Data model: stable IDs, evidence requirements, and cross-framework traceability

Rubric items need to remain stable across revisions, even when wording shifts or requirements are reorganized. The data model centers on a versioned `Rubric` containing `RubricItem`s, each carrying a stable `item_id`, a requirement strength drawn from RFC 2119 language (MUST, SHOULD, MAY), and an explicit `evidence_required` contract that names the concrete artifact types needed to demonstrate compliance.

```python
class RequirementLevel(str, Enum):
    MUST = "MUST"
    SHOULD = "SHOULD"
    MAY = "MAY"

class RubricItem(BaseModel):
    item_id: str                 # stable across versions (e.g., "r001")
    title: str
    requirement_level: RequirementLevel
    requirement_text: str
    evidence_required: list[str] # named artifacts, not free-form
    sources: list[SourceRef] = []
    framework_mappings: dict[str, list[str]] = {}  # e.g. {"SOC2": [...]}
```

Two design choices deserve emphasis. First, `evidence_required` lists specific artifact types ("quarterly access review report," "TLS certificate inventory") rather than vague descriptions. This constrains the assessment phase to look for concrete evidence instead of accepting fluent prose as proof. Second, `framework_mappings` supports cross-standard traceability: the same access control intent appears in SOC 2, HIPAA technical safeguards, and ISO 27001 Annex A, and a single rubric item can track all three without duplicating the requirement. When a rubric item maps to multiple frameworks, per-framework views can be rendered without re-evaluating the project, keeping assessment consistent while satisfying different stakeholder checklists. ([ecfr.gov][2], [ISMS.online][7])

### Three-stage pipeline

The pipeline separates offline construction from online assessment. Stages 1 and 2 build and refine the rubric -- they can be slow, expensive, and heavily reviewed by humans before deployment. Stage 3 runs the rubric against a submission and produces evidence-backed verdicts -- it needs bounded latency and predictable costs.

### Stage 1: Structured extraction from policy text

Rubric creation begins by ingesting policy documents, control frameworks, and process guides. Each document is split into chunks (the default chunker uses semantic boundaries, though paragraph-level chunking can be substituted), and each chunk is sent to an LLM for structured extraction. The extractor is prompted as a policy analyst and returns a list of candidate requirements, each with a title, requirement level, requirement text, and a list of evidence types that would demonstrate compliance. The output is a typed `PoolItem` -- the uniform currency flowing through the entire build pipeline.

```python
prompt = load_prompt("extract_requirements.md", chunk_text=text)
agent = get_agent(output_type=ExtractedRequirements)
result = await agent.run(prompt)
# Returns: [{title, requirement_level, requirement_text, evidence_required}, ...]
```

Extraction runs in parallel across all chunks. Each chunk's results are checkpointed to disk immediately on completion, so a crash loses only the in-flight chunks while all completed chunks are preserved. Transient errors (timeouts, HTTP 5xx) are retried with exponential backoff; content-filter errors skip the chunk gracefully rather than halting the entire run. The extraction prompt constrains the model to pull only requirements that are explicitly stated or clearly implied -- no invention.

A key design choice is to store provenance at the item level: each pool item retains a `SourceRef` pointing to the chunk that produced it, including the original text. That makes the rubric auditable when someone later asks "why is this a requirement?"

### Stage 2: Refinement via semantic clustering

Raw extraction from multiple documents produces many candidates with heavy overlap. "Quarterly access reviews must be completed on time" might appear in the access control policy, in three separate audit findings from different quarters, and in a process guide, each worded differently. Stage 2 reduces this redundancy through iterative merge passes driven by semantic clustering, then synthesizes the reduced pool into the final rubric.

The merge phase operates as a convergent loop. While the pool is larger than a configurable batch size, the builder embeds all pool items, clusters them using agglomerative clustering over cosine similarity, and runs a merge agent on each cluster in parallel. The merge agent identifies the coherent core of each cluster -- requirements that address the same underlying compliance need -- and produces a single merged statement that preserves the strictest requirement level across the group. Items that do not belong (semantically unrelated outliers) are ejected back to the pool for the next pass. This approach draws on the insight behind SemDeDup: embedding-based similarity identifies semantic duplicates that exact string matching misses. ([arXiv][3])

```python
def merge_pass(pool, batch_size, algorithm):
    n_clusters = ceil(len(pool) / batch_size)
    groups = cluster(pool, n_clusters=n_clusters, algorithm=algorithm)
    new_pool = []
    for group in groups:
        result = merge_agent.run(group)  # {merged_text, ejected_indices}
        coherent = [g for i, g in enumerate(group) if i not in result.ejected_indices]
        new_pool.append(PoolItem(text=result.merged_text, sources=union(coherent)))
        new_pool.extend(group[i] for i in result.ejected_indices)
    return new_pool
```

The loop repeats until the pool fits in one batch or stops shrinking. The convergence check -- exit if the new pool is at least as large as the old one -- prevents infinite cycling when items cannot be merged further. Pool state is checkpointed after each completed pass, so a resume picks up from the last full pass rather than rerunning already-merged groups.

Once the pool is small enough, the synthesis phase converts pool items into final `RubricItem`s. The synthesis agent has three tools: `find_similar_items` (semantic search over the current rubric via a persistent vector index), `add_item` (create a new rubric item and index it), and `add_source` (record an additional source reference on an existing item). Batches are processed sequentially, and because `add_item` writes to the vector index immediately, every subsequent batch sees items committed by previous ones. This prevents cross-batch duplicates without requiring the full rubric in the prompt context. For rubrics above fifty items, the agent must call `find_similar_items` before deciding to add; for smaller rubrics, the full list is included directly in the prompt.

```python
# Synthesis tools -- closures over the live rubric and its vector index
async def rubric_find_similar_items(text, top_k=5) -> list[dict]:
    """Semantic search over current rubric items."""

async def rubric_add_item(title, requirement_level, requirement_text,
                          evidence_required, sources) -> str:
    """Create new rubric item and index it."""

async def rubric_add_source(item_id, doc_id, collection_name) -> None:
    """Map an additional source to an existing rubric item."""
```

`RubricSession` exposes two workflows on top of this machinery. In the incremental workflow, each `add_document()` call extracts, merges, and synthesizes against the current rubric, so the rubric grows document by document. In the batch workflow, `extract()` is called multiple times to checkpoint each document's pool items independently, and then `build()` pools everything together for a single merge-and-synthesize pass. Batch tends to produce a more compact rubric when documents overlap heavily; incremental lets you observe how each new document changes the criteria.

```python
# Incremental: rubric evolves with each document
session = RubricSession("soc2_demo")
rubric = await session.add_document(POLICY_TEXT, source="soc2_policy")
rubric = await session.add_document(AUDIT_FINDINGS_TEXT, source="audit_findings")

# Batch: extract all, build once
session = RubricSession("soc2_batch")
await session.extract(POLICY_TEXT, source="soc2_policy")
await session.extract(AUDIT_FINDINGS_TEXT, source="audit_findings")
rubric = await session.build()
```

When rubrics grow large across many sources, a `deduplicate()` pass re-clusters existing items by semantic similarity, merges duplicates through the same merge agent, and re-synthesizes into a cleaner set.

### Stage 3: Multi-source evidence-backed assessment

Assessment is where the rubric becomes an instrument. The evaluator processes rubric items sequentially; for each item, it retrieves evidence from multiple independent sources in parallel. A typical compliance setup uses three indexes: policy (what the requirement means), history (whether similar issues have occurred before), and project (the submission's own claims about its posture). The `MultiSourceRetriever` queries all registered vector indexes concurrently, deduplicates results by document ID (keeping the highest-scoring occurrence), and returns a merged, score-sorted evidence set.

```python
retriever = MultiSourceRetriever(
    policy=policy_index,
    history=history_index,
    project=project_index,
)
evaluator = RubricEvaluator()
verdicts = await evaluator.evaluate(rubric, retriever)
```

For each item, the evaluator formats the retrieved evidence with source attribution and relevance scores, then prompts an LLM acting as an evidence-based auditor. The model must produce a structured verdict: PASS (sufficient evidence demonstrates compliance), RISK (partial or ambiguous evidence), or FAIL (no credible evidence, or evidence contradicts the requirement). The verdict includes citations -- span references into the source documents -- and a list of missing evidence types. Citations are not decorative; they are the mechanism that makes the pipeline defensible and debuggable. When a reviewer questions a FAIL verdict, they can trace the judgment through the citation to the retrieved span, the source index, and the original document.

```python
class RubricVerdict(BaseModel):
    item_id: str
    status: VerdictStatus            # PASS, RISK, or FAIL
    rationale: str                   # concise explanation (2-4 sentences)
    citations: list[SpanRef] = []    # (index_name, doc_id, start, end)
    missing_evidence: list[str] = [] # expected artifact types not found
```

The multi-source design creates natural triangulation. Policy evidence establishes what the requirement means, historical evidence reveals whether similar issues have occurred before, and project evidence claims compliance. When project evidence contradicts historical evidence -- the project claims encryption is handled, but past audits found gaps -- the tension surfaces explicitly in the rationale rather than being papered over.

### The rubric as structured adversarial probe

A rubric pipeline is, at its core, a structured form of adversarial testing. Each MUST requirement with an explicit evidence contract is a targeted challenge: "show me the artifact, or fail." This is more systematic than ad-hoc red-teaming because the challenges are derived from policy rather than improvised, the evidence requirements are concrete rather than vague, and the verdicts are traceable rather than subjective.

The connection to the adversarial patterns discussed earlier in this chapter is direct. A red-team agent can operate on the rubric itself, probing for gaps in criteria coverage ("what failure modes does this rubric not test for?") or challenging the evidence behind PASS verdicts ("is a quarterly access review script sufficient evidence for RBAC enforcement, or should it also require role-definition documentation?"). Feeding RISK verdicts through a debate agent -- where one side argues the evidence is sufficient and the other argues it is not -- can surface ambiguities that a single-pass assessment would miss.

The pipeline also stress-tests rubric coverage against historical data. When audit findings from multiple quarters are added as documents in Stage 2, findings that do not map to any existing policy requirement are promoted into new rubric items. These are the "unwritten rules" and institutional knowledge that no policy document captures, and surfacing them is one of the highest-value outputs of the refinement process.

### Hands-on

See `example_rubric.ipynb` for a working notebook that demonstrates both workflows (incremental and batch) using a simplified SOC 2 subset as policy, mock audit findings as history, and a project security description as the submission under evaluation.

[1]: https://aclanthology.org/2024.acl-long.745/ "LLM-Rubric: A Multidimensional, Calibrated Approach to Automated Evaluation"
[2]: https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164/subpart-C/section-164.312 "45 CFR 164.312 -- Technical safeguards"
[3]: https://arxiv.org/abs/2303.09540 "SemDeDup: Data-efficient learning at web-scale through semantic deduplication"
[7]: https://www.isms.online/iso-27001/annex-a-2013/annex-a-9-access-control-2013/ "ISO 27001 -- Annex A.9: Access Control"
