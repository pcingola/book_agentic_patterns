import asyncio
import unittest
from pathlib import Path
from unittest.mock import patch

from agentic_patterns.core.evals.discovery import discover_datasets
from agentic_patterns.core.evals.runner import PrintOptions, run_all_evaluations

TEST_DATA_DIR = Path(__file__).parent.parent / "data" / "evals"


class TestRunAllEvaluations(unittest.TestCase):
    """Tests for run_all_evaluations function."""

    def setUp(self):
        files = [TEST_DATA_DIR / "eval_sample.py"]
        self.datasets = discover_datasets(files, verbose=False)
        self.print_options = PrintOptions()

    def test_run_all_returns_true_on_success(self):
        with patch("builtins.print"):
            result = asyncio.run(run_all_evaluations(self.datasets, self.print_options, min_assertions=1.0))
        self.assertTrue(result)

    def test_run_all_runs_all_datasets(self):
        """All discovered datasets are executed by run_all_evaluations."""
        with patch("builtins.print"):
            result = asyncio.run(run_all_evaluations(self.datasets, self.print_options))
        self.assertTrue(result)
        self.assertGreater(len(self.datasets), 0)

    def test_run_all_verbose_prints_summary(self):
        with patch("builtins.print") as mock_print:
            asyncio.run(run_all_evaluations(self.datasets, self.print_options, verbose=True))
            calls = " ".join(str(call) for call in mock_print.call_args_list)
            self.assertIn("EVALUATION SUMMARY", calls)


if __name__ == "__main__":
    unittest.main()
