import unittest

from pydantic_evals.reporting import EvaluationReport, ReportCase

from agentic_patterns.core.evals.runner import average_assertions


def make_report_with_assertions(assertions_avg: float | None) -> EvaluationReport:
    """Create a real EvaluationReport with a specific assertions average."""
    if assertions_avg is None:
        return EvaluationReport(name="test", cases=[])

    # A single case with one assertion whose bool value yields the desired average
    passing = assertions_avg >= 1.0
    from pydantic_evals.evaluators import EvaluationResult, EvaluatorSpec
    source = EvaluatorSpec(name="test", arguments=None)
    case = ReportCase(
        name="case1",
        inputs="input",
        metadata=None,
        expected_output=None,
        output="output",
        metrics={},
        attributes={},
        scores={},
        labels={},
        assertions={"a1": EvaluationResult(name="a1", value=passing, reason="", source=source)},
        task_duration=0.0,
        total_duration=0.0,
    )
    return EvaluationReport(name="test", cases=[case])


class TestAverageAssertions(unittest.TestCase):
    """Tests for average_assertions scorer."""

    def test_passes_when_above_threshold(self):
        report = make_report_with_assertions(1.0)
        self.assertTrue(average_assertions(report, min_score=1.0))

    def test_passes_when_equal_threshold(self):
        report = make_report_with_assertions(1.0)
        self.assertTrue(average_assertions(report, min_score=1.0))

    def test_fails_when_below_threshold(self):
        report = make_report_with_assertions(0.0)
        self.assertFalse(average_assertions(report, min_score=0.8))

    def test_fails_when_no_assertions(self):
        report = make_report_with_assertions(None)
        self.assertFalse(average_assertions(report, min_score=1.0))

    def test_fails_when_no_cases(self):
        report = EvaluationReport(name="test", cases=[])
        self.assertFalse(average_assertions(report, min_score=1.0))


if __name__ == "__main__":
    unittest.main()
