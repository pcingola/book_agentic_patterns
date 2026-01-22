import unittest
from unittest.mock import MagicMock

from pydantic import BaseModel

from agentic_patterns.core.evals.evaluators import OutputMatchesSchema


def make_context(output, span_tree=None):
    """Create a mock EvaluatorContext."""
    ctx = MagicMock()
    ctx.output = output
    ctx.span_tree = span_tree
    return ctx


class SampleSchema(BaseModel):
    name: str
    value: int


class TestOutputMatchesSchema(unittest.TestCase):
    """Tests for OutputMatchesSchema evaluator."""

    def test_valid_pydantic_schema(self):
        evaluator = OutputMatchesSchema(schema=SampleSchema)
        ctx = make_context('{"name": "test", "value": 42}')
        result = evaluator.evaluate(ctx)
        self.assertTrue(result.value)

    def test_invalid_pydantic_schema(self):
        evaluator = OutputMatchesSchema(schema=SampleSchema)
        ctx = make_context('{"name": "test"}')
        result = evaluator.evaluate(ctx)
        self.assertFalse(result.value)
        self.assertIn("validation failed", result.reason)

    def test_dict_schema_valid(self):
        evaluator = OutputMatchesSchema(schema={"key1": str, "key2": int})
        ctx = make_context({"key1": "value", "key2": 123})
        result = evaluator.evaluate(ctx)
        self.assertTrue(result.value)

    def test_dict_schema_missing_keys(self):
        evaluator = OutputMatchesSchema(schema={"key1": str, "key2": int})
        ctx = make_context({"key1": "value"})
        result = evaluator.evaluate(ctx)
        self.assertFalse(result.value)
        self.assertIn("Missing keys", result.reason)

    def test_none_output(self):
        evaluator = OutputMatchesSchema(schema=SampleSchema)
        ctx = make_context(None)
        result = evaluator.evaluate(ctx)
        self.assertFalse(result.value)
        self.assertIn("None", result.reason)

    def test_invalid_json_string(self):
        evaluator = OutputMatchesSchema(schema=SampleSchema)
        ctx = make_context("not json")
        result = evaluator.evaluate(ctx)
        self.assertFalse(result.value)
        self.assertIn("not valid JSON", result.reason)


if __name__ == "__main__":
    unittest.main()
