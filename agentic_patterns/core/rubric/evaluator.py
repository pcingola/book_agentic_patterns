"""Evidence-backed rubric assessment (Stage 3)."""

import logging

from pydantic import BaseModel

from agentic_patterns.core.agents.agents import get_agent
from agentic_patterns.core.config.config import PROMPTS_DIR
from agentic_patterns.core.prompt import load_prompt
from agentic_patterns.core.rubric.models import (
    Rubric,
    RubricVerdict,
    SpanRef,
    VerdictStatus,
)
from agentic_patterns.core.vectordb.multi_source import MultiSourceRetriever

logger = logging.getLogger(__name__)

RUBRIC_PROMPTS = PROMPTS_DIR / "rubric"


class _ItemJudgment(BaseModel):
    status: VerdictStatus
    rationale: str
    citations: list[dict]
    missing_evidence: list[str] = []


class RubricEvaluator:
    """Evaluates each rubric item against evidence from multiple sources."""

    def __init__(self, *, config_name: str = "default") -> None:
        self._config_name = config_name

    async def evaluate(
        self, rubric: Rubric, retriever: MultiSourceRetriever
    ) -> list[RubricVerdict]:
        agent = get_agent(config_name=self._config_name, output_type=_ItemJudgment)
        verdicts: list[RubricVerdict] = []

        for item in rubric.items:
            docs = retriever.retrieve_all(query=item.requirement_text, max_results=10)
            evidence_lines = []
            for doc in docs:
                source = doc.metadata.get("source_collection", "unknown")
                evidence_lines.append(f"[{source}:{doc.doc_id}] {doc.text}")
            evidence_text = (
                "\n\n".join(evidence_lines) if evidence_lines else "(no evidence found)"
            )

            prompt = load_prompt(
                RUBRIC_PROMPTS / "assess_item.md",
                item_id=item.item_id,
                title=item.title,
                requirement_level=item.requirement_level.value,
                requirement_text=item.requirement_text,
                evidence_required=", ".join(item.evidence_required),
                evidence=evidence_text,
            )
            run_result = await agent.run(prompt)
            judgment = run_result.output

            citations = []
            for c in judgment.citations:
                try:
                    citations.append(
                        SpanRef(
                            index_name=str(c.get("index_name", "")),
                            doc_id=str(c.get("doc_id", "")),
                            start=int(c.get("start", 0)),
                            end=int(c.get("end", 0)),
                        )
                    )
                except (ValueError, TypeError):
                    continue

            verdicts.append(
                RubricVerdict(
                    item_id=item.item_id,
                    status=judgment.status,
                    rationale=judgment.rationale,
                    citations=citations,
                    missing_evidence=judgment.missing_evidence,
                )
            )

        logger.info("Evaluated %d rubric items", len(verdicts))
        return verdicts
