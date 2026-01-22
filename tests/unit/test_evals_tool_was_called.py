import unittest
from unittest.mock import MagicMock

from agentic_patterns.core.evals.evaluators import ToolWasCalled


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


class TestToolWasCalled(unittest.TestCase):
    """Tests for ToolWasCalled evaluator."""

    def test_tool_found_in_root(self):
        evaluator = ToolWasCalled(tool_name="search_tool")
        span = make_span("search_tool")
        ctx = make_context("output", span_tree=span)
        result = evaluator.evaluate(ctx)
        self.assertTrue(result.value)
        self.assertIn("search_tool", result.reason)

    def test_tool_found_in_children(self):
        evaluator = ToolWasCalled(tool_name="nested_tool")
        child = make_span("nested_tool")
        root = make_span("root", children=[child])
        ctx = make_context("output", span_tree=root)
        result = evaluator.evaluate(ctx)
        self.assertTrue(result.value)

    def test_tool_not_found(self):
        evaluator = ToolWasCalled(tool_name="missing_tool")
        span = make_span("other_tool")
        ctx = make_context("output", span_tree=span)
        result = evaluator.evaluate(ctx)
        self.assertFalse(result.value)
        self.assertIn("was not called", result.reason)

    def test_no_span_tree(self):
        evaluator = ToolWasCalled(tool_name="any_tool")
        ctx = make_context("output", span_tree=None)
        result = evaluator.evaluate(ctx)
        self.assertFalse(result.value)
        self.assertIn("No span tree", result.reason)


if __name__ == "__main__":
    unittest.main()
