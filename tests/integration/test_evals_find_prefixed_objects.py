import unittest
from pathlib import Path

from agentic_patterns.core.evals.discovery import (
    _find_datasets,
    _find_scorer_functions,
    _find_target_functions,
    load_module_from_file,
)

TEST_DATA_DIR = Path(__file__).parent.parent / "data" / "evals"


class TestFindPrefixedObjects(unittest.TestCase):
    """Tests for finding prefixed objects in modules."""

    def setUp(self):
        self.module = load_module_from_file(TEST_DATA_DIR / "eval_sample.py")

    def test_find_datasets(self):
        datasets = _find_datasets(self.module)
        names = [name for name, _ in datasets]
        self.assertIn("dataset_one", names)
        self.assertIn("dataset_two", names)

    def test_find_target_functions(self):
        targets = _find_target_functions(self.module)
        self.assertEqual(len(targets), 1)
        name, func = targets[0]
        self.assertEqual(name, "target_sample")
        self.assertTrue(callable(func))

    def test_find_scorer_functions(self):
        scorers = _find_scorer_functions(self.module)
        self.assertEqual(len(scorers), 1)
        name, func = scorers[0]
        self.assertEqual(name, "scorer_strict")


if __name__ == "__main__":
    unittest.main()
