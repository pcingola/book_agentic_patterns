from agentic_patterns.agents.research.models import ResearchReport
from agentic_patterns.core.listeners import AgentListener


class ResearchListener(AgentListener[ResearchReport]):
    """Hooks called at each step of the deep research pipeline. Override to customise behaviour."""

    async def on_decompose(self, questions: list[str]) -> None:
        pass

    async def on_search_start(self, questions: list[str]) -> None:
        pass

    async def on_search_done(self, results_count: int) -> None:
        pass

    async def on_gap_start(self, iteration: int) -> None:
        pass

    async def on_gap_done(
        self, iteration: int, sufficient: bool, gaps: list[str]
    ) -> None:
        pass

    async def on_conflict_start(self) -> None:
        pass

    async def on_conflict_done(self, conflicts: list[str]) -> None:
        pass

    async def on_synthesis_start(self) -> None:
        pass


class PrintResearchListener(ResearchListener):
    """Prints progress to stdout as each step completes."""

    async def on_start(self) -> None:
        print("Starting research...")

    async def on_decompose(self, questions: list[str]) -> None:
        print(f"Decomposed into {len(questions)} sub-questions:")
        for q in questions:
            print(f"  - {q}")

    async def on_search_start(self, questions: list[str]) -> None:
        print(f"\nSearching {len(questions)} queries...")

    async def on_search_done(self, results_count: int) -> None:
        print(f"Found {results_count} results.")

    async def on_gap_start(self, iteration: int) -> None:
        print(f"\nAssessing gaps (iteration {iteration})...")

    async def on_gap_done(
        self, iteration: int, sufficient: bool, gaps: list[str]
    ) -> None:
        if sufficient:
            print("Evidence sufficient, skipping further iterations.")
        else:
            print(f"Gaps found: {len(gaps)}")
            for g in gaps:
                print(f"  - {g}")

    async def on_conflict_start(self) -> None:
        print("\nDetecting conflicts...")

    async def on_conflict_done(self, conflicts: list[str]) -> None:
        if conflicts:
            print(f"Conflicts: {len(conflicts)}")
            for c in conflicts:
                print(f"  - {c}")
        else:
            print("No conflicts detected.")

    async def on_synthesis_start(self) -> None:
        print("\nSynthesizing report...")

    async def on_done(self, report: ResearchReport) -> None:
        print(
            f"Done. Report: {len(report.content)} chars, {len(report.references)} references."
        )
