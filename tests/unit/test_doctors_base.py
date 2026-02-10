import asyncio
import unittest
from unittest.mock import patch

from agentic_patterns.core.doctors.base import DoctorBase
from agentic_patterns.core.doctors.models import Recommendation


class MockDoctor(DoctorBase):
    """Mock doctor for testing base class functionality."""

    def __init__(self):
        self.batches_processed = []

    async def analyze(self, target, verbose: bool = False) -> Recommendation:
        return Recommendation(name=str(target), needs_improvement=False, issues=[])

    async def _analyze_batch_internal(
        self, batch: list, verbose: bool = False
    ) -> list[Recommendation]:
        self.batches_processed.append(batch)
        return [
            Recommendation(name=str(t), needs_improvement=False, issues=[])
            for t in batch
        ]


class TestDoctorBase(unittest.TestCase):
    """Tests for agentic_patterns.core.doctors.base.DoctorBase class."""

    def test_default_batch_size(self):
        """Test default batch size is 5."""
        doctor = MockDoctor()
        self.assertEqual(doctor.default_batch_size, 5)

    def test_analyze_batch_single_batch(self):
        """Test analyze_batch with items fitting in one batch."""
        doctor = MockDoctor()
        targets = ["a", "b", "c"]

        results = asyncio.run(doctor.analyze_batch(targets, batch_size=5))

        self.assertEqual(len(results), 3)
        self.assertEqual(len(doctor.batches_processed), 1)
        self.assertEqual(doctor.batches_processed[0], ["a", "b", "c"])

    def test_analyze_batch_multiple_batches(self):
        """Test analyze_batch splits items into multiple batches."""
        doctor = MockDoctor()
        targets = ["a", "b", "c", "d", "e", "f", "g"]

        results = asyncio.run(doctor.analyze_batch(targets, batch_size=3))

        self.assertEqual(len(results), 7)
        self.assertEqual(len(doctor.batches_processed), 3)
        self.assertEqual(doctor.batches_processed[0], ["a", "b", "c"])
        self.assertEqual(doctor.batches_processed[1], ["d", "e", "f"])
        self.assertEqual(doctor.batches_processed[2], ["g"])

    def test_analyze_batch_exact_batch_size(self):
        """Test analyze_batch when items exactly fill batches."""
        doctor = MockDoctor()
        targets = ["a", "b", "c", "d"]

        results = asyncio.run(doctor.analyze_batch(targets, batch_size=2))

        self.assertEqual(len(results), 4)
        self.assertEqual(len(doctor.batches_processed), 2)
        self.assertEqual(doctor.batches_processed[0], ["a", "b"])
        self.assertEqual(doctor.batches_processed[1], ["c", "d"])

    def test_analyze_batch_uses_default_batch_size(self):
        """Test analyze_batch uses default_batch_size when not specified."""
        doctor = MockDoctor()
        targets = list(range(12))

        results = asyncio.run(doctor.analyze_batch(targets))

        self.assertEqual(len(results), 12)
        self.assertEqual(len(doctor.batches_processed), 3)
        self.assertEqual(len(doctor.batches_processed[0]), 5)
        self.assertEqual(len(doctor.batches_processed[1]), 5)
        self.assertEqual(len(doctor.batches_processed[2]), 2)

    def test_analyze_batch_empty_list(self):
        """Test analyze_batch with empty list."""
        doctor = MockDoctor()
        targets = []

        results = asyncio.run(doctor.analyze_batch(targets))

        self.assertEqual(len(results), 0)
        self.assertEqual(len(doctor.batches_processed), 0)

    def test_analyze_batch_verbose_output(self):
        """Test analyze_batch prints progress when verbose=True."""
        doctor = MockDoctor()
        targets = ["a", "b", "c", "d"]

        with patch("builtins.print") as mock_print:
            asyncio.run(doctor.analyze_batch(targets, batch_size=2, verbose=True))

        self.assertEqual(mock_print.call_count, 2)
        calls = [str(c) for c in mock_print.call_args_list]
        self.assertTrue(any("batch 1/2" in c for c in calls))
        self.assertTrue(any("batch 2/2" in c for c in calls))

    def test_analyze_batch_no_output_when_not_verbose(self):
        """Test analyze_batch does not print when verbose=False."""
        doctor = MockDoctor()
        targets = ["a", "b", "c", "d"]

        with patch("builtins.print") as mock_print:
            asyncio.run(doctor.analyze_batch(targets, batch_size=2, verbose=False))

        mock_print.assert_not_called()

    def test_analyze_not_implemented(self):
        """Test DoctorBase.analyze raises NotImplementedError."""
        doctor = DoctorBase()
        with self.assertRaises(NotImplementedError):
            asyncio.run(doctor.analyze("target"))

    def test_analyze_batch_internal_not_implemented(self):
        """Test DoctorBase._analyze_batch_internal raises NotImplementedError."""
        doctor = DoctorBase()
        with self.assertRaises(NotImplementedError):
            asyncio.run(doctor._analyze_batch_internal(["target"]))


if __name__ == "__main__":
    unittest.main()
