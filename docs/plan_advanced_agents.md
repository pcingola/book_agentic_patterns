# Plan: Advanced Agents Chapter

## Overview

One chapter covering three agent types that each compose patterns from earlier chapters. The chapter is structured so each section builds on the previous: adversarial agents feed into deep research, which feeds into the rubric agent.

The original plan included a standalone Documentation Agent section (template-driven generation with RAG fill-in for SOWs, runbooks, etc.). This was dropped because it introduces no new pattern beyond what the Rubric Agent already demonstrates -- Stage 4 of the Rubric Agent already produces a structured long-form document from templates and retrieved context. The compliance-oriented hands-on exercise for the Rubric Agent covers the same use case in a richer setting.

The RAG chapter prerequisites (multi-source retrieval and semantic clustering) are implemented. See `docs/plan_rag.md` for details.

---

## RAG prerequisites (DONE)

Implemented in the RAG chapter. The actual API surface that advanced agents build on:

- `MultiSourceRetriever` (`core/vectordb/multi_source.py`): holds named `chromadb.Collection` sources, `retrieve_all(query, max_results, level)` queries all in parallel, merges and deduplicates. Source name preserved in `RetrievedDocument` metadata.
- `RetrievedDocument` (`core/vectordb/models.py`): `doc_id`, `text`, `score`, `level`, `parent_id`, `metadata` (includes serialized `DocumentProvenance` fields for provenance/citation).
- `cluster()` (`core/vectordb/clustering.py`): clusters chunks or a collection by embedding, returns `ClusterResult` with `list[Cluster]`. Each `Cluster` has `cluster_id`, `label`, `summary`, `items`.
- `label_clusters()` (`agents/rag/clustering.py`): LLM-powered labeling/summarization of clusters.
- `expand_query()` (`agents/rag/retrieval.py`): LLM query reformulation for broader recall.

**Still needed for the Rubric Agent (not part of the RAG plan):** `map_clusters_to_items(clusters, items, sim_threshold, min_size)` -- maps clusters onto existing rubric items by cosine similarity of cluster centroid vs item embedding. Returns matched items (with weight bump) and unmatched clusters above a size/confidence gate as new candidate items. To be implemented as part of this chapter's work, likely in `core/rubric/`.

---

## Chapter: Advanced Agents

### Section: Adversarial & Debate Agents

**Problem:** Any agent that produces an assessment, plan, or proposal benefits from having an adversary challenge it before a human sees it.

**Patterns:**

**Red-team agent:** Takes a structured result (status dict, plan, draft) and a context index (historical precedents, known failure modes). Generates a ranked list of challenges, questions, and gaps. Implemented as a single agent with a system prompt that explicitly instructs it to find weaknesses.

**Debate pattern:** Two sub-agents receive the same proposal. One argues for it (advocate), one argues against it (critic). An arbiter agent receives both arguments and produces a verdict with explicit reasoning. Implemented using `OrchestratorAgent` with two specialist sub-agents and a final arbiter call.

**Persona simulation:** An agent configured with a role description, domain background, and a retrieval tool over a persona-specific index. Multiple personas can be run in parallel and their outputs merged.

**Core library additions (`core/agents/`):**
- `RedTeamAgent`: wraps a standard agent with a red-team system prompt; takes `result: dict` and `context_index` as inputs
- `DebateOrchestrator`: spawns advocate + critic sub-agents, collects arguments, calls arbiter

**Hands-on:** Debate agent — two sub-agents argue opposite positions on a short proposal; arbiter produces a structured verdict. Show how the arbiter's reasoning changes when context indices are swapped.

---

### Section: Deep Research Agent

**Problem:** A single RAG query cannot answer questions that require iterative refinement, gap detection, and synthesis across contradicting sources.

**Core loop:**
1. Plan: decompose the research question into sub-questions (planning/decomposition pattern)
2. Retrieve: `MultiSourceRetriever.retrieve_all()` for each sub-question, accumulate `RetrievedDocument` evidence
3. Assess gaps: LLM identifies which sub-questions lack sufficient evidence
4. Re-query: reformulate via `expand_query()` and retrieve again for gap sub-questions
5. Conflict detection: find `RetrievedDocument` pairs with contradicting claims; surface them explicitly
6. Synthesize: produce a structured report with inline citations and a conflict summary
7. Stop: evidence sufficiency threshold, iteration cap, or human-in-the-loop checkpoint

**Core library additions:**
- `ResearchLoop`: orchestrates the plan-retrieve-gap-requery cycle; configurable `max_iterations` and `sufficiency_threshold`
- `EvidenceAccumulator`: collects `RetrievedDocument` objects keyed by sub-question; detects conflicts via embedding similarity + LLM arbitration
- `ConflictReport`: structured output listing contradicting source pairs with an arbitration note

**Hands-on:** Research agent over a heterogeneous corpus (mix of docs with deliberate contradictions). Show the iteration trace: which gaps triggered re-queries, which conflicts were surfaced, final cited report.

---

### Section: Rubric Agent

**Problem:** Committee-style evaluation requires traceable, evidence-backed criteria applied consistently to new submissions, with anticipation of reviewer challenges.

**This section is primarily composition.** All mechanisms are already built. The value is showing how they wire together into a coherent pipeline.

**Four-stage pipeline:**

**Stage 1 -- Rubric creation (offline):**
- Ingest policy handbooks and process guides into `policy_index`
- Extract MUST/SHOULD/checklist requirements per chunk (structured output)
- Canonicalize: deduplicate, assign stable IDs, set `evidence_required` fields
- Output: versioned `Rubric` object (Pydantic model, serialized to JSON)

**Stage 2 -- Rubric refinement (offline):**
- Ingest meeting minutes and past presentations into `history_index`
- Extract short concern sentences per document chunk
- `cluster()` + `label_clusters()` -> `map_clusters_to_items()` against existing rubric items
- Weight bump for matched items; gated promotion for large unmatched clusters
- Version the rubric; diff is auditable

**Stage 3 -- Project assessment (online):**
- Ingest project spec + slides + prior project minutes into `project_index`
- For each rubric item: `MultiSourceRetriever.retrieve_all()` across `{policy_index, history_index, project_index}`
- LLM assigns Pass / Risk / Fail with citations from retrieved chunks
- Output: status table (`RubricStatus`) with per-item verdicts and source spans

**Stage 4 -- Adversarial simulation (online):**
- `RedTeamAgent` over `RubricStatus` + `history_index` -> ranked question bank
- Gap detection: items with Risk/Fail -> `propose_fixes()` (where/what to add to the project)
- Assemble committee packet: readiness summary, status table, question bank, fix plan

**Core library additions:**
- `Rubric`, `RubricItem`, `RubricStatus`, `RubricVerdict` (Pydantic models in `core/rubric/`)
- `RubricBuilder`: stages 1 and 2 as callable steps
- `RubricEvaluator`: stage 3 loop
- `CommitteePacket`: stage 4 output model

**Compliance as the natural application domain.** The rubric pipeline maps directly onto regulatory compliance workflows (GxP, HIPAA, SOC 2, ISO 27001). Stage 1 becomes control framework extraction (parsing regulatory text into structured requirements). Stage 2 incorporates past audit findings and corrective actions. Stage 3 performs evidence-based assessment against controls. Stage 4 simulates the external auditor. This framing makes the section concrete and immediately applicable to enterprise readers, while also showing that "structured long-form document generation" (compliance reports, audit packets) is a rendering step on top of the assessment pipeline, not a separate agent pattern.

`RubricItem` supports an optional `framework_mappings` field for cross-framework traceability (e.g. SOC 2 CC6.1 maps to HIPAA 164.312(a)(1) and ISO 27001 A.9.2).

**Hands-on:** End-to-end compliance assessment pipeline. Sample corpus: a small subset of SOC 2 Trust Services Criteria as policy, a few mock audit findings as history, and a short project security description as the submission. Show each stage's output: extracted controls, refined rubric with audit-finding weight bumps, per-control Pass/Risk/Fail verdicts with citations, and the final auditor simulation with question bank. Final output is a rendered compliance packet.

---

### Section: Code Indexing and Search Agent

**Problem:** Keyword search fails for large codebases. Agents need semantic understanding of code structure to answer questions like "where is X implemented" or "what calls Y".

**Pattern:** Chunk code by logical unit (function/class), embed with a code-tuned model, store in a dedicated index. A search agent retrieves candidates and a re-ranker resolves cross-references.

**Hands-on:** Index a medium-sized Python codebase. Run natural-language queries. Show cross-reference resolution (find callers of a function, find implementations of an interface).

---

## Code additions summary

Already implemented (RAG chapter):

| Module | What |
|---|---|
| `core/vectordb/multi_source.py` | `MultiSourceRetriever` |
| `core/vectordb/models.py` | `RetrievedDocument`, `Cluster`, `ClusterResult` |
| `core/vectordb/clustering.py` | `cluster()` |
| `agents/rag/clustering.py` | `label_clusters()` |
| `agents/rag/retrieval.py` | `expand_query()` |

Still to implement (this chapter):

| Module | What |
|---|---|
| `core/agents/red_team.py` | `RedTeamAgent` |
| `core/agents/debate.py` | `DebateOrchestrator` |
| `core/agents/research_loop.py` | `ResearchLoop`, `EvidenceAccumulator`, `ConflictReport` |
| `core/rubric/models.py` | `Rubric`, `RubricItem`, `RubricStatus`, `RubricVerdict`, `CommitteePacket` |
| `core/rubric/builder.py` | `RubricBuilder` (stages 1 + 2) |
| `core/rubric/evaluator.py` | `RubricEvaluator` (stage 3) |
| `core/rubric/mapping.py` | `map_clusters_to_items()` |
