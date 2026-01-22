import unittest
from unittest.mock import MagicMock

from agentic_patterns.core.evals.evaluators import OutputContainsJson


def make_context(output, span_tree=None):
    """Create a mock EvaluatorContext."""
    ctx = MagicMock()
    ctx.output = output
    ctx.span_tree = span_tree
    return ctx


class TestOutputContainsJson(unittest.TestCase):
    """Tests for OutputContainsJson evaluator."""

    def test_valid_json_object(self):
        evaluator = OutputContainsJson()
        ctx = make_context('{"key": "value"}')
        result = evaluator.evaluate(ctx)
        self.assertTrue(result.value)
        self.assertEqual(result.reason, "Valid JSON")

    def test_valid_json_array(self):
        evaluator = OutputContainsJson()
        ctx = make_context('[1, 2, 3]')
        result = evaluator.evaluate(ctx)
        self.assertTrue(result.value)

    def test_invalid_json(self):
        evaluator = OutputContainsJson()
        ctx = make_context("not json at all")
        result = evaluator.evaluate(ctx)
        self.assertFalse(result.value)
        self.assertIn("Invalid JSON", result.reason)

    def test_none_output(self):
        evaluator = OutputContainsJson()
        ctx = make_context(None)
        result = evaluator.evaluate(ctx)
        self.assertFalse(result.value)


if __name__ == "__main__":
    unittest.main()
