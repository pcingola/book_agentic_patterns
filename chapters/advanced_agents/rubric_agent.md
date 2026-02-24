## Rubric Agent

A Rubric Agent turns “committee-style” review into a repeatable, auditable, evidence-backed evaluation pipeline.

The core idea is composition: the agent does not invent new mechanisms so much as it wires together retrieval, structured extraction, clustering over historical feedback, calibrated verdict assignment, and adversarial stress-testing into one coherent loop. Compared to ad-hoc “LLM judging”, the rubric framing forces stable criterion IDs, explicit evidence requirements, and consistent application across time, which is what you need when reviewers can (and will) challenge both the criteria and the conclusions.

### Why rubrics are different from generic LLM evaluation

Most LLM-based evaluation is optimized for “pick the better answer” or “score this output,” and often relies on implicit criteria. A rubric pipeline makes the criteria first-class objects that can be versioned, diffed, and traced to source policy text and past committee behavior. This changes both engineering and governance: you can explain not just why an item failed, but which requirement it maps to, where that requirement came from, and what evidence would flip the verdict.

A practical rubric also needs to anticipate social dynamics. Committees do not only check compliance; they probe ambiguity, missing artifacts, and inconsistencies with precedent. That is why the final stage is adversarial simulation: it operationalizes “what will reviewers ask?” as a tool-driven output, not as informal intuition.

### Data model: stable IDs, evidence requirements, and cross-framework traceability

Rubric items need to be stable across revisions, even when text is reworded or moved. The typical design is a versioned `Rubric` with `RubricItem`s that include a stable `item_id`, a requirement strength, and an explicit `evidence_required` contract. For compliance-like domains, cross-framework mappings are critical because the same control intent appears in multiple standards (for example, access control requirements in SOC 2, HIPAA, and ISO 27001). ([ecfr.gov][1])

```python
class RubricItem(BaseModel):
    item_id: str                 # stable across versions
    title: str
    requirement_level: Literal["MUST", "SHOULD", "MAY"]
    requirement_text: str        # canonicalized, de-duplicated phrasing
    evidence_required: list[str] # named artifacts or proofs, not free-form
    framework_mappings: dict[str, list[str]] = {}  # e.g. {"SOC2":[...], "HIPAA":[...]}
    weight: float = 1.0
    tags: set[str] = set()

class Rubric(BaseModel):
    rubric_id: str               # versioned, e.g. "soc2-mini@v3"
    provenance: dict             # sources + build metadata
    items: list[RubricItem]
```

### Four-stage pipeline

The pipeline splits cleanly into offline build/refinement and online assessment/simulation. This split matters operationally: offline steps can be slower, more expensive, and heavily reviewed; online steps need bounded latency and predictable costs.

### Stage 1: Rubric creation from policy (offline)

Rubric creation starts by ingesting policy handbooks, process guides, and control frameworks into a `policy_index`. Each chunk is processed with structured extraction that emits candidate requirements with explicit modality (MUST/SHOULD), scope, and evidence expectations. The agent then canonicalizes those candidates by deduplicating semantically equivalent items, assigning stable IDs, and normalizing evidence fields into a constrained vocabulary (so later retrieval can target specific artifact types).

A key design choice is to store provenance at the item level: each item should retain pointers to the policy spans that created it. That makes the rubric auditable when someone asks “why is this a requirement?”

```python
class RubricBuilder:
    def build_from_policy(self, policy_index) -> Rubric:
        candidates = []
        for chunk in policy_index.iter_chunks():
            reqs = extract_requirements(chunk)   # structured output
            candidates.extend(reqs)

        canon = canonicalize_requirements(candidates)  # dedupe + normalize
        items = assign_stable_ids(canon)               # deterministic hashing + salt
        return Rubric(rubric_id=version(), provenance=provenance(), items=items)
```

### Stage 2: Rubric refinement from history (offline)

Rubrics fail when they ignore precedent. Stage 2 ingests meeting minutes, past reviews, and prior submissions into a `history_index`, extracts “concern sentences” (short, atomic statements of what reviewers flagged), and clusters them. The purpose of clustering is not just summarization; it is governance. If a large cluster is repeatedly mentioned and is not covered by the rubric, the agent can propose a new rubric item, but only under a gated promotion rule (for example: minimum cluster size, diversity across meetings, and at least one explicit policy anchor).

This stage produces an auditable diff. That diff is what you review with humans, because it is where institutional drift and “unwritten rules” enter the system.

```python
def refine_with_history(rubric: Rubric, history_index) -> Rubric:
    concerns = []
    for chunk in history_index.iter_chunks():
        concerns.extend(extract_concerns(chunk))   # short sentences, structured output

    clusters = cluster(concerns)
    labels   = label_clusters(clusters)
    mapping  = map_clusters_to_items(labels, rubric.items)

    for item_id in mapping.matched_item_ids:
        bump_weight(rubric, item_id, mapping[item_id].support)

    for c in mapping.unmatched_clusters:
        if c.size >= PROMOTION_THRESHOLD and c.policy_anchors_present:
            rubric.items.append(propose_new_item(c))  # still human-reviewed

    return rubric_versioned(rubric, diff=True)
```

### Stage 3: Evidence-backed assessment (online)

Online assessment begins by ingesting the submission (spec, slides, supporting docs) into a `project_index`. For each rubric item, the evaluator retrieves evidence across multiple indexes: policy (definition), history (precedent), and project (claimed implementation). The output is a per-item verdict—Pass, Risk, or Fail—backed by citations to retrieved spans. The citations are not optional: they are the mechanism that makes the pipeline defensible and debuggable.

This is also where you enforce consistency: verdict prompts must be constrained to the rubric item and the retrieved evidence, and the model must be prevented from “making up” missing artifacts.

```python
class RubricVerdict(BaseModel):
    item_id: str
    status: Literal["PASS", "RISK", "FAIL"]
    rationale: str
    citations: list["SpanRef"]     # (index_name, doc_id, start, end)
    missing_evidence: list[str] = []

class RubricEvaluator:
    def evaluate(self, rubric: Rubric, policy_index, history_index, project_index):
        status = []
        for item in rubric.items:
            evidence = MultiSourceRetriever.retrieve_all(
                query=item.requirement_text,
                sources=[policy_index, history_index, project_index],
                filters={"tags": item.tags},
            )
            verdict = judge_item(item, evidence)  # constrained output + citations required
            status.append(verdict)
        return status
```

### Stage 4: Adversarial simulation and committee packet (online)

The assessment output is not the end product; the end product is a committee packet. The Red Team stage consumes the rubric status table plus history, then generates a ranked question bank that targets weak points, ambiguities, and missing evidence. It also proposes fixes, which are best framed as concrete edits: what to add, where to add it, and which rubric item that addition would satisfy.

This stage is where prior “Adversarial & Debate Agents” composition shows up: a `RedTeamAgent` behaves like a hostile reviewer, while an “owner” sub-agent proposes remediations, and an arbiter can rank the questions by expected impact.

```python
class CommitteePacket(BaseModel):
    readiness_summary: str
    rubric_status: list[RubricVerdict]
    question_bank: list[str]     # ranked
    fix_plan: list[str]          # actionable edits tied to item_ids

def assemble_committee_packet(rubric_status, history_index) -> CommitteePacket:
    questions = RedTeamAgent().generate_questions(rubric_status, history_index)
    fixes = propose_fixes(rubric_status)  # focused on RISK/FAIL items
    return CommitteePacket(
        readiness_summary=summarize_readiness(rubric_status),
        rubric_status=rubric_status,
        question_bank=rank(questions),
        fix_plan=fixes,
    )
```

### Compliance as the canonical application domain

Compliance workflows make the rubric pattern concrete because they already have the primitives the agent needs: control frameworks (policy), past audit findings (history), implementation artifacts (project), and adversarial reviewers (external auditors). Stage 1 becomes control extraction from regulatory or standards text; Stage 2 incorporates audit findings and corrective actions; Stage 3 performs evidence-based control assessment; Stage 4 simulates the auditor’s questioning, producing an audit-ready packet. This mapping is particularly direct for access control, which appears across HIPAA technical safeguards, ISO 27001 access control controls, and NIST SP 800-53 access control families. ([ecfr.gov][1])

Cross-framework mappings should be treated as traceability edges, not as loose annotations. When a rubric item maps to multiple frameworks, the packet can render per-framework views without re-evaluating the project, which keeps assessment consistent while satisfying different stakeholder checklists.

### Hands-on: end-to-end compliance assessment packet

A minimal end-to-end exercise uses (1) a small SOC 2 subset as policy text, (2) a handful of mock audit findings as history, and (3) a short project security description as the submission. The stage outputs are: extracted controls with stable IDs; a refined rubric with weight bumps driven by clustered findings; a Pass/Risk/Fail table with citations; and an auditor-style question bank plus fix plan. The final rendering step produces a compliance packet that is mechanically generated from the `CommitteePacket`, rather than being treated as a separate agent pattern.

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
