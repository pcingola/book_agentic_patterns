import unittest

from pydantic import BaseModel
from pydantic_ai.messages import TextPart, ToolCallPart
from pydantic_ai.models import ModelRequestParameters

from agentic_patterns.testing.model_mock import (
    ModelMock,
    MockFinishReason,
    _convert_to_parts,
    final_result_tool,
)


class TestModelMock(unittest.IsolatedAsyncioTestCase):
    """Tests for agentic_patterns.testing.model_mock module."""

    def test_convert_to_parts_strings(self):
        """Test that strings are converted to TextParts."""
        result = _convert_to_parts(["hello", "world"])
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], TextPart)
        self.assertEqual(result[0].content, "hello")

    def test_convert_to_parts_mixed(self):
        """Test that mixed inputs (strings and ToolCallParts) are converted correctly."""
        tool_call = ToolCallPart(tool_name="test_tool", args={"x": 1})
        result = _convert_to_parts(["text", tool_call])
        self.assertIsInstance(result[0], TextPart)
        self.assertIsInstance(result[1], ToolCallPart)

    def test_final_result_tool_with_dict(self):
        """Test that final_result_tool creates ToolCallPart from dict."""
        result = final_result_tool({"key": "value"})
        self.assertIsInstance(result, ToolCallPart)
        self.assertEqual(result.tool_name, "final_result")
        self.assertEqual(result.args, {"key": "value"})

    def test_final_result_tool_with_pydantic_model(self):
        """Test that final_result_tool creates ToolCallPart from Pydantic model."""

        class MyModel(BaseModel):
            name: str
            value: int

        result = final_result_tool(MyModel(name="test", value=42))
        self.assertEqual(result.args, {"name": "test", "value": 42})

    def test_mock_finish_reason_with_response(self):
        """Test that MockFinishReason stores finish reason and converts response."""
        mfr = MockFinishReason(reason="content_filter", response="blocked text")
        self.assertEqual(mfr.reason, "content_filter")
        self.assertEqual(len(mfr.parts), 1)
        self.assertIsInstance(mfr.parts[0], TextPart)

    async def test_model_mock_returns_text_response(self):
        """Test that ModelMock returns text responses in order."""
        model = ModelMock(responses=["first", "second"])
        params = ModelRequestParameters(
            function_tools=[], allow_text_output=True, output_mode="text"
        )

        response1 = await model.request([], None, params)
        response2 = await model.request([], None, params)

        self.assertEqual(response1.parts[0].content, "first")
        self.assertEqual(response2.parts[0].content, "second")

    async def test_model_mock_returns_tool_call(self):
        """Test that ModelMock returns ToolCallPart responses."""
        tool_call = ToolCallPart(tool_name="search", args={"query": "test"})
        model = ModelMock(responses=[tool_call])
        params = ModelRequestParameters(
            function_tools=[], allow_text_output=True, output_mode="text"
        )

        response = await model.request([], None, params)

        self.assertIsInstance(response.parts[0], ToolCallPart)
        self.assertEqual(response.parts[0].tool_name, "search")

    async def test_model_mock_raises_exception(self):
        """Test that ModelMock raises exceptions when configured to do so."""
        model = ModelMock(responses=[ValueError("test error")])
        params = ModelRequestParameters(
            function_tools=[], allow_text_output=True, output_mode="text"
        )

        with self.assertRaises(ValueError) as ctx:
            await model.request([], None, params)
        self.assertEqual(str(ctx.exception), "test error")


if __name__ == "__main__":
    unittest.main()
