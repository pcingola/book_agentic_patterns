"""Tests for RubricBuilder checkpoint scoping."""

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from agentic_patterns.agents.rubric.builder import RubricBuilder
from agentic_patterns.agents.rubric.models import (
    PoolItem,
    Rubric,
    RubricItem,
    RequirementLevel,
    SourceRef,
)


def _make_pool_items(n: int, prefix: str = "item") -> list[PoolItem]:
    return [
        PoolItem(
            text=f"{prefix}_{i}",
            sources=[SourceRef(doc_id=f"doc_{i}", collection_name="test")],
            label=f"{prefix}_{i}",
        )
        for i in range(n)
    ]


def _make_rubric_items(n: int) -> list[RubricItem]:
    return [
        RubricItem(
            item_id=f"r{i:03d}",
            title=f"Item {i}",
            requirement_level=RequirementLevel.MUST,
            requirement_text=f"Requirement {i}",
            evidence_required=[f"evidence_{i}"],
            sources=[SourceRef(doc_id=f"doc_{i}", collection_name="test")],
        )
        for i in range(n)
    ]


def _mock_index(doc_ids: list[str]):
    """Create a mock index with given doc_ids and texts."""
    texts = [f"text for {d}" for d in doc_ids]
    mock = type("MockIndex", (), {})()
    mock.name = "test_collection"
    mock.get_all_ids = lambda: list(doc_ids)
    mock.get_all_documents = lambda: (list(doc_ids), list(texts))
    return mock


class TestRubricBuilderCheckpointing(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._base_dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _make_builder(self) -> RubricBuilder:
        builder = RubricBuilder.__new__(RubricBuilder)
        builder._config_name = "default"
        builder._batch_size = 20
        builder._max_passes = 10
        builder._algorithm = "agglomerative"
        builder._listener = AsyncMock()
        builder._embedder = None
        builder._max_retries = 1
        builder._retry_delay = 0.0
        # Override _get_checkpoint_dir to use temp dir
        builder._get_checkpoint_dir = lambda rubric_id: self._get_ckpt_dir(rubric_id)
        return builder

    def _get_ckpt_dir(self, rubric_id: str) -> Path:
        d = self._base_dir / rubric_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    async def test_add_documents_different_indexes_different_checkpoints(self):
        builder = self._make_builder()
        rubric = Rubric(rubric_id="test_r", name="test")

        index_a = _mock_index(["a1", "a2"])
        index_b = _mock_index(["b1", "b2"])

        pool_a = _make_pool_items(2, "a")
        pool_b = _make_pool_items(2, "b")
        items_a = _make_rubric_items(2)
        items_b = _make_rubric_items(4)

        rubric_a = Rubric(rubric_id="test_r", name="test", items=items_a)
        rubric_b = Rubric(rubric_id="test_r", name="test", items=items_b)

        with (
            patch.object(
                builder,
                "_extract_with_checkpoint",
                new_callable=AsyncMock,
                side_effect=[pool_a, pool_b],
            ),
            patch.object(
                builder,
                "_merge_phase",
                new_callable=AsyncMock,
                side_effect=[pool_a, pool_b],
            ),
            patch.object(
                builder,
                "_synthesis_phase",
                new_callable=AsyncMock,
                side_effect=[rubric_a, rubric_b],
            ),
        ):
            await builder.add_documents(rubric, index_a)
            await builder.add_documents(rubric, index_b)

        hash_a = hashlib.md5("|".join(sorted(["a1", "a2"])).encode()).hexdigest()[:8]
        hash_b = hashlib.md5("|".join(sorted(["b1", "b2"])).encode()).hexdigest()[:8]

        incr_dir = self._base_dir / "test_r" / "incremental"
        self.assertTrue((incr_dir / hash_a).is_dir())
        self.assertTrue((incr_dir / hash_b).is_dir())
        self.assertNotEqual(hash_a, hash_b)

    async def test_add_documents_same_index_resumes(self):
        builder = self._make_builder()
        rubric = Rubric(rubric_id="test_r", name="test")
        index = _mock_index(["x1", "x2"])

        pool = _make_pool_items(2, "x")
        result_rubric = Rubric(
            rubric_id="test_r", name="test", items=_make_rubric_items(2)
        )

        extract_mock = AsyncMock(return_value=pool)
        merge_mock = AsyncMock(return_value=pool)
        synthesis_mock = AsyncMock(return_value=result_rubric)

        with (
            patch.object(builder, "_extract_with_checkpoint", extract_mock),
            patch.object(builder, "_merge_phase", merge_mock),
            patch.object(builder, "_synthesis_phase", synthesis_mock),
        ):
            await builder.add_documents(rubric, index)
            await builder.add_documents(rubric, index)

        # Both calls should use the same checkpoint dir
        hash_x = hashlib.md5("|".join(sorted(["x1", "x2"])).encode()).hexdigest()[:8]
        incr_dir = self._base_dir / "test_r" / "incremental"
        self.assertTrue((incr_dir / hash_x).is_dir())

        # _extract_with_checkpoint called twice with the same dir
        self.assertEqual(extract_mock.call_count, 2)
        dir_arg_1 = extract_mock.call_args_list[0][0][2]
        dir_arg_2 = extract_mock.call_args_list[1][0][2]
        self.assertEqual(dir_arg_1, dir_arg_2)

    async def test_deduplicate_own_checkpoint_dir(self):
        builder = self._make_builder()
        items = _make_rubric_items(25)  # > batch_size=20
        rubric = Rubric(rubric_id="test_r", name="test", items=items)

        pool = [
            PoolItem(text=f"item_{i}", sources=[], label=f"item_{i}") for i in range(25)
        ]
        deduped = Rubric(rubric_id="test_r", name="test", items=_make_rubric_items(15))

        with (
            patch.object(
                builder, "_merge_phase", new_callable=AsyncMock, return_value=pool
            ),
            patch.object(
                builder,
                "_synthesis_phase",
                new_callable=AsyncMock,
                return_value=deduped,
            ),
        ):
            await builder.deduplicate(rubric)

        item_ids = sorted(item.item_id for item in items)
        dedup_hash = hashlib.md5("|".join(item_ids).encode()).hexdigest()[:8]
        dedup_dir = self._base_dir / "test_r" / "dedup" / dedup_hash
        self.assertTrue(dedup_dir.is_dir())


if __name__ == "__main__":
    unittest.main()
