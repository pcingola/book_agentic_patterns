"""Progress hooks for RubricEvaluator."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentic_patterns.core.rubric.models import RubricItem, RubricVerdict


class RubricEvaluatorListener:
    """Hooks called during rubric evaluation. Override to customise behaviour."""

    def on_start(self, total: int) -> None:
        pass

    def on_item_done(self, item: RubricItem, verdict: RubricVerdict, done: int, total: int) -> None:
        pass

    def on_done(self, verdicts: list[RubricVerdict]) -> None:
        pass


class PrintRubricEvaluatorListener(RubricEvaluatorListener):
    """Prints each verdict to stdout as it completes."""

    def on_start(self, total: int) -> None:
        print(f"Evaluating {total} rubric items in parallel...")

    def on_item_done(self, item: RubricItem, verdict: RubricVerdict, done: int, total: int) -> None:
        print(f"  [{done}/{total}] {verdict.status.value}  {item.title}")

    def on_done(self, verdicts: list[RubricVerdict]) -> None:
        passed = sum(1 for v in verdicts if v.status.value == "PASS")
        print(f"Done: {passed}/{len(verdicts)} passed")
