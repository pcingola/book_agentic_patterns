import unittest
from pathlib import Path
from unittest.mock import patch

from agentic_patterns.core.evals.discovery import (
    DiscoveredDataset,
    discover_datasets,
    find_eval_files,
)

TEST_DATA_DIR = Path(__file__).parent.parent / "data" / "evals"


class TestDiscoverDatasets(unittest.TestCase):
    """Tests for discover_datasets function."""

    def test_discover_all(self):
        files = find_eval_files(TEST_DATA_DIR)
        sample_files = [f for f in files if f.name == "eval_sample.py"]
        datasets = discover_datasets(sample_files, verbose=False)
        self.assertEqual(len(datasets), 2)

    def test_discover_with_filter(self):
        files = [TEST_DATA_DIR / "eval_sample.py"]
        datasets = discover_datasets(files, name_filter="one", verbose=False)
        self.assertEqual(len(datasets), 1)
        self.assertIn("dataset_one", datasets[0].name)

    def test_discover_returns_discovered_dataset(self):
        files = [TEST_DATA_DIR / "eval_sample.py"]
        datasets = discover_datasets(files, verbose=False)
        self.assertIsInstance(datasets[0], DiscoveredDataset)
        self.assertIsNotNone(datasets[0].dataset)
        self.assertIsNotNone(datasets[0].target_func)
        self.assertEqual(len(datasets[0].scorers), 1)

    def test_discover_skips_no_target(self):
        """Files without exactly one target function are skipped."""
        files = [TEST_DATA_DIR / "eval_no_target.py"]
        with self.assertRaises(SystemExit):
            discover_datasets(files, verbose=False)

    def test_discover_verbose_output(self):
        files = [TEST_DATA_DIR / "eval_sample.py"]
        with patch("builtins.print"):
            datasets = discover_datasets(files, verbose=True)
            self.assertEqual(len(datasets), 2)


if __name__ == "__main__":
    unittest.main()
