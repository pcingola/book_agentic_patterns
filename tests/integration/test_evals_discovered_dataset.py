import unittest
from pathlib import Path

from agentic_patterns.core.evals.discovery import discover_datasets

TEST_DATA_DIR = Path(__file__).parent.parent / "data" / "evals"


class TestDiscoveredDataset(unittest.TestCase):
    """Tests for DiscoveredDataset dataclass."""

    def test_discovered_dataset_fields(self):
        files = [TEST_DATA_DIR / "eval_sample.py"]
        datasets = discover_datasets(files, verbose=False)
        ds = datasets[0]
        self.assertTrue(hasattr(ds, "dataset"))
        self.assertTrue(hasattr(ds, "target_func"))
        self.assertTrue(hasattr(ds, "scorers"))
        self.assertTrue(hasattr(ds, "name"))
        self.assertTrue(hasattr(ds, "file_path"))

    def test_discovered_dataset_name_format(self):
        files = [TEST_DATA_DIR / "eval_sample.py"]
        datasets = discover_datasets(files, verbose=False)
        for ds in datasets:
            self.assertIn("eval_sample.", ds.name)


if __name__ == "__main__":
    unittest.main()
