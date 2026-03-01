"""LLM-based cluster labelling."""

import json

from pydantic import BaseModel
from pydantic_ai import Agent

from agentic_patterns.core.agents import get_agent
from agentic_patterns.core.config.config import PROMPTS_DIR
from agentic_patterns.core.prompt import load_prompt
from agentic_patterns.core.vectordb.models import ClusterResult


class _ClusterLabel(BaseModel):
    label: str
    summary: str


async def label_clusters(
    result: ClusterResult, agent: Agent | None = None, max_items_per_cluster: int = 20
) -> ClusterResult:
    """Prompt the LLM to assign a label and summary to each cluster.

    Only `max_items_per_cluster` items are sampled per cluster to keep prompts within
    context limits. For large clusters this means the label is based on a representative
    sample, not the full contents.

    Note: clusters are labeled sequentially (one LLM call per cluster). For large numbers
    of clusters this becomes a bottleneck; parallelization is left as a future improvement.
    """
    if agent is None:
        agent = get_agent(output_type=_ClusterLabel)

    prompt_path = PROMPTS_DIR / "rag" / "label_clusters.md"
    labeled_clusters = []

    for cluster in result.clusters:
        sample = cluster.items[:max_items_per_cluster]
        items_text = json.dumps(
            [
                {"doc_id": item.doc_id, "text": item.text[:500]}
                for item in sample
            ],
            indent=2,
        )
        prompt = load_prompt(prompt_path, items=items_text)
        run_result = await agent.run(prompt)
        labeled = cluster.model_copy(
            update={
                "label": run_result.output.label,
                "summary": run_result.output.summary,
            }
        )
        labeled_clusters.append(labeled)

    return ClusterResult(clusters=labeled_clusters)
