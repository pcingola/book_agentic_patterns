"""Tests for RubricSession."""

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from agentic_patterns.agents.rubric.models import (
    PoolItem,
    Rubric,
    RubricItem,
    RequirementLevel,
    SourceRef,
)
from agentic_patterns.agents.rubric.session import RubricSession


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


def _make_pool_items(n: int) -> list[PoolItem]:
    return [
        PoolItem(
            text=f"pool_{i}",
            sources=[SourceRef(doc_id=f"doc_{i}", collection_name="test")],
            label=f"pool_{i}",
        )
        for i in range(n)
    ]


class TestRubricSession(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._base_dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _make_session(self, name: str = "test") -> RubricSession:
        """Create a RubricSession with checkpoint dir redirected to temp."""
        session = RubricSession.__new__(RubricSession)
        session._name = name
        session._rubric_id = hashlib.md5(name.encode()).hexdigest()[:8]
        session._listener = AsyncMock()

        from agentic_patterns.agents.rubric.builder import RubricBuilder

        builder = RubricBuilder.__new__(RubricBuilder)
        builder._config_name = "default"
        builder._batch_size = 20
        builder._max_passes = 10
        builder._algorithm = "agglomerative"
        builder._listener = session._listener
        builder._embedder = None
        builder._max_retries = 1
        builder._retry_delay = 0.0

        base_dir = self._base_dir

        def _get_ckpt_dir(rubric_id):
            d = base_dir / rubric_id
            d.mkdir(parents=True, exist_ok=True)
            return d

        builder._get_checkpoint_dir = _get_ckpt_dir
        session._builder = builder
        session._rubric = Rubric(rubric_id=session._rubric_id, name=name)
        return session

    async def test_add_document(self):
        session = self._make_session()
        items = _make_rubric_items(3)
        result_rubric = Rubric(rubric_id=session._rubric_id, name="test", items=items)
        pool = _make_pool_items(3)

        mock_index = AsyncMock()
        mock_index.get_all_ids = lambda: ["d1", "d2"]

        with (
            patch.object(session, "_create_temp_index", return_value=mock_index),
            patch.object(
                session._builder,
                "_extract_with_checkpoint",
                new_callable=AsyncMock,
                return_value=pool,
            ),
            patch.object(
                session._builder,
                "_merge_phase",
                new_callable=AsyncMock,
                return_value=pool,
            ),
            patch.object(
                session._builder,
                "_synthesis_phase",
                new_callable=AsyncMock,
                return_value=result_rubric,
            ),
        ):
            rubric = await session.add_document("some text", source="test_src")

        self.assertEqual(len(rubric.items), 3)
        self.assertIs(rubric, session.rubric)

    async def test_extract_and_build(self):
        session = self._make_session()
        pool = _make_pool_items(5)
        items = _make_rubric_items(4)
        result_rubric = Rubric(rubric_id=session._rubric_id, name="test", items=items)

        mock_index = AsyncMock()
        mock_index.get_all_ids = lambda: ["e1"]

        with (
            patch.object(session, "_create_temp_index", return_value=mock_index),
            patch.object(
                session._builder,
                "_extract_with_checkpoint",
                new_callable=AsyncMock,
                return_value=pool,
            ),
        ):
            await session.extract("policy text", source="policy")
            await session.extract("audit text", source="audit")

        # Verify extraction dirs were created
        base = self._base_dir / session._rubric_id / "extractions"
        content_hash = hashlib.md5("e1".encode()).hexdigest()[:8]
        self.assertTrue((base / content_hash).is_dir())

        # Now build
        with (
            patch.object(session, "_collect_all_extractions", return_value=pool),
            patch.object(
                session._builder,
                "build",
                new_callable=AsyncMock,
                return_value=result_rubric,
            ),
        ):
            rubric = await session.build()

        self.assertEqual(len(rubric.items), 4)

    async def test_add_document_twice(self):
        session = self._make_session()

        items_1 = _make_rubric_items(3)
        items_2 = _make_rubric_items(5)
        rubric_1 = Rubric(rubric_id=session._rubric_id, name="test", items=items_1)
        rubric_2 = Rubric(rubric_id=session._rubric_id, name="test", items=items_2)
        pool = _make_pool_items(3)

        mock_index_a = type(
            "I",
            (),
            {"get_all_ids": lambda self_=None: ["a1", "a2"]},
        )()
        mock_index_b = type(
            "I",
            (),
            {"get_all_ids": lambda self_=None: ["b1", "b2"]},
        )()

        with (
            patch.object(
                session, "_create_temp_index", side_effect=[mock_index_a, mock_index_b]
            ),
            patch.object(
                session._builder,
                "_extract_with_checkpoint",
                new_callable=AsyncMock,
                return_value=pool,
            ),
            patch.object(
                session._builder,
                "_merge_phase",
                new_callable=AsyncMock,
                return_value=pool,
            ),
            patch.object(
                session._builder,
                "_synthesis_phase",
                new_callable=AsyncMock,
                side_effect=[rubric_1, rubric_2],
            ),
        ):
            r1 = await session.add_document("doc A", source="src_a")
            r2 = await session.add_document("doc B", source="src_b")

        self.assertEqual(len(r1.items), 3)
        self.assertEqual(len(r2.items), 5)
        self.assertIs(session.rubric, r2)

        # Both should have created separate dirs
        incr_dir = self._base_dir / session._rubric_id / "incremental"
        hash_a = hashlib.md5("|".join(sorted(["a1", "a2"])).encode()).hexdigest()[:8]
        hash_b = hashlib.md5("|".join(sorted(["b1", "b2"])).encode()).hexdigest()[:8]
        self.assertTrue((incr_dir / hash_a).is_dir())
        self.assertTrue((incr_dir / hash_b).is_dir())
        self.assertNotEqual(hash_a, hash_b)

    async def test_deduplicate(self):
        session = self._make_session()
        items = _make_rubric_items(25)
        session._rubric = Rubric(rubric_id=session._rubric_id, name="test", items=items)
        deduped = Rubric(
            rubric_id=session._rubric_id, name="test", items=_make_rubric_items(15)
        )

        with patch.object(
            session._builder,
            "deduplicate",
            new_callable=AsyncMock,
            return_value=deduped,
        ) as mock_dedup:
            result = await session.deduplicate()

        self.assertEqual(len(result.items), 15)
        self.assertIs(session.rubric, result)

        # Verify dedup was called with a ckpt_dir under dedup/
        call_kwargs = mock_dedup.call_args[1]
        self.assertIn("ckpt_dir", call_kwargs)
        ckpt_dir = call_kwargs["ckpt_dir"]
        self.assertIn("dedup", str(ckpt_dir))


if __name__ == "__main__":
    unittest.main()
