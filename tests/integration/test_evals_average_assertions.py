import unittest
from unittest.mock import MagicMock

from agentic_patterns.core.evals.runner import average_assertions


def make_mock_report(assertions_avg: float | None):
    """Create a mock EvaluationReport."""
    report = MagicMock()
    averages = MagicMock()
    averages.assertions = assertions_avg
    report.averages.return_value = averages
    report.cases = []
    return report


class TestAverageAssertions(unittest.TestCase):
    """Tests for average_assertions scorer."""

    def test_passes_when_above_threshold(self):
        report = make_mock_report(1.0)
        self.assertTrue(average_assertions(report, min_score=1.0))

    def test_passes_when_equal_threshold(self):
        report = make_mock_report(0.8)
        self.assertTrue(average_assertions(report, min_score=0.8))

    def test_fails_when_below_threshold(self):
        report = make_mock_report(0.5)
        self.assertFalse(average_assertions(report, min_score=0.8))

    def test_fails_when_no_assertions(self):
        report = make_mock_report(None)
        self.assertFalse(average_assertions(report, min_score=1.0))

    def test_fails_when_no_averages(self):
        report = MagicMock()
        report.averages.return_value = None
        self.assertFalse(average_assertions(report, min_score=1.0))


if __name__ == "__main__":
    unittest.main()
