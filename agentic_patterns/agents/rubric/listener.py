"""Listener interfaces for the rubric pipeline."""

from agentic_patterns.agents.rubric.models import Rubric, RubricVerdict


class RubricListener:
    """Callback hooks for the rubric build pipeline."""

    async def on_pass_start(self, pass_num: int, n_items: int) -> None:
        pass

    async def on_group_start(self, pass_num: int, group_num: int, n_groups: int) -> None:
        pass

    async def on_group_done(self, pass_num: int, n_groups_done: int, n_groups_total: int, items: list[str] | None = None) -> None:
        pass

    async def on_item_added(self, item_id: str, title: str, requirement_level: str) -> None:
        pass

    async def on_source_mapped(self, item_id: str, title: str) -> None:
        pass

    async def on_done(self, rubric: Rubric) -> None:
        pass


class PrintRubricListener(RubricListener):
    """Prints progress during rubric build."""

    async def on_pass_start(self, pass_num: int, n_items: int) -> None:
        if pass_num == -1:
            print(f"[rubric] extracting requirements from {n_items} document chunks (in parallel)")
        elif pass_num == 0:
            print(f"[rubric] synthesis: mapping {n_items} candidates into rubric items")
        else:
            print(f"[rubric] merge pass {pass_num}: reducing {n_items} candidates by semantic similarity")

    async def on_group_start(self, pass_num: int, group_num: int, n_groups: int) -> None:
        if pass_num == 0:
            print(f"[rubric]   synthesis batch {group_num}/{n_groups}")
        elif pass_num >= 1:
            print(f"[rubric]   merging group {group_num}/{n_groups} ...")

    async def on_group_done(self, pass_num: int, n_groups_done: int, n_groups_total: int, items: list[str] | None = None) -> None:
        if pass_num == -1:
            print(f"[rubric]   chunk {n_groups_done}/{n_groups_total}: {len(items or [])} extracted")
            for item in (items or []):
                print(f"[rubric]     {item}")

    async def on_item_added(self, item_id: str, title: str, requirement_level: str) -> None:
        print(f"[rubric]     + [{requirement_level}] {title} ({item_id})")

    async def on_source_mapped(self, item_id: str, title: str) -> None:
        print(f"[rubric]     ~ mapped to existing: {title} ({item_id})")

    async def on_done(self, rubric: Rubric) -> None:
        print(f"[rubric] done: {len(rubric.items)} rubric items")


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
