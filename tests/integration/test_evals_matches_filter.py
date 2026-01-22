import unittest

from agentic_patterns.core.evals.discovery import _matches_filter


class TestMatchesFilter(unittest.TestCase):
    """Tests for _matches_filter function."""

    def test_no_filter(self):
        self.assertTrue(_matches_filter("module", "file", "dataset", None))

    def test_matches_module(self):
        self.assertTrue(_matches_filter("my_module", "file", "dataset", "my_mod"))

    def test_matches_file(self):
        self.assertTrue(_matches_filter("module", "eval_sample", "dataset", "sample"))

    def test_matches_dataset(self):
        self.assertTrue(_matches_filter("module", "file", "dataset_one", "one"))

    def test_matches_full_name(self):
        self.assertTrue(_matches_filter("module", "file", "dataset_one", "module.dataset"))

    def test_no_match(self):
        self.assertFalse(_matches_filter("module", "file", "dataset", "xyz"))


if __name__ == "__main__":
    unittest.main()
