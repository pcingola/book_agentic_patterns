import unittest
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from agentic_patterns.core.evals.evaluators import OutputMatchesSchema


@dataclass
class FakeContext:
    output: Any = None
    span_tree: Any = None


class SampleSchema(BaseModel):
    name: str
    value: int


class TestOutputMatchesSchema(unittest.TestCase):
    """Tests for OutputMatchesSchema evaluator."""

    def test_valid_pydantic_schema(self):
        evaluator = OutputMatchesSchema(schema=SampleSchema)
        ctx = FakeContext(output='{"name": "test", "value": 42}')
        result = evaluator.evaluate(ctx)
        self.assertTrue(result.value)

    def test_invalid_pydantic_schema(self):
        evaluator = OutputMatchesSchema(schema=SampleSchema)
        ctx = FakeContext(output='{"name": "test"}')
        result = evaluator.evaluate(ctx)
        self.assertFalse(result.value)
        self.assertIn("validation failed", result.reason)

    def test_dict_schema_valid(self):
        evaluator = OutputMatchesSchema(schema={"key1": str, "key2": int})
        ctx = FakeContext(output={"key1": "value", "key2": 123})
        result = evaluator.evaluate(ctx)
        self.assertTrue(result.value)

    def test_dict_schema_missing_keys(self):
        evaluator = OutputMatchesSchema(schema={"key1": str, "key2": int})
        ctx = FakeContext(output={"key1": "value"})
        result = evaluator.evaluate(ctx)
        self.assertFalse(result.value)
        self.assertIn("Missing keys", result.reason)

    def test_none_output(self):
        evaluator = OutputMatchesSchema(schema=SampleSchema)
        ctx = FakeContext(output=None)
        result = evaluator.evaluate(ctx)
        self.assertFalse(result.value)
        self.assertIn("None", result.reason)

    def test_invalid_json_string(self):
        evaluator = OutputMatchesSchema(schema=SampleSchema)
        ctx = FakeContext(output="not json")
        result = evaluator.evaluate(ctx)
        self.assertFalse(result.value)
        self.assertIn("not valid JSON", result.reason)


if __name__ == "__main__":
    unittest.main()
