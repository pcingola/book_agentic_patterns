"""Progress hooks for rubric pipeline stages."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agentic_patterns.core.listeners import AgentListener

if TYPE_CHECKING:
    from agentic_patterns.core.rubric.models import Rubric, RubricItem, RubricVerdict


class RubricBuilderListener(AgentListener["Rubric"]):
    """Hooks called during rubric building. Override to customise behaviour."""

    async def on_extract_start(self, n_chunks: int) -> None:
        pass

    async def on_chunk_extracted(self, chunk_idx: int, n_chunks: int, n_reqs: int) -> None:
        pass

    async def on_canonicalize_start(self, n_candidates: int) -> None:
        pass


class PrintRubricBuilderListener(RubricBuilderListener):
    """Prints progress to stdout."""

    async def on_extract_start(self, n_chunks: int) -> None:
        print(f"Extracting requirements from {n_chunks} policy chunks...")

    async def on_chunk_extracted(self, chunk_idx: int, n_chunks: int, n_reqs: int) -> None:
        print(f"  [{chunk_idx}/{n_chunks}] {n_reqs} requirement(s) found")

    async def on_canonicalize_start(self, n_candidates: int) -> None:
        print(f"Canonicalizing {n_candidates} candidates...")

    async def on_done(self, rubric: Rubric) -> None:
        print(f"Done: {rubric.rubric_id} ({len(rubric.items)} items)")


class RubricRefinerListener(AgentListener["Rubric"]):
    """Hooks called during rubric refinement. Override to customise behaviour."""

    async def on_concerns_extracted(self, n_concerns: int) -> None:
        pass

    async def on_weight_bumped(self, item: RubricItem, old_weight: float, new_weight: float) -> None:
        pass

    async def on_item_promoted(self, item: RubricItem) -> None:
        pass


class PrintRubricRefinerListener(RubricRefinerListener):
    """Prints progress to stdout."""

    async def on_concerns_extracted(self, n_concerns: int) -> None:
        print(f"Extracted {n_concerns} concern(s) from history, mapping to rubric...")

    async def on_weight_bumped(self, item: RubricItem, old_weight: float, new_weight: float) -> None:
        print(f"  Weight bumped: {item.title}  ({old_weight:.1f} -> {new_weight:.1f})")

    async def on_item_promoted(self, item: RubricItem) -> None:
        print(f"  New item: [{item.requirement_level.value}] {item.title}")

    async def on_done(self, rubric: Rubric) -> None:
        print(f"Done: {rubric.rubric_id} ({len(rubric.items)} items)")


class RubricEvaluatorListener(AgentListener[list["RubricVerdict"]]):
    """Hooks called during rubric evaluation. Override to customise behaviour."""

    async def on_item_start(self, item: RubricItem, total: int) -> None:
        pass

    async def on_item_done(self, item: RubricItem, result: RubricVerdict, done: int, total: int) -> None:
        pass


class PrintRubricEvaluatorListener(RubricEvaluatorListener):
    """Prints each verdict to stdout as it completes."""

    async def on_start(self) -> None:
        print("Evaluating rubric items in parallel...")

    async def on_item_start(self, item: Any, total: int) -> None:
        print(f"  Checking: {item.title}...")

    async def on_item_done(self, item: Any, result: Any, done: int, total: int) -> None:
        print(f"  [{done}/{total}] {result.status.value}  {item.title}")

    async def on_done(self, verdicts: list[Any]) -> None:
        passed = sum(1 for v in verdicts if v.status.value == "PASS")
        print(f"Done: {passed}/{len(verdicts)} passed")
