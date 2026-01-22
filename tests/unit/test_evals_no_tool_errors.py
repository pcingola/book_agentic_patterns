import unittest
from unittest.mock import MagicMock

from agentic_patterns.core.evals.evaluators import NoToolErrors


def make_context(output, span_tree=None):
    """Create a mock EvaluatorContext."""
    ctx = MagicMock()
    ctx.output = output
    ctx.span_tree = span_tree
    return ctx


def make_span(name: str, children: list | None = None, status: str = "ok"):
    """Create a mock span for testing."""
    span = MagicMock()
    span.name = name
    span.status = status
    span.children = children or []
    return span


class TestNoToolErrors(unittest.TestCase):
    """Tests for NoToolErrors evaluator."""

    def test_no_errors(self):
        evaluator = NoToolErrors()
        span = make_span("tool", status="ok")
        ctx = make_context("output", span_tree=span)
        result = evaluator.evaluate(ctx)
        self.assertTrue(result.value)
        self.assertIn("No tool errors", result.reason)

    def test_error_in_root(self):
        evaluator = NoToolErrors()
        span = make_span("failing_tool", status="error")
        ctx = make_context("output", span_tree=span)
        result = evaluator.evaluate(ctx)
        self.assertFalse(result.value)
        self.assertIn("failing_tool", result.reason)

    def test_error_in_child(self):
        evaluator = NoToolErrors()
        child = make_span("child_error", status="error")
        root = make_span("root", children=[child], status="ok")
        ctx = make_context("output", span_tree=root)
        result = evaluator.evaluate(ctx)
        self.assertFalse(result.value)

    def test_no_span_tree(self):
        evaluator = NoToolErrors()
        ctx = make_context("output", span_tree=None)
        result = evaluator.evaluate(ctx)
        self.assertTrue(result.value)


if __name__ == "__main__":
    unittest.main()
