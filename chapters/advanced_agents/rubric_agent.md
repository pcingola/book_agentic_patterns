## Rubric Agent

A Rubric Agent turns “committee-style” review into a repeatable, auditable, evidence-backed evaluation pipeline.

The core idea is composition: the agent does not invent new mechanisms so much as it wires together retrieval, structured extraction, clustering over historical feedback, and calibrated verdict assignment into one coherent loop. Compared to ad-hoc “LLM judging”, the rubric framing forces stable criterion IDs, explicit evidence requirements, and consistent application across time, which is what you need when reviewers can (and will) challenge both the criteria and the conclusions.

### Why rubrics are different from generic LLM evaluation

Most LLM-based evaluation is optimized for “pick the better answer” or “score this output,” and often relies on implicit criteria. A rubric pipeline makes the criteria first-class objects that can be versioned, diffed, and traced to source policy text and past committee behavior. This changes both engineering and governance: you can explain not just why an item failed, but which requirement it maps to, where that requirement came from, and what evidence would flip the verdict.

### Data model: stable IDs, evidence requirements, and cross-framework traceability

Rubric items need to be stable across revisions, even when text is reworded or moved. The typical design is a versioned `Rubric` with `RubricItem`s that include a stable `item_id`, a requirement strength, and an explicit `evidence_required` contract. For compliance-like domains, cross-framework mappings are critical because the same control intent appears in multiple standards (for example, access control requirements in SOC 2, HIPAA, and ISO 27001). ([ecfr.gov][1])

```python
class RequirementLevel(str, Enum):
    MUST = "MUST"
    SHOULD = "SHOULD"
    MAY = "MAY"

class RubricItem(BaseModel):
    item_id: str                 # stable across versions
    title: str
    requirement_level: RequirementLevel
    requirement_text: str        # canonicalized, de-duplicated phrasing
    evidence_required: list[str] # named artifacts or proofs, not free-form
    sources: list[SourceRef] = []
    framework_mappings: dict[str, list[str]] = {}  # e.g. {"SOC2":[...], "HIPAA":[...]}
    tags: set[str] = set()

class Rubric(BaseModel):
    rubric_id: str               # auto-generated UUID prefix
    name: str
    items: list[RubricItem] = []
    provenance: dict = {}        # sources + build metadata
```

### Three-stage pipeline

The pipeline splits cleanly into offline build/refinement and online assessment. This split matters operationally: offline steps can be slower, more expensive, and heavily reviewed; online steps need bounded latency and predictable costs.

### Stage 1: Rubric creation from policy (offline)

Rubric creation starts by ingesting policy handbooks, process guides, and control frameworks. Each chunk is processed with structured extraction that emits candidate requirements with explicit modality (MUST/SHOULD), scope, and evidence expectations. The agent then canonicalizes those candidates by deduplicating semantically equivalent items, assigning stable IDs, and normalizing evidence fields into a constrained vocabulary (so later retrieval can target specific artifact types).

A key design choice is to store provenance at the item level: each item should retain pointers to the policy spans that created it. That makes the rubric auditable when someone asks “why is this a requirement?”

`RubricSession` is the high-level API that handles chunking, indexing, extraction, and synthesis. Two workflows are supported: incremental (one document at a time) and batch (extract many, build once).

```python
# Incremental: each add_document() extracts + builds against existing rubric
session = RubricSession(“soc2_demo”)
rubric = await session.add_document(POLICY_TEXT, source=”soc2_policy”)
```

Under the hood, `RubricSession` delegates to `RubricBuilder`, which runs the three-phase pipeline: extraction, merge passes, and synthesis.

### Stage 2: Rubric refinement from history (offline)

Rubrics fail when they ignore precedent. Stage 2 adds meeting minutes, past reviews, and prior submissions to the same session. Because the structured extractor outputs MUST/SHOULD/MAY requirements, historical findings that match existing items add their source references, while findings that represent gaps not covered by the policy are promoted into new rubric items.

This stage produces an auditable diff. That diff is what you review with humans, because it is where institutional drift and “unwritten rules” enter the system.

```python
# Same session -- add_document merges into the existing rubric
rubric = await session.add_document(AUDIT_FINDINGS_TEXT, source=”audit_findings”)
```

For batch processing, use `extract()` to process all documents first, then `build()` once:

```python
session = RubricSession(“soc2_batch”)
await session.extract(POLICY_TEXT, source=”soc2_policy”)
await session.extract(AUDIT_FINDINGS_TEXT, source=”audit_findings”)
rubric = await session.build()
```

When rubrics grow large across many document sources, a `deduplicate()` pass merges semantically equivalent items back down. It re-clusters the existing rubric items, merges duplicates, and re-synthesizes -- the same merge and synthesis phases used during the initial build.

```python
rubric = await session.deduplicate()
```

### Stage 3: Evidence-backed assessment (online)

Online assessment begins by ingesting the submission (spec, slides, supporting docs) into a `project_index`. For each rubric item, the evaluator retrieves evidence across multiple indexes: policy (definition), history (precedent), and project (claimed implementation). The output is a per-item verdict—Pass, Risk, or Fail—backed by citations to retrieved spans. The citations are not optional: they are the mechanism that makes the pipeline defensible and debuggable.

This is also where you enforce consistency: verdict prompts must be constrained to the rubric item and the retrieved evidence, and the model must be prevented from “making up” missing artifacts.

```python
class VerdictStatus(str, Enum):
    PASS = "PASS"
    RISK = "RISK"
    FAIL = "FAIL"

class RubricVerdict(BaseModel):
    item_id: str
    status: VerdictStatus
    rationale: str
    citations: list[SpanRef] = []    # (index_name, doc_id, start, end)
    missing_evidence: list[str] = []

class RubricEvaluator:
    async def evaluate(self, rubric: Rubric, retriever: MultiSourceRetriever):
        verdicts = []
        for item in rubric.items:
            docs = await retriever.retrieve_all(item.requirement_text)
            verdict = await self._evaluate_item(item, docs)
            verdicts.append(verdict)
        return verdicts
```


### Compliance as the canonical application domain

Compliance workflows make the rubric pattern concrete because they already have the primitives the agent needs: control frameworks (policy), past audit findings (history), and implementation artifacts (project). Stage 1 becomes control extraction from regulatory or standards text; Stage 2 incorporates audit findings and corrective actions; Stage 3 performs evidence-based control assessment. This mapping is particularly direct for access control, which appears across HIPAA technical safeguards, ISO 27001 access control controls, and NIST SP 800-53 access control families. ([ecfr.gov][1])

Cross-framework mappings should be treated as traceability edges, not as loose annotations. When a rubric item maps to multiple frameworks, the packet can render per-framework views without re-evaluating the project, which keeps assessment consistent while satisfying different stakeholder checklists.

### Hands-on: end-to-end compliance assessment

A minimal end-to-end exercise uses (1) a small SOC 2 subset as policy text, (2) a handful of mock audit findings as history, and (3) a short project security description as the submission. The notebook demonstrates both workflows: incremental (`add_document()` called twice) and batch (`extract()` twice then `build()` once). Evaluation uses `RubricEvaluator` with a `MultiSourceRetriever` spanning policy, history, and project indexes. The stage outputs are: extracted controls with stable IDs; a refined rubric with new items promoted from historical findings; and a Pass/Risk/Fail table with a concise per-item rationale.

## References (references.md)

1. Joint Task Force. *Security and Privacy Controls for Information Systems and Organizations (NIST SP 800-53 Rev. 5)*. NIST, 2020. ([NIST Computer Security Resource Center][2])
2. Electronic Code of Federal Regulations. *45 CFR § 164.312 Technical safeguards (HIPAA Security Rule)*. eCFR, current version. ([ecfr.gov][1])
3. David Holloway. *ISO 27001 – Annex A.9: Access Control*. ISMS.online, 2025. ([ISMS.online][3])
4. Liu, Iter, Xu, et al. *G-Eval: NLG Evaluation using GPT-4 with Better Human Alignment*. EMNLP, 2023. ([arXiv][4])
5. Zheng, et al. *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena*. NeurIPS, 2023. ([arXiv][5])
6. Es, James, et al. *RAGAs: Automated Evaluation of Retrieval Augmented Generation*. arXiv, 2023. ([arXiv][6])
7. OpenAI. *Evals: A framework for evaluating LLMs and LLM systems*. GitHub repository, 2024. ([GitHub][7])

[1]: https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164/subpart-C/section-164.312?utm_source=chatgpt.com "45 CFR 164.312 -- Technical safeguards."
[2]: https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final?utm_source=chatgpt.com "SP 800-53 Rev. 5, Security and Privacy Controls ... - NIST CSRC"
[3]: https://www.isms.online/iso-27001/annex-a-2013/annex-a-9-access-control-2013/?utm_source=chatgpt.com "ISO 27001 – Annex A.9: Access Control | ISMS.online"
[4]: https://arxiv.org/abs/2303.16634?utm_source=chatgpt.com "G-Eval: NLG Evaluation using GPT-4 with Better Human Alignment"
[5]: https://arxiv.org/abs/2306.05685?utm_source=chatgpt.com "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena"
[6]: https://arxiv.org/abs/2309.15217?utm_source=chatgpt.com "Automated Evaluation of Retrieval Augmented Generation"
[7]: https://github.com/openai/evals?utm_source=chatgpt.com "openai/evals: Evals is a framework for evaluating LLMs ..."
