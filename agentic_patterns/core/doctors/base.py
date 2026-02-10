"""Base doctor class with batching logic."""

from typing import Any

from agentic_patterns.core.doctors.models import Recommendation


class DoctorBase:
    """Base class for all doctors with common batching logic."""

    default_batch_size: int = 5

    async def analyze(self, target: Any, verbose: bool = False) -> Recommendation:
        """Analyze a single target. Subclasses must implement this."""
        raise NotImplementedError

    async def analyze_batch(
        self,
        targets: list[Any],
        batch_size: int | None = None,
        verbose: bool = False,
    ) -> list[Recommendation]:
        """Process targets in batches to avoid overwhelming the model."""
        batch_size = batch_size or self.default_batch_size
        results = []
        total_batches = (len(targets) + batch_size - 1) // batch_size

        for i in range(0, len(targets), batch_size):
            batch = targets[i : i + batch_size]
            batch_num = i // batch_size + 1
            if verbose:
                print(
                    f"Processing batch {batch_num}/{total_batches} ({len(batch)} items)"
                )
            batch_results = await self._analyze_batch_internal(batch, verbose=verbose)
            results.extend(batch_results)

        return results

    async def _analyze_batch_internal(
        self, batch: list[Any], verbose: bool = False
    ) -> list[Recommendation]:
        """Analyze a batch of targets. Subclasses must implement this."""
        raise NotImplementedError
