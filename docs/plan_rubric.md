# Plan: Rubric Agent — Implementation

## Context

Build a rubric-based evaluation system for criteria-driven assessment with evidence-grounded decision support. Four-step pipeline:
1. Build canonical rubric from policy docs (handbooks, process guides)
2. Refine with historical precedents (committee minutes, past presentations)
3. Assess a project against the rubric with mandatory evidence citations
4. Adversarial simulation — generate likely committee questions and a concrete fix plan

Domain for notebooks: investment committee review (policy = Investment Policy Statement, history = committee minutes + past proposals, project = new investment proposal). Generalizable to any governance/compliance context.

**Existing infrastructure used**:
- `get_vector_db(collection_name)` / `vdb_add()` / `vdb_query()` from `core/vectordb/vectordb.py`
- `embed_texts(texts)` (async) from `core/vectordb/embeddings.py`
- `get_agent(**kwargs)` / `run_agent(agent, prompt)` from `core/agents/agents.py`
  - `get_agent` accepts `output_type`, `system_prompt`, `tools` as kwargs → passes them to `pydantic_ai.Agent`
  - `run_agent` returns `(agent_run, nodes)`; result accessed as `agent_run.result.output`
- `load_prompt(path)` from `core/prompt.py` — loads markdown, resolves `{% include %}`, substitutes `{vars}`
- `PROMPTS_DIR` from `core/config/config.py`
- `tool_permission(ToolPermission.READ)` from `core/tools/permissions.py`
- `scipy` already in `pyproject.toml`

---

## 1. Data Models

**File**: `agentic_patterns/core/rubric/models.py`

```python
from enum import Enum
from pydantic import BaseModel


class RubricStatus(str, Enum):
    PASS = "Pass"
    RISK = "Risk"
    FAIL = "Fail"


class RubricItem(BaseModel):
    id: str                        # stable slug, e.g. "liquidity-001"
    description: str
    applicability: str             # when this item applies
    required_evidence: list[str]   # what the project must provide
    weight: float = 1.0            # learned from history; default 1.0
    source_spans: list[str]        # citation text from policy docs

    def __str__(self) -> str:
        return f"[{self.id}] {self.description} (weight={self.weight})"


class Rubric(BaseModel):
    version: str
    items: list[RubricItem]

    def __str__(self) -> str:
        return f"Rubric v{self.version} ({len(self.items)} items)"


class ItemAssessment(BaseModel):
    item_id: str
    status: RubricStatus
    citations: list[str]   # source spans backing the verdict
    rationale: str

    def __str__(self) -> str:
        return f"{self.item_id}: {self.status}"


class RubricAssessment(BaseModel):
    project: str
    rubric_version: str
    assessments: list[ItemAssessment]
    gaps: list[str]        # item_ids with Risk or Fail
    questions: list[str]   # adversarial committee questions
    fix_plan: list[str]    # concrete actions to address gaps

    def __str__(self) -> str:
        return f"Assessment({self.project}, {len(self.assessments)} items, {len(self.gaps)} gaps)"
```

---

## 2. Toolkit

**File**: `agentic_patterns/toolkits/rubric.py`

```python
from pathlib import Path

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import pdist

from agentic_patterns.core.rubric.models import Rubric
from agentic_patterns.core.vectordb.embeddings import embed_texts
from agentic_patterns.core.vectordb.vectordb import get_vector_db, vdb_add, vdb_query


def build_index(collection_name: str, chunks: list[str]) -> None:
    """Index text chunks into a named Chroma collection."""
    vdb = get_vector_db(collection_name)
    for i, chunk in enumerate(chunks):
        vdb_add(vdb, chunk, doc_id=f"{collection_name}-{i}")


def chunk_documents(paths: list[Path], chunk_size: int = 400) -> list[str]:
    """Split documents into overlapping text chunks (word-based, 50% overlap)."""
    chunks = []
    step = chunk_size // 2
    for path in paths:
        words = path.read_text(encoding="utf-8").split()
        for i in range(0, max(1, len(words) - chunk_size + 1), step):
            chunks.append(" ".join(words[i : i + chunk_size]))
    return chunks


async def cluster_concerns(
    concerns: list[str],
    min_size: int = 2,
    min_confidence: float = 0.65,
) -> list[list[str]]:
    """Cluster semantically similar concerns via hierarchical clustering.

    Returns only clusters with >= min_size members and cosine similarity >= min_confidence.
    """
    if len(concerns) < 2:
        return [concerns] if concerns else []
    embeddings = await embed_texts(concerns)
    matrix = np.array(embeddings)
    distances = pdist(matrix, metric="cosine")
    Z = linkage(distances, method="average")
    labels = fcluster(Z, t=1 - min_confidence, criterion="distance")
    clusters: dict[int, list[str]] = {}
    for concern, label in zip(concerns, labels):
        clusters.setdefault(int(label), []).append(concern)
    return [group for group in clusters.values() if len(group) >= min_size]


def load_rubric(path: Path) -> Rubric:
    """Load a Rubric from a JSON file."""
    return Rubric.model_validate_json(path.read_text(encoding="utf-8"))


def retrieve(collection_name: str, query: str, top_k: int = 5) -> list[str]:
    """Retrieve top-k text chunks from a named Chroma collection."""
    vdb = get_vector_db(collection_name)
    results = vdb_query(vdb, query, max_items=top_k)
    return [doc for doc, _meta, _score in results]


def save_rubric(rubric: Rubric, path: Path) -> None:
    """Persist a Rubric as JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rubric.model_dump_json(indent=2), encoding="utf-8")
```

---

## 3. Tool Wrapper

**File**: `agentic_patterns/tools/rubric.py`

```python
from agentic_patterns.core.tools.permissions import ToolPermission, tool_permission
from agentic_patterns.toolkits.rubric import retrieve


def get_all_tools() -> list:

    @tool_permission(ToolPermission.READ)
    def retrieve_context(collection_name: str, query: str, top_k: int = 5) -> str:
        """Retrieve relevant text chunks from a named index for a given query."""
        chunks = retrieve(collection_name, query, top_k)
        return "\n---\n".join(chunks) if chunks else "No relevant context found."

    return [retrieve_context]
```

---

## 4. Prompts

**Directory**: `prompts/rubric/`

Loaded via `load_prompt(PROMPTS_DIR / "rubric" / "<file>")`.

### System prompts (one per agent)

| File | Purpose |
|---|---|
| `builder_system.md` | You are an expert policy analyst. Extract structured requirements from policy documents and produce a canonical, deduplicated rubric. For each requirement assign a stable ID (domain-keyword-NNN), applicability rule, and list of required evidence. |
| `refiner_system.md` | You are an expert in committee decision analysis. Given a rubric and clusters of recurring concerns from meeting minutes, update item weights and promote new items when a cluster clearly exceeds the existing rubric. |
| `assessor_system.md` | You are a rigorous due-diligence analyst. For each rubric item, you will be given policy text, historical precedents, and project evidence. Assign Pass/Risk/Fail strictly based on evidence. Every verdict must cite source text verbatim. |
| `simulator_system.md` | You are an adversarial committee member. Given a project assessment with gaps, generate the hardest likely questions the committee will ask and a concrete fix plan specifying what to add and where. |

### Task prompts (called within agents via structured user messages)

| File | Variables | Expected structured output |
|---|---|---|
| `extract_requirements.md` | `{chunks}` | Markdown list of MUST/SHOULD requirements |
| `canonicalize_rubric.md` | `{requirements}` | JSON matching `list[RubricItem]` |
| `extract_concerns.md` | `{chunks}` | JSON `list[str]` (short concern phrases, one per finding) |
| `refine_rubric.md` | `{rubric_json}`, `{clusters_json}` | JSON matching `Rubric` |
| `assess_rubric_item.md` | `{item_json}`, `{policy_context}`, `{precedent_context}`, `{project_context}` | JSON matching `ItemAssessment` |
| `simulate_committee.md` | `{assessment_json}`, `{history_context}` | JSON `list[str]` (questions) |
| `generate_fix_plan.md` | `{gaps_json}`, `{project_context}` | JSON `list[str]` (fix actions, each referencing a gap item_id) |

---

## 5. Agents

**Directory**: `agentic_patterns/agents/rubric/`

All agents follow the same pattern:

```python
from agentic_patterns.core.agents import get_agent, run_agent
from agentic_patterns.core.config.config import PROMPTS_DIR
from agentic_patterns.core.prompt import load_prompt

agent = get_agent(
    system_prompt=load_prompt(PROMPTS_DIR / "rubric" / "builder_system.md"),
    output_type=Rubric,   # structured output enforced by PydanticAI
)
agent_run, _ = await run_agent(agent, user_message)
result: Rubric = agent_run.result.output
```

### `builder_agent.py` — `run_builder(policy_chunks) -> Rubric`

1. Build `user_message` by calling `load_prompt` on `extract_requirements.md` with `chunks="\n\n".join(policy_chunks)`
2. Run agent (no tools needed, pure reasoning from context)
3. Second call with `canonicalize_rubric.md` to get structured `Rubric`

### `refiner_agent.py` — `run_refiner(rubric, history_chunks, clusters) -> Rubric`

1. Build user message from `refine_rubric.md` with `rubric_json` and `clusters_json`
2. Run agent (no tools), get updated `Rubric` with bumped version

### `assessor_agent.py` — `run_assessor(rubric, project_name, policy_col, history_col, project_col) -> RubricAssessment`

Loop over rubric items. For each item:
1. Build user message from `assess_rubric_item.md`, calling `retrieve()` toolkit inline for context
2. Run assessor agent → `ItemAssessment`

After loop, compute `gaps = [a.item_id for a in assessments if a.status != RubricStatus.PASS]`.
Return `RubricAssessment(project=project_name, rubric_version=rubric.version, assessments=assessments, gaps=gaps, questions=[], fix_plan=[])`.

### `simulator_agent.py` — `run_simulator(assessment, history_collection) -> RubricAssessment`

1. Retrieve history context for each gap item
2. Call `simulate_committee.md` → questions
3. Call `generate_fix_plan.md` → fix_plan
4. Return completed `RubricAssessment`

---

## 6. Orchestrator

**File**: `agentic_patterns/agents/rubric/orchestrator.py`

```python
from pathlib import Path
from pydantic import BaseModel
from agentic_patterns.core.rubric.models import RubricAssessment
from agentic_patterns.toolkits.rubric import build_index, chunk_documents, cluster_concerns, save_rubric
from agentic_patterns.agents.rubric.builder_agent import run_builder
from agentic_patterns.agents.rubric.refiner_agent import run_refiner
from agentic_patterns.agents.rubric.assessor_agent import run_assessor
from agentic_patterns.agents.rubric.simulator_agent import run_simulator


class RubricPipelineConfig(BaseModel):
    policy_paths: list[Path]
    history_paths: list[Path]
    project_paths: list[Path]
    project_name: str
    rubric_path: Path
    policy_collection: str = "rubric_policy"
    history_collection: str = "rubric_history"
    project_collection: str = "rubric_project"
    cluster_min_size: int = 2
    cluster_min_confidence: float = 0.65


async def run_rubric_pipeline(config: RubricPipelineConfig) -> RubricAssessment:
    policy_chunks = chunk_documents(config.policy_paths)
    history_chunks = chunk_documents(config.history_paths)
    project_chunks = chunk_documents(config.project_paths)
    build_index(config.policy_collection, policy_chunks)
    build_index(config.history_collection, history_chunks)
    build_index(config.project_collection, project_chunks)

    rubric = await run_builder(policy_chunks)
    clusters = await cluster_concerns(history_chunks, config.cluster_min_size, config.cluster_min_confidence)
    rubric = await run_refiner(rubric, history_chunks, clusters)
    save_rubric(rubric, config.rubric_path)

    assessment = await run_assessor(rubric, config.project_name, config.policy_collection, config.history_collection, config.project_collection)
    return await run_simulator(assessment, config.history_collection)
```

---

## 7. Notebooks

**Directory**: `agentic_patterns/examples/rubric_agent/`

No `set_user_session()`. Use `await run_agent(agent, prompt)` and access `agent_run.result.output`.

**Synthetic data** (defined inline, no external files needed):
- `POLICY_DOC`: one-page Investment Policy Statement with explicit MUST/SHOULD requirements (liquidity, diversification, ESG, reporting)
- `MINUTES_1/2/3`: three short committee minutes referencing concerns about concentration risk, climate exposure, quarterly reporting gaps
- `PROJECT_DOC`: one-page investment proposal with partial compliance (passes liquidity, fails ESG, risk on reporting)

### `example_rubric_offline.ipynb`

Steps 1 & 2. Sections:
1. Write synthetic docs to temp files, call `chunk_documents` + `build_index`
2. Call `run_builder` → display rubric as table
3. Call `cluster_concerns` + `run_refiner` → display diff (changed weights, new items)

### `example_rubric_online.ipynb`

Steps 3 & 4. Sections:
1. Load rubric, index project doc
2. Call `run_assessor` → display assessment table (item_id | status | rationale | citations)
3. Call `run_simulator` → display question bank + fix plan

---

## Files to Create

```
agentic_patterns/core/rubric/models.py
agentic_patterns/toolkits/rubric.py
agentic_patterns/tools/rubric.py
agentic_patterns/agents/rubric/builder_agent.py
agentic_patterns/agents/rubric/refiner_agent.py
agentic_patterns/agents/rubric/assessor_agent.py
agentic_patterns/agents/rubric/simulator_agent.py
agentic_patterns/agents/rubric/orchestrator.py
agentic_patterns/examples/rubric_agent/example_rubric_offline.ipynb
agentic_patterns/examples/rubric_agent/example_rubric_online.ipynb
prompts/rubric/builder_system.md
prompts/rubric/refiner_system.md
prompts/rubric/assessor_system.md
prompts/rubric/simulator_system.md
prompts/rubric/extract_requirements.md
prompts/rubric/canonicalize_rubric.md
prompts/rubric/extract_concerns.md
prompts/rubric/refine_rubric.md
prompts/rubric/assess_rubric_item.md
prompts/rubric/simulate_committee.md
prompts/rubric/generate_fix_plan.md
```

No changes needed to `pyproject.toml` (scipy already present) or `config.yaml` (defaults live in `RubricPipelineConfig`).
