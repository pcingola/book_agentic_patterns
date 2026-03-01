from agentic_patterns.core.agents.research.models import ResearchReport


class ResearchListener:
    """Hooks called at each step of the deep research pipeline. Override to customise behaviour."""

    def on_decompose(self, questions: list[str]) -> None:
        pass

    def on_search_start(self, questions: list[str]) -> None:
        pass

    def on_search_done(self, results_count: int) -> None:
        pass

    def on_gap_start(self, iteration: int) -> None:
        pass

    def on_gap_done(self, iteration: int, sufficient: bool, gaps: list[str]) -> None:
        pass

    def on_conflict_start(self) -> None:
        pass

    def on_conflict_done(self, conflicts: list[str]) -> None:
        pass

    def on_synthesis_start(self) -> None:
        pass

    def on_done(self, report: ResearchReport) -> None:
        pass


class PrintResearchListener(ResearchListener):
    """Prints progress to stdout as each step completes."""

    def on_decompose(self, questions: list[str]) -> None:
        print(f"Decomposed into {len(questions)} sub-questions:")
        for q in questions:
            print(f"  - {q}")

    def on_search_start(self, questions: list[str]) -> None:
        print(f"\nSearching {len(questions)} queries...")

    def on_search_done(self, results_count: int) -> None:
        print(f"Found {results_count} results.")

    def on_gap_start(self, iteration: int) -> None:
        print(f"\nAssessing gaps (iteration {iteration})...")

    def on_gap_done(self, iteration: int, sufficient: bool, gaps: list[str]) -> None:
        if sufficient:
            print("Evidence sufficient, skipping further iterations.")
        else:
            print(f"Gaps found: {len(gaps)}")
            for g in gaps:
                print(f"  - {g}")

    def on_conflict_start(self) -> None:
        print("\nDetecting conflicts...")

    def on_conflict_done(self, conflicts: list[str]) -> None:
        if conflicts:
            print(f"Conflicts: {len(conflicts)}")
            for c in conflicts:
                print(f"  - {c}")
        else:
            print("No conflicts detected.")

    def on_synthesis_start(self) -> None:
        print("\nSynthesizing report...")

    def on_done(self, report: ResearchReport) -> None:
        print(f"Done. Report: {len(report.content)} chars, {len(report.references)} references.")
