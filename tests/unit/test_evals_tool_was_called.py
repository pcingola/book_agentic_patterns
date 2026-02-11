import unittest
from dataclasses import dataclass, field
from typing import Any

from agentic_patterns.core.evals.evaluators import ToolWasCalled


@dataclass
class FakeSpan:
    name: str = ""
    status: str = "ok"
    children: list = field(default_factory=list)


@dataclass
class FakeContext:
    output: Any = None
    span_tree: Any = None


class TestToolWasCalled(unittest.TestCase):
    """Tests for ToolWasCalled evaluator."""

    def test_tool_found_in_root(self):
        evaluator = ToolWasCalled(tool_name="search_tool")
        span = FakeSpan(name="search_tool")
        ctx = FakeContext(output="output", span_tree=span)
        result = evaluator.evaluate(ctx)
        self.assertTrue(result.value)
        self.assertIn("search_tool", result.reason)

    def test_tool_found_in_children(self):
        evaluator = ToolWasCalled(tool_name="nested_tool")
        child = FakeSpan(name="nested_tool")
        root = FakeSpan(name="root", children=[child])
        ctx = FakeContext(output="output", span_tree=root)
        result = evaluator.evaluate(ctx)
        self.assertTrue(result.value)

    def test_tool_not_found(self):
        evaluator = ToolWasCalled(tool_name="missing_tool")
        span = FakeSpan(name="other_tool")
        ctx = FakeContext(output="output", span_tree=span)
        result = evaluator.evaluate(ctx)
        self.assertFalse(result.value)
        self.assertIn("was not called", result.reason)

    def test_no_span_tree(self):
        evaluator = ToolWasCalled(tool_name="any_tool")
        ctx = FakeContext(output="output", span_tree=None)
        result = evaluator.evaluate(ctx)
        self.assertFalse(result.value)
        self.assertIn("No span tree", result.reason)


if __name__ == "__main__":
    unittest.main()
