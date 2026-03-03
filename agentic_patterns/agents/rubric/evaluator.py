"""Evidence-backed rubric assessment (Stage 3)."""

from agentic_patterns.agents.rubric.listener import RubricEvaluatorListener
from agentic_patterns.agents.rubric.models import Rubric, RubricVerdict
from agentic_patterns.core.agents.agents import get_agent
from agentic_patterns.core.config.config import PROMPTS_DIR
from agentic_patterns.core.prompt import load_prompt
from agentic_patterns.core.vectordb.models import RetrievedDocument
from agentic_patterns.core.vectordb.multi_source import MultiSourceRetriever

_RUBRIC_PROMPTS = PROMPTS_DIR / "rubric"


def _format_evidence(docs: list[RetrievedDocument]) -> str:
    parts = []
    for i, doc in enumerate(docs, 1):
        source = doc.metadata.get("source_collection", "unknown")
        parts.append(
            f"[{i}] ({source}) {doc.doc_id} (score={doc.score:.3f})\n{doc.text}"
        )
    return "\n\n".join(parts) if parts else "No evidence retrieved."


class RubricEvaluator:
    """Assesses each rubric item against retrieved evidence, returning PASS/RISK/FAIL verdicts."""

    def __init__(
        self,
        config_name: str = "default",
        max_results: int = 10,
        listener: RubricEvaluatorListener | None = None,
    ) -> None:
        self._config_name = config_name
        self._max_results = max_results
        self._listener = listener or RubricEvaluatorListener()

    async def evaluate(
        self, rubric: Rubric, retriever: MultiSourceRetriever
    ) -> list[RubricVerdict]:
        """Evaluate all rubric items against retrieved evidence."""
        verdicts = []
        for item in rubric.items:
            await self._listener.on_item_start(item.item_id, item.title)
            verdict = await self._evaluate_item(item, retriever)
            await self._listener.on_item_done(item.item_id, verdict)
            verdicts.append(verdict)
        await self._listener.on_done(verdicts)
        return verdicts

    async def _evaluate_item(
        self, item, retriever: MultiSourceRetriever
    ) -> RubricVerdict:
        docs = await retriever.retrieve_all(
            item.requirement_text, max_results=self._max_results
        )
        evidence = _format_evidence(docs)
        evidence_required_str = "\n".join(f"- {e}" for e in item.evidence_required)
        prompt = load_prompt(
            _RUBRIC_PROMPTS / "assess_item.md",
            item_id=item.item_id,
            title=item.title,
            requirement_level=item.requirement_level.value,
            requirement_text=item.requirement_text,
            evidence_required=evidence_required_str,
            evidence=evidence,
        )
        agent = get_agent(config_name=self._config_name, output_type=RubricVerdict)
        result = await agent.run(prompt)
        verdict = result.output
        # Ensure item_id is always correct regardless of model output
        return verdict.model_copy(update={"item_id": item.item_id})
