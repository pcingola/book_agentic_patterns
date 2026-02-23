# Plan: Rubric-Based Evaluation

Source: `PROMPT_rubric.md`

## Goal

Implement a rubric-based evaluation system as a new hands-on example that puts together RAG, multi-agent orchestration, and adversarial simulation. The example is general-purpose (criteria-driven assessment, evidence-grounded) but concrete enough to be instructive.

## Chapter Placement

New hands-on section added to the **Evals** chapter, after the existing Doctors section. Title: "Hands-on: Rubric-Based Evaluation". It demonstrates how the patterns from the book compose into a real-world quality-gate workflow.

Entry in `chapters.md`:

```
- [ ] Hands-on: Rubric-Based Evaluation -- Four-step pipeline: build canonical rubric from policy docs,
      refine with historical precedents, assess a project with evidence-grounded retrieval, then
      simulate adversarial committee questions and produce a fix plan.
```

## Data Models

File: `agentic_patterns/core/rubric/models.py`

```python
class RubricItem(BaseModel):
    id: str                       # stable slug, e.g. "data-privacy-001"
    description: str
    applicability: str            # when this item applies
    required_evidence: list[str]  # what the project must provide
    weight: float = 1.0           # learned from history
    source_spans: list[str]       # citations from policy docs

class Rubric(BaseModel):
    version: str
    items: list[RubricItem]

class RubricStatus(str, Enum):
    PASS = "Pass"
    RISK = "Risk"
    FAIL = "Fail"

class ItemAssessment(BaseModel):
    item_id: str
    status: RubricStatus
    citations: list[str]          # source spans backing the verdict
    rationale: str

class RubricAssessment(BaseModel):
    project: str
    rubric_version: str
    assessments: list[ItemAssessment]
    gaps: list[str]               # item_ids with Risk or Fail
    questions: list[str]          # adversarial committee questions
    fix_plan: list[str]           # concrete actions to address gaps
```

## RAG Infrastructure

Re-use `agentic_patterns/core/vectordb/` for indexing and retrieval. Three separate indexes are needed:

| Index | Content | Built when |
|---|---|---|
| `policy_index` | Chunks from handbooks and process guides | Step 1 (offline) |
| `history_index` | Chunks from committee minutes and past presentations | Step 2 (offline) |
| `project_index` | Chunks from project spec, slides, prior reviews | Step 3 (per project) |

Chunking uses the existing semantic chunker from the RAG chapter.

## Prompts

Directory: `prompts/rubric/`

| File | Purpose |
|---|---|
| `extract_requirements.md` | Extract MUST/SHOULD/checklist items from policy text chunks |
| `canonicalize_rubric.md` | Merge duplicates and assign stable IDs; output `list[RubricItem]` |
| `extract_concerns.md` | Extract short, concrete concerns from committee minutes chunks |
| `refine_rubric.md` | Given concern clusters, update weights or promote new items; output updated `Rubric` |
| `assess_rubric_item.md` | Given policy text, precedents, and project evidence, assign Pass/Risk/Fail with citations |
| `simulate_committee.md` | Given assessments and history chunks, generate likely adversarial questions |
| `generate_fix_plan.md` | Given gaps and project evidence, propose minimal concrete fixes |

## Toolkits

File: `agentic_patterns/toolkits/rubric.py`

Pure Python, no framework dependency.

```python
def chunk_documents(paths: list[Path]) -> list[str]: ...
def build_index(chunks: list[str], index_path: Path) -> None: ...
def retrieve(index_path: Path, query: str, top_k: int = 5) -> list[str]: ...
def cluster_concerns(concerns: list[str], embeddings: list[list[float]]) -> list[list[str]]: ...
def save_rubric(rubric: Rubric, path: Path) -> None: ...
def load_rubric(path: Path) -> Rubric: ...
```

Clustering uses cosine-similarity hierarchical clustering (scipy or sklearn) with configurable `min_size` and `min_confidence` thresholds to gate promotion of new rubric items.

## Agents

Each step is a separate PydanticAI agent. All use the same model config as the rest of the book.

### Step 1 — RubricBuilderAgent

File: `agentic_patterns/agents/rubric/builder_agent.py`

Input: paths to handbooks and process guides.
Output: `Rubric` (versioned, saved to disk).

Tools: `chunk_documents`, `build_index` (via toolkit wrappers), structured output `Rubric`.

### Step 2 — RubricRefinerAgent

File: `agentic_patterns/agents/rubric/refiner_agent.py`

Input: existing `Rubric`, paths to minutes and past presentations.
Output: updated `Rubric` (new version).

Tools: `chunk_documents`, `build_index`, `cluster_concerns`, `retrieve`.

### Step 3 — ProjectAssessorAgent

File: `agentic_patterns/agents/rubric/assessor_agent.py`

Input: `Rubric`, path to project documents.
Output: `RubricAssessment` (partial, without questions and fix plan).

This agent iterates over rubric items. For each item it calls `retrieve` on all three indexes and then uses `assess_rubric_item` prompt to assign a verdict.

### Step 4 — CommitteeSimulatorAgent

File: `agentic_patterns/agents/rubric/simulator_agent.py`

Input: `RubricAssessment` (gaps), `history_index`.
Output: `RubricAssessment` (completed, with `questions` and `fix_plan`).

## Orchestration

File: `agentic_patterns/agents/rubric/orchestrator.py`

A thin workflow (not an LLM agent) that sequences the four agents and passes artifacts between them. Follows the sequential workflow pattern from the Orchestration chapter.

```python
async def run_rubric_pipeline(config: RubricPipelineConfig) -> RubricAssessment:
    rubric = await build_rubric(config.policy_paths)
    rubric = await refine_rubric(rubric, config.history_paths)
    assessment = await assess_project(rubric, config.project_paths)
    assessment = await simulate_committee(assessment)
    return assessment
```

`RubricPipelineConfig` is a Pydantic model holding all input paths and thresholds.

## Hands-on Notebook

File: `agentic_patterns/examples/evals/example_rubric.ipynb`

Four sections mapping to the four steps. Uses small synthetic documents (a one-page "policy handbook", three short "committee minutes", and a one-page "project brief") so it runs without external data and finishes in under a minute.

Output cells show:
- The canonical rubric (table of RubricItems)
- Diffs introduced by refinement (new weights / new items)
- Assessment table (item × Pass/Risk/Fail with citation)
- Question bank and fix plan

## File Summary

```
agentic_patterns/
  core/rubric/models.py
  toolkits/rubric.py
  agents/rubric/
    builder_agent.py
    refiner_agent.py
    assessor_agent.py
    simulator_agent.py
    orchestrator.py
  examples/evals/
    example_rubric.ipynb
prompts/rubric/
  extract_requirements.md
  canonicalize_rubric.md
  extract_concerns.md
  refine_rubric.md
  assess_rubric_item.md
  simulate_committee.md
  generate_fix_plan.md
chapters/evals/
  hands_on_rubric.md        # new chapter section
```

## Open Questions

- **Clustering library**: scipy is not currently a dependency; sklearn may already be present via other deps. Confirm before adding.
- **Synthetic data**: The notebook needs compact synthetic policy/history/project documents that exercise all four steps without being contrived. Draft these before writing agent prompts.
- **Rubric versioning format**: SemVer string (e.g. `"1.2.0"`) is simplest; no migration tooling needed for the book example.
