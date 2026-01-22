import unittest
from pathlib import Path

from agentic_patterns.core.evals.discovery import find_eval_files

TEST_DATA_DIR = Path(__file__).parent.parent / "data" / "evals"


class TestFindEvalFiles(unittest.TestCase):
    """Tests for find_eval_files function."""

    def test_find_eval_files_success(self):
        files = find_eval_files(TEST_DATA_DIR)
        self.assertGreaterEqual(len(files), 2)
        names = [f.name for f in files]
        self.assertIn("eval_sample.py", names)
        self.assertIn("eval_no_target.py", names)

    def test_find_eval_files_sorted(self):
        files = find_eval_files(TEST_DATA_DIR)
        names = [f.name for f in files]
        self.assertEqual(names, sorted(names))

    def test_find_eval_files_missing_dir(self):
        with self.assertRaises(SystemExit):
            find_eval_files(Path("/nonexistent/directory"))


if __name__ == "__main__":
    unittest.main()
