import unittest
from dataclasses import dataclass
from typing import Any

from agentic_patterns.core.evals.evaluators import OutputContainsJson


@dataclass
class FakeContext:
    output: Any = None
    span_tree: Any = None


class TestOutputContainsJson(unittest.TestCase):
    """Tests for OutputContainsJson evaluator."""

    def test_valid_json_object(self):
        evaluator = OutputContainsJson()
        ctx = FakeContext(output='{"key": "value"}')
        result = evaluator.evaluate(ctx)
        self.assertTrue(result.value)
        self.assertEqual(result.reason, "Valid JSON")

    def test_valid_json_array(self):
        evaluator = OutputContainsJson()
        ctx = FakeContext(output="[1, 2, 3]")
        result = evaluator.evaluate(ctx)
        self.assertTrue(result.value)

    def test_invalid_json(self):
        evaluator = OutputContainsJson()
        ctx = FakeContext(output="not json at all")
        result = evaluator.evaluate(ctx)
        self.assertFalse(result.value)
        self.assertIn("Invalid JSON", result.reason)

    def test_none_output(self):
        evaluator = OutputContainsJson()
        ctx = FakeContext(output=None)
        result = evaluator.evaluate(ctx)
        self.assertFalse(result.value)


if __name__ == "__main__":
    unittest.main()
