import unittest
from dataclasses import dataclass, field
from typing import Any

from agentic_patterns.core.evals.evaluators import NoToolErrors


@dataclass
class FakeSpan:
    name: str = ""
    status: str = "ok"
    children: list = field(default_factory=list)


@dataclass
class FakeContext:
    output: Any = None
    span_tree: Any = None


class TestNoToolErrors(unittest.TestCase):
    """Tests for NoToolErrors evaluator."""

    def test_no_errors(self):
        evaluator = NoToolErrors()
        span = FakeSpan(name="tool", status="ok")
        ctx = FakeContext(output="output", span_tree=span)
        result = evaluator.evaluate(ctx)
        self.assertTrue(result.value)
        self.assertIn("No tool errors", result.reason)

    def test_error_in_root(self):
        evaluator = NoToolErrors()
        span = FakeSpan(name="failing_tool", status="error")
        ctx = FakeContext(output="output", span_tree=span)
        result = evaluator.evaluate(ctx)
        self.assertFalse(result.value)
        self.assertIn("failing_tool", result.reason)

    def test_error_in_child(self):
        evaluator = NoToolErrors()
        child = FakeSpan(name="child_error", status="error")
        root = FakeSpan(name="root", children=[child], status="ok")
        ctx = FakeContext(output="output", span_tree=root)
        result = evaluator.evaluate(ctx)
        self.assertFalse(result.value)

    def test_no_span_tree(self):
        evaluator = NoToolErrors()
        ctx = FakeContext(output="output", span_tree=None)
        result = evaluator.evaluate(ctx)
        self.assertTrue(result.value)


if __name__ == "__main__":
    unittest.main()
