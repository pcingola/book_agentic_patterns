"""Deep research agent: iterative search, gap detection, conflict resolution, synthesis."""

import asyncio
import logging

from agentic_patterns.core.agents.agents import get_agent
from agentic_patterns.core.agents.research.models import (
    ResearchReport,
    _ConflictReport,
    _GapAssessment,
    _SubQuestions,
    _SynthesisOutput,
)
from agentic_patterns.core.agents.research.source import SearchResult, SearchSource, SearchSourcePerplexity
from agentic_patterns.core.config.config import PROMPTS_DIR
from agentic_patterns.core.prompt import load_prompt

logger = logging.getLogger(__name__)

RESEARCH_PROMPTS = PROMPTS_DIR / "research"


def _build_evidence_summary(evidence: dict[str, list[SearchResult]]) -> str:
    """Format accumulated evidence into a readable summary for prompts."""
    parts = []
    source_index = 0
    for question, results in evidence.items():
        parts.append(f"### Sub-question: {question}")
        for r in results:
            source_index += 1
            source_label = f"[{source_index}]"
            parts.append(f"{source_label} ({r.source_type}) {r.title}")
            if r.url:
                parts.append(f"  URL: {r.url}")
            # Truncate long content to keep prompt manageable
            content = r.content[:2000] if len(r.content) > 2000 else r.content
            parts.append(f"  Content: {content}")
        parts.append("")
    return "\n".join(parts)


class DeepResearchAgent:
    """Iterative deep research: decompose, search, assess gaps, detect conflicts, synthesize."""

    def __init__(
        self,
        sources: list[SearchSource] | None = None,
        *,
        config_name: str = "default",
        max_iterations: int = 2,
    ):
        self._sources = sources if sources is not None else [SearchSourcePerplexity.from_config()]
        self._config_name = config_name
        self._max_iterations = max_iterations

    async def _search_all(self, query: str) -> list[SearchResult]:
        """Query all sources in parallel and merge results."""
        tasks = [source.search(query) for source in self._sources]
        results_lists = await asyncio.gather(*tasks, return_exceptions=True)
        merged = []
        errors = []
        for result in results_lists:
            if isinstance(result, Exception):
                logger.warning("Search source error: %s", result)
                errors.append(result)
            else:
                merged.extend(result)
        if not merged and errors:
            raise errors[0]
        return merged

    async def run(self, question: str) -> ResearchReport:
        # Step 1: Decompose into sub-questions
        decompose_agent = get_agent(
            config_name=self._config_name, output_type=_SubQuestions
        )
        prompt = load_prompt(RESEARCH_PROMPTS / "decompose.md", question=question)
        result = await decompose_agent.run(prompt)
        sub_questions = result.output.questions
        logger.info("Decomposed into %d sub-questions", len(sub_questions))

        # Step 2: Search for each sub-question
        evidence: dict[str, list[SearchResult]] = {}
        search_tasks = {q: self._search_all(q) for q in sub_questions}
        for q, task in zip(
            search_tasks.keys(), await asyncio.gather(*search_tasks.values())
        ):
            evidence[q] = task

        # Step 3-4: Assess gaps and re-query (up to max_iterations)
        for iteration in range(self._max_iterations):
            evidence_summary = _build_evidence_summary(evidence)
            gap_agent = get_agent(
                config_name=self._config_name, output_type=_GapAssessment
            )
            gap_prompt = load_prompt(
                RESEARCH_PROMPTS / "assess_gaps.md",
                question=question,
                evidence_summary=evidence_summary,
            )
            gap_result = await gap_agent.run(gap_prompt)
            assessment = gap_result.output

            if assessment.sufficient:
                logger.info("Evidence sufficient after iteration %d", iteration)
                break

            logger.info(
                "Iteration %d: %d gaps found, re-querying",
                iteration,
                len(assessment.gaps),
            )
            gap_tasks = {g: self._search_all(g) for g in assessment.gaps}
            for g, results in zip(
                gap_tasks.keys(), await asyncio.gather(*gap_tasks.values())
            ):
                evidence.setdefault(g, []).extend(results)

        # Step 5: Detect conflicts
        evidence_summary = _build_evidence_summary(evidence)
        conflict_agent = get_agent(
            config_name=self._config_name, output_type=_ConflictReport
        )
        conflict_prompt = load_prompt(
            RESEARCH_PROMPTS / "detect_conflicts.md",
            question=question,
            evidence_summary=evidence_summary,
        )
        conflict_result = await conflict_agent.run(conflict_prompt)
        conflicts = conflict_result.output.conflicts
        conflicts_text = (
            "\n".join(f"- {c}" for c in conflicts)
            if conflicts
            else "No conflicts detected."
        )

        # Step 6: Synthesize
        synthesis_agent = get_agent(
            config_name=self._config_name, output_type=_SynthesisOutput
        )
        synth_prompt = load_prompt(
            RESEARCH_PROMPTS / "synthesize.md",
            question=question,
            evidence_summary=evidence_summary,
            conflicts=conflicts_text,
        )
        synth_result = await synthesis_agent.run(synth_prompt)
        output = synth_result.output

        return ResearchReport(content=output.content, references=output.references)

    def __str__(self) -> str:
        return f"DeepResearchAgent(sources={len(self._sources)}, max_iterations={self._max_iterations})"
