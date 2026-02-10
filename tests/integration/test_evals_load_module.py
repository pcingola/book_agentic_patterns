import sys
import unittest
from pathlib import Path

from agentic_patterns.core.evals.discovery import load_module_from_file

TEST_DATA_DIR = Path(__file__).parent.parent / "data" / "evals"


class TestLoadModule(unittest.TestCase):
    """Tests for load_module_from_file function."""

    def test_load_module_success(self):
        module = load_module_from_file(TEST_DATA_DIR / "eval_sample.py")
        self.assertEqual(module.__name__, "eval_sample")
        self.assertTrue(hasattr(module, "target_sample"))
        self.assertTrue(hasattr(module, "dataset_one"))

    def test_load_module_adds_to_sys_modules(self):
        load_module_from_file(TEST_DATA_DIR / "eval_sample.py")
        self.assertIn("eval_sample", sys.modules)

    def test_load_module_invalid_file(self):
        with self.assertRaises(Exception):
            load_module_from_file(Path("/nonexistent/file.py"))


if __name__ == "__main__":
    unittest.main()
