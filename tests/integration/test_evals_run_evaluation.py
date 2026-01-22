import asyncio
import unittest
from pathlib import Path
from unittest.mock import patch

from agentic_patterns.core.evals.discovery import discover_datasets
from agentic_patterns.core.evals.runner import PrintOptions, run_evaluation

TEST_DATA_DIR = Path(__file__).parent.parent / "data" / "evals"


class TestRunEvaluation(unittest.TestCase):
    """Tests for run_evaluation function."""

    def setUp(self):
        files = [TEST_DATA_DIR / "eval_sample.py"]
        self.datasets = discover_datasets(files, verbose=False)
        self.print_options = PrintOptions()

    def test_run_evaluation_success(self):
        ds = self.datasets[0]
        with patch("builtins.print"):
            name, success, report = asyncio.run(run_evaluation(ds, self.print_options, min_assertions=1.0))
        self.assertEqual(name, ds.name)
        self.assertTrue(success)
        self.assertIsNotNone(report)

    def test_run_evaluation_returns_name(self):
        ds = self.datasets[0]
        with patch("builtins.print"):
            name, _, _ = asyncio.run(run_evaluation(ds, self.print_options))
        self.assertIn("eval_sample", name)

    def test_run_evaluation_verbose(self):
        ds = self.datasets[0]
        with patch("builtins.print") as mock_print:
            asyncio.run(run_evaluation(ds, self.print_options, verbose=True))
            calls = [str(call) for call in mock_print.call_args_list]
            self.assertTrue(any("Running evaluation" in c for c in calls))


if __name__ == "__main__":
    unittest.main()
