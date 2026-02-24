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


async def label_clusters(result: ClusterResult, agent: Agent | None = None) -> ClusterResult:
    """Prompt the LLM to assign a label and summary to each cluster."""
    if agent is None:
        agent = get_agent(output_type=_ClusterLabel)

    prompt_path = PROMPTS_DIR / "rag" / "label_clusters.md"
    labeled_clusters = []

    for cluster in result.clusters:
        items_text = json.dumps(
            [{"doc_id": item.doc_id, "text": item.text[:500]} for item in cluster.items],
            indent=2,
        )
        prompt = load_prompt(prompt_path, items=items_text)
        run_result = await agent.run(prompt)
        labeled = cluster.model_copy(update={"label": run_result.output.label, "summary": run_result.output.summary})
        labeled_clusters.append(labeled)

    return ClusterResult(clusters=labeled_clusters)
