"""Listener interfaces for the rubric pipeline."""

from agentic_patterns.agents.rubric.models import Rubric, RubricVerdict


class RubricListener:
    """Callback hooks for the rubric build pipeline."""

    async def on_pass_start(self, pass_num: int, n_items: int) -> None:
        pass

    async def on_group_done(self, pass_num: int, n_groups_done: int, n_groups_total: int) -> None:
        pass

    async def on_done(self, rubric: Rubric) -> None:
        pass


class PrintRubricListener(RubricListener):
    """Prints progress during rubric build."""

    async def on_pass_start(self, pass_num: int, n_items: int) -> None:
        label = "synthesis" if pass_num == 0 else f"merge pass {pass_num}"
        print(f"[rubric] {label}: {n_items} items in pool")

    async def on_group_done(self, pass_num: int, n_groups_done: int, n_groups_total: int) -> None:
        label = "synthesis" if pass_num == 0 else f"pass {pass_num}"
        print(f"[rubric] {label}: {n_groups_done}/{n_groups_total} groups done")

    async def on_done(self, rubric: Rubric) -> None:
        print(f"[rubric] done: {rubric}")


class RubricEvaluatorListener:
    """Callback hooks for rubric evaluation."""

    async def on_item_start(self, item_id: str, title: str) -> None:
        pass

    async def on_item_done(self, item_id: str, verdict: RubricVerdict) -> None:
        pass

    async def on_done(self, verdicts: list[RubricVerdict]) -> None:
        pass


class PrintRubricEvaluatorListener(RubricEvaluatorListener):
    """Prints progress during rubric evaluation."""

    async def on_item_start(self, item_id: str, title: str) -> None:
        print(f"[eval] {item_id}: {title}")

    async def on_item_done(self, item_id: str, verdict: RubricVerdict) -> None:
        print(f"[eval] {item_id}: {verdict.status.value} -- {verdict.rationale[:80]}")

    async def on_done(self, verdicts: list[RubricVerdict]) -> None:
        counts = {s: sum(1 for v in verdicts if v.status.value == s) for s in ("PASS", "RISK", "FAIL")}
        print(f"[eval] done: {counts}")
