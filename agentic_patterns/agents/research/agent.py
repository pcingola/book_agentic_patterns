"""Deep research agent: iterative search, gap detection, conflict resolution, synthesis."""

import asyncio
import logging

from agentic_patterns.core.agents.agents import get_agent
from agentic_patterns.agents.research.listener import ResearchListener
from agentic_patterns.agents.research.models import (
    ResearchReport,
    _ConflictReport,
    _GapAssessment,
    _SubQuestions,
    _SynthesisOutput,
)
from agentic_patterns.agents.research.source import (
    SearchResult,
    SearchSource,
    SearchSourcePerplexity,
)
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
            parts.append(f"[{source_index}] ({r.source_type}) {r.title}")
            if r.url:
                parts.append(f"  URL: {r.url}")
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
        max_questions: int = 5,
        listener: ResearchListener | None = None,
    ):
        self._sources = (
            sources if sources is not None else [SearchSourcePerplexity.from_config()]
        )
        self._config_name = config_name
        self._max_iterations = max_iterations
        self._max_questions = max_questions
        self._listener = listener

    async def _search_all(self, query: str) -> list[SearchResult]:
        """Query all sources in parallel and merge results."""
        tasks = [source.search(query) for source in self._sources]
        results_lists = await asyncio.gather(*tasks, return_exceptions=True)
        merged = []
        for result in results_lists:
            if isinstance(result, Exception):
                raise result
            merged.extend(result)
        return merged

    async def _search_queries(
        self, queries: list[str]
    ) -> dict[str, list[SearchResult]]:
        """Run all queries in parallel and return a mapping of query -> results."""
        if self._listener:
            await self._listener.on_search_start(queries)
        tasks = {q: self._search_all(q) for q in queries}
        results = dict(zip(tasks.keys(), await asyncio.gather(*tasks.values())))
        if self._listener:
            await self._listener.on_search_done(sum(len(r) for r in results.values()))
        return results

    async def _decompose(self, question: str) -> list[str]:
        """Break the question into sub-questions."""
        agent = get_agent(config_name=self._config_name, output_type=_SubQuestions)
        prompt = load_prompt(
            RESEARCH_PROMPTS / "decompose.md",
            question=question,
            max_questions=self._max_questions,
        )
        sub_questions = (await agent.run(prompt)).output.questions
        logger.info("Decomposed into %d sub-questions", len(sub_questions))
        if self._listener:
            await self._listener.on_decompose(sub_questions)
        return sub_questions

    async def _assess_gaps(
        self, question: str, evidence: dict[str, list[SearchResult]], iteration: int
    ) -> _GapAssessment:
        """Assess whether the current evidence is sufficient."""
        if self._listener:
            await self._listener.on_gap_start(iteration)
        agent = get_agent(config_name=self._config_name, output_type=_GapAssessment)
        prompt = load_prompt(
            RESEARCH_PROMPTS / "assess_gaps.md",
            question=question,
            evidence_summary=_build_evidence_summary(evidence),
        )
        assessment = (await agent.run(prompt)).output
        if self._listener:
            await self._listener.on_gap_done(
                iteration, assessment.sufficient, assessment.gaps
            )
        return assessment

    async def _detect_conflicts(
        self, question: str, evidence: dict[str, list[SearchResult]]
    ) -> list[str]:
        """Detect conflicting claims across evidence."""
        if self._listener:
            await self._listener.on_conflict_start()
        agent = get_agent(config_name=self._config_name, output_type=_ConflictReport)
        prompt = load_prompt(
            RESEARCH_PROMPTS / "detect_conflicts.md",
            question=question,
            evidence_summary=_build_evidence_summary(evidence),
        )
        conflicts = (await agent.run(prompt)).output.conflicts
        if self._listener:
            await self._listener.on_conflict_done(conflicts)
        return conflicts

    async def _synthesize(
        self,
        question: str,
        evidence: dict[str, list[SearchResult]],
        conflicts: list[str],
    ) -> ResearchReport:
        """Synthesize evidence into a final report."""
        if self._listener:
            await self._listener.on_synthesis_start()
        conflicts_text = (
            "\n".join(f"- {c}" for c in conflicts)
            if conflicts
            else "No conflicts detected."
        )
        agent = get_agent(config_name=self._config_name, output_type=_SynthesisOutput)
        prompt = load_prompt(
            RESEARCH_PROMPTS / "synthesize.md",
            question=question,
            evidence_summary=_build_evidence_summary(evidence),
            conflicts=conflicts_text,
        )
        output = (await agent.run(prompt)).output
        return ResearchReport(content=output.content, references=output.references)

    async def run(self, question: str) -> ResearchReport:
        if self._listener:
            await self._listener.on_start()
        sub_questions = await self._decompose(question)

        evidence = await self._search_queries(sub_questions)

        for iteration in range(1, self._max_iterations + 1):
            assessment = await self._assess_gaps(question, evidence, iteration)
            if assessment.sufficient:
                break
            logger.info(
                "Iteration %d: %d gaps found, re-querying",
                iteration,
                len(assessment.gaps),
            )
            gap_results = await self._search_queries(assessment.gaps)
            for q, results in gap_results.items():
                evidence.setdefault(q, []).extend(results)

        conflicts = await self._detect_conflicts(question, evidence)
        report = await self._synthesize(question, evidence, conflicts)
        if self._listener:
            await self._listener.on_done(report)
        return report

    def __str__(self) -> str:
        return f"DeepResearchAgent(sources={len(self._sources)}, max_iterations={self._max_iterations}, max_questions={self._max_questions})"
