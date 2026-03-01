"""Evidence-backed rubric assessment (Stage 3)."""

import logging

from pydantic import BaseModel

from agentic_patterns.core.agents.agents import get_agent
from agentic_patterns.core.agents.utils import run_parallel
from agentic_patterns.core.config.config import PROMPTS_DIR
from agentic_patterns.core.prompt import load_prompt
from agentic_patterns.core.listeners import AgentListener
from agentic_patterns.core.rubric.models import (
    Rubric,
    RubricItem,
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

    def __init__(
        self,
        *,
        config_name: str = "default",
        listener: AgentListener | None = None,
    ) -> None:
        self._config_name = config_name
        self._listener = listener

    async def evaluate(
        self,
        rubric: Rubric,
        retriever: MultiSourceRetriever,
        *,
        max_results: int = 5,
        concurrency: int | None = None,
    ) -> list[RubricVerdict]:
        agent = get_agent(config_name=self._config_name, output_type=_ItemJudgment)
        total = len(rubric.items)
        done_count = [0]

        if self._listener:
            await self._listener.on_start()

        async def _eval_item(item: RubricItem) -> RubricVerdict:
            if self._listener:
                await self._listener.on_item_start(item, total)
            docs = await retriever.retrieve_all(query=item.requirement_text, max_results=max_results)
            evidence_lines = [
                f"[{doc.metadata.get('source_collection', 'unknown')}:{doc.doc_id}] {doc.text}"
                for doc in docs
            ]
            evidence_text = "\n\n".join(evidence_lines) if evidence_lines else "(no evidence found)"

            prompt = load_prompt(
                RUBRIC_PROMPTS / "assess_item.md",
                item_id=item.item_id,
                title=item.title,
                requirement_level=item.requirement_level.value,
                requirement_text=item.requirement_text,
                evidence_required=", ".join(item.evidence_required),
                evidence=evidence_text,
            )
            judgment = (await agent.run(prompt)).output

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

            verdict = RubricVerdict(
                item_id=item.item_id,
                status=judgment.status,
                rationale=judgment.rationale,
                citations=citations,
                missing_evidence=judgment.missing_evidence,
            )

            done_count[0] += 1
            if self._listener:
                await self._listener.on_item_done(item, verdict, done_count[0], total)
            return verdict

        verdicts = await run_parallel(
            [_eval_item(item) for item in rubric.items], concurrency=concurrency
        )

        logger.info("Evaluated %d rubric items", len(verdicts))
        if self._listener:
            await self._listener.on_done(verdicts)
        return verdicts
