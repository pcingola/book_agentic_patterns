"""Test model implementation for AI agent testing with predefined responses."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from types import AsyncGeneratorType

from pydantic import BaseModel
from pydantic_ai.messages import FinishReason, ModelMessage, ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models import Model, ModelRequestParameters, StreamedResponse
from pydantic_ai.models.function import _estimate_usage
from pydantic_ai.models.test import TestStreamedResponse
from pydantic_ai.settings import ModelSettings

FINAL_RESULT_TOOL_NAME = "final_result"

ResponseItem = str | TextPart | ToolCallPart


async def _async_iter(items):
    """Asynchronously iterate over items."""
    for item in items:
        yield item


def _convert_to_parts(items: list[ResponseItem]) -> list[TextPart | ToolCallPart]:
    """Convert a list of strings, TextParts, or ToolCallParts to a list of Parts."""
    parts: list[TextPart | ToolCallPart] = []
    for item in items:
        match item:
            case str():
                parts.append(TextPart(item))
            case TextPart() | ToolCallPart():
                parts.append(item)
            case _:
                raise ValueError(f"Invalid item type in list: {type(item)}, item: {item}")
    return parts


def final_result_tool(result: BaseModel | dict | list) -> ToolCallPart:
    """Create a ToolCallPart for the final result.

    For BaseModel output types, pass the model directly.
    For non-model output types (e.g. list[str]), the value is automatically wrapped
    with {'response': value} to match PydanticAI's internal format.
    """
    if isinstance(result, BaseModel):
        args = result.model_dump()
    elif isinstance(result, dict):
        args = result
    else:
        args = {"response": result}
    return ToolCallPart(tool_name=FINAL_RESULT_TOOL_NAME, args=args)


class MockFinishReason:
    """Wraps a response item for ModelMock to emulate a custom finish reason from the model."""

    def __init__(self, reason: FinishReason, response: ResponseItem | list[ResponseItem] | None = None):
        self.reason: FinishReason = reason
        match response:
            case list():
                self.parts = _convert_to_parts(response)
            case str() | TextPart() | ToolCallPart():
                self.parts = _convert_to_parts([response])
            case _:
                self.parts = []


class ModelMock(Model):
    """
    Test model that returns a specified list of answers, including messages or tool calls.
    Used for testing agent and model interaction without calling a real LLM.

    Args:
        responses: List of response items returned in order. Each item can be:
            - str: A simple text response
            - TextPart: A text part
            - ToolCallPart: A tool call
            - list[str | TextPart | ToolCallPart]: Multiple parts in a single response
            - MockFinishReason: Custom finish reason with optional response parts
            - Exception: Will be raised when encountered
            - Callable: Called with (model, messages) to generate response dynamically
        sleep_time: Optional delay between responses for simulating latency

    Note: The agent continues invoking request() until it returns text (not a ToolCallPart).

    Example - Unstructured output:
        model = ModelMock(responses=[
            ToolCallPart(tool_name='search', args={'query': 'test'}),
            "The answer is 42.",
        ])

    Example - Structured output:
        class MyResult(BaseModel):
            text: str

        model = ModelMock(responses=[
            ToolCallPart(tool_name='analyze', args={'data': 'xyz'}),
            final_result_tool(MyResult(text='Analysis complete')),
        ])

    Example - Multiple parts in single response:
        model = ModelMock(responses=[
            ["Thinking...", ToolCallPart(tool_name='calc', args={'x': 1})],
            "Done.",
        ])

    Example - Custom finish reason:
        model = ModelMock(responses=[
            MockFinishReason(reason='content_filter'),
        ])
    """

    def __init__(
        self,
        responses: list[ResponseItem | list[ResponseItem] | MockFinishReason] | AsyncGeneratorType,
        sleep_time: float | None = None,
    ):
        self.response_iter = responses(self) if callable(responses) else _async_iter(responses)
        self.messages: list[ModelMessage] = None
        self.sleep_time = sleep_time
        self.last_model_request_parameters: ModelRequestParameters | None = None

    @property
    def last_message(self) -> ModelResponse | None:
        """Return the last response."""
        return self.messages[-1] if self.messages else None

    @property
    def last_message_part(self) -> TextPart | ToolCallPart | None:
        """Return the last part of the response."""
        return self.last_message.parts[-1] if self.last_message and self.last_message.parts else None

    @property
    def model_name(self) -> str:
        return self.__class__.__name__.lower()

    @property
    def system(self) -> str:
        return "test_system"

    async def request(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> ModelResponse:
        self.last_model_request_parameters = model_request_parameters
        model_response = await self._request(messages, model_settings, model_request_parameters)
        model_response.usage = _estimate_usage([*messages, model_response])
        return model_response

    @asynccontextmanager
    async def request_stream(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
        *args,  # noqa: ARG002
        **kwargs,  # noqa: ARG002
    ) -> AsyncIterator[StreamedResponse]:
        model_response = await self._request(messages, model_settings, model_request_parameters)
        response = TestStreamedResponse(
            _model_name=self.model_name,
            _structured_response=model_response,
            _messages=messages,
            model_request_parameters=model_request_parameters,
            _provider_name="",
        )
        response.finish_reason = model_response.finish_reason
        yield response

    async def _request(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,  # noqa: ARG002
        model_request_parameters: ModelRequestParameters,  # noqa: ARG002
    ) -> ModelResponse:
        self.messages = messages
        res = await anext(self.response_iter, None)
        assert res, "No more responses available."
        if callable(res):
            res = res(self, messages)

        finish_reason: FinishReason | None = None

        match res:
            case Exception():
                raise res
            case list():
                parts = _convert_to_parts(res)
            case str() | TextPart() | ToolCallPart():
                parts = _convert_to_parts([res])
            case MockFinishReason():
                parts = res.parts
                finish_reason = res.reason
            case _:
                raise ValueError(f"Invalid response type: {type(res)}, response: {res}")

        if self.sleep_time:
            await asyncio.sleep(self.sleep_time)
        return ModelResponse(parts=parts, model_name=self.model_name, finish_reason=finish_reason)
