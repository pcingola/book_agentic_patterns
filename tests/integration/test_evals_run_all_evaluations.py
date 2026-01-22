import asyncio
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from agentic_patterns.core.evals.discovery import discover_datasets
from agentic_patterns.core.evals.runner import PrintOptions, run_all_evaluations

TEST_DATA_DIR = Path(__file__).parent.parent / "data" / "evals"


def make_mock_report(assertions_avg: float | None):
    """Create a mock EvaluationReport."""
    report = MagicMock()
    averages = MagicMock()
    averages.assertions = assertions_avg
    report.averages.return_value = averages
    report.cases = []
    return report


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
        with patch("builtins.print"):
            with patch("agentic_patterns.core.evals.runner.run_evaluation") as mock_run:
                mock_run.return_value = ("test", True, make_mock_report(1.0))
                asyncio.run(run_all_evaluations(self.datasets, self.print_options))
                self.assertEqual(mock_run.call_count, len(self.datasets))

    def test_run_all_verbose_prints_summary(self):
        with patch("builtins.print") as mock_print:
            asyncio.run(run_all_evaluations(self.datasets, self.print_options, verbose=True))
            calls = " ".join(str(call) for call in mock_print.call_args_list)
            self.assertIn("EVALUATION SUMMARY", calls)


if __name__ == "__main__":
    unittest.main()
