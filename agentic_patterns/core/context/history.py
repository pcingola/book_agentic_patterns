"""History compaction service for managing conversation context window.

Provides functionality to automatically detect when the conversation history approaches
the context window limit and compact/summarize older messages to allow the conversation
to continue.
"""

import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import asdict
from typing import Sequence

import tiktoken
from pydantic import BaseModel, model_validator
from pydantic_ai import Agent
from pydantic_ai.messages import (
    BuiltinToolCallPart,
    BuiltinToolReturnPart,
    FilePart,
    ModelMessage,
    ModelRequest,
    RetryPromptPart,
    SystemPromptPart,
    TextPart,
    ThinkingPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models import Model
from pydantic_ai.tools import RunContext

from agentic_patterns.core.context.config import load_context_config

logger = logging.getLogger(__name__)

TOOL_RESULT_PREVIEW_LENGTH = 200

SUMMARIZATION_REQUEST_PROMPT = """Summarize the following conversation concisely, preserving key information,
decisions made, and important context that would be needed to continue the conversation. Focus on facts
and outcomes rather than the back-and-forth dialogue. Avoid adding a markdown header.

Conversation:
{conversation}

Summary:"""

SUMMARY_WRAPPED = """This session is being continued from a previous conversation that ran out of context. \
The conversation is summarized below:

{summary}

Please continue the conversation from where we left it off without asking the user any further questions. \
Continue with the last task that you were asked to work on, if any, otherwise just wait for the user's next input.
"""


class CompactionConfig(BaseModel):
    """Configuration for history compaction."""
    max_tokens: int = 120_000
    target_tokens: int = 40_000

    @model_validator(mode="after")
    def validate_tokens(self) -> "CompactionConfig":
        if self.target_tokens >= self.max_tokens:
            raise ValueError("target_tokens must be less than max_tokens")
        return self


class CompactionResult(BaseModel):
    """Result of a history compaction operation."""
    original_messages: int
    compacted_messages: int
    original_tokens: int
    compacted_tokens: int
    summary: str


class HistoryCompactor:
    """Manages conversation history compaction for pydantic-ai agents.

    Provides automatic detection of context window limits and compaction
    of older messages through summarization using the same model as the agent.
    """

    _tokenizer = tiktoken.get_encoding("cl100k_base")

    def __init__(
        self,
        config: CompactionConfig | None = None,
        model: Model | None = None,
        on_compaction: Callable[[CompactionResult], Awaitable[None]] | None = None,
    ):
        """Initialize the HistoryCompactor.

        Args:
            config: Compaction configuration. If None, loads from config.yaml.
            model: Model to use for summarization.
            on_compaction: Optional async callback called when compaction occurs.
        """
        if config is None:
            ctx_config = load_context_config()
            config = CompactionConfig(
                max_tokens=ctx_config.history_max_tokens,
                target_tokens=ctx_config.history_target_tokens,
            )

        self.config = config
        self.model = model
        self.on_compaction = on_compaction
        self._summarizer_max_tokens = load_context_config().summarizer_max_tokens

        logger.info("Created compactor with config: %s", self.config)

    def _count_text_tokens(self, text: str) -> int:
        return len(self._tokenizer.encode(text))

    def _serialize_part_for_tokens(self, part) -> str:
        """Serialize a message part for accurate token counting."""
        try:
            return json.dumps(asdict(part), default=str)
        except (TypeError, ValueError):
            return str(part)

    def _serialize_message_for_tokens(self, message: ModelMessage) -> str:
        parts_json = [self._serialize_part_for_tokens(part) for part in message.parts]
        return " ".join(parts_json)

    def _extract_text_for_summary(self, part) -> str:
        """Extract readable text from a message part for summarization."""
        result = None

        if isinstance(part, (TextPart, UserPromptPart, SystemPromptPart, ThinkingPart)):
            content = part.content
            if isinstance(content, str):
                result = content
            elif isinstance(content, Sequence):
                result = " ".join(str(item) for item in content if isinstance(item, str))
        elif isinstance(part, (ToolCallPart, BuiltinToolCallPart)):
            result = f"[Tool call: {part.tool_name}({part.args})]"
        elif isinstance(part, (ToolReturnPart, BuiltinToolReturnPart)):
            content = part.content
            content_str = content if isinstance(content, str) else str(content)
            if len(content_str) > TOOL_RESULT_PREVIEW_LENGTH:
                result = f"[Tool result ({part.tool_name}): {content_str[:TOOL_RESULT_PREVIEW_LENGTH]}...]"
            else:
                result = f"[Tool result ({part.tool_name}): {content_str}]"
        elif isinstance(part, RetryPromptPart):
            content = part.content
            content_str = content if isinstance(content, str) else str(content)
            result = f"[Retry ({part.tool_name}): {content_str}]"
        elif isinstance(part, FilePart):
            file_id = part.id or "unknown"
            file_size = len(part.content) if part.content else 0
            result = f"[File ({file_id}): {file_size} bytes]"

        return result if result is not None else str(part)

    def _extract_message_for_summary(self, message: ModelMessage) -> str:
        texts = [self._extract_text_for_summary(part) for part in message.parts]
        return " ".join(texts)

    def count_tokens(self, messages: list[ModelMessage]) -> int:
        """Count the tokens in a list of messages using tiktoken."""
        if not messages:
            return 0

        total_tokens = 0
        for message in messages:
            text = self._serialize_message_for_tokens(message)
            total_tokens += self._count_text_tokens(text)

        return total_tokens

    def needs_compaction(self, messages: list[ModelMessage], current_tokens: int | None = None) -> bool:
        """Check if the message history needs compaction."""
        token_count = current_tokens if current_tokens is not None else self.count_tokens(messages)
        return token_count > self.config.max_tokens

    async def compact(self, messages: list[ModelMessage]) -> list[ModelMessage]:
        """Compact the message history by summarizing all messages."""
        token_count = self.count_tokens(messages)
        total_messages = len(messages)
        logger.info(
            "Checking: %d messages, %d tokens (max=%d, target=%d)",
            total_messages, token_count, self.config.max_tokens, self.config.target_tokens
        )

        if not self.needs_compaction(messages, current_tokens=token_count):
            logger.debug("No compaction needed")
            return messages

        logger.info("Starting compaction: %d messages, %d tokens", total_messages, token_count)

        summary = await self._summarize_messages(messages)
        summary_content = SUMMARY_WRAPPED.format(summary=summary)
        messages_after_summary = [ModelRequest(parts=[UserPromptPart(content=summary_content)])]
        token_count_after_summary = self.count_tokens(messages_after_summary)
        logger.info(
            "Compaction complete: %d -> %d messages, %d -> %d tokens",
            total_messages, len(messages_after_summary), token_count, token_count_after_summary
        )

        if self.on_compaction:
            result = CompactionResult(
                original_messages=total_messages,
                compacted_messages=len(messages_after_summary),
                original_tokens=token_count,
                compacted_tokens=token_count_after_summary,
                summary=summary_content,
            )
            await self.on_compaction(result)

        return messages_after_summary

    async def _summarize_messages(self, messages: list[ModelMessage]) -> str:
        """Summarize a list of messages into a text summary."""
        text_parts = []
        for msg in messages:
            role = "User" if isinstance(msg, ModelRequest) else "Assistant"
            content = self._extract_message_for_summary(msg)
            text_parts.append(f"{role}: {content}")

        conversation_text = "\n".join(text_parts)
        summary = await self._call_summarizer(conversation_text)
        return summary

    def _truncate_for_fallback(self, text: str, max_tokens: int) -> str:
        """Create a truncated summary when model summarization isn't available."""
        tokens = self._tokenizer.encode(text)
        if len(tokens) > max_tokens:
            head_tokens = max_tokens // 4
            tail_tokens = max_tokens - head_tokens

            head = self._tokenizer.decode(tokens[:head_tokens])
            tail = self._tokenizer.decode(tokens[-tail_tokens:])
            removed_count = len(tokens) - max_tokens

            truncated = f"{head}\n\n[... {removed_count} tokens removed ...]\n\n{tail}"
            return f"[Previous conversation (truncated)]:\n{truncated}"

        return f"[Previous conversation]:\n{text}"

    async def _call_summarizer(self, text: str) -> str:
        """Call the model to generate a summary of the conversation."""
        if self.model is None:
            logger.warning("No model provided for summarization, using truncation fallback")
            return self._truncate_for_fallback(text, self.config.target_tokens // 2)

        text_tokens = self._count_text_tokens(text)
        if text_tokens > self._summarizer_max_tokens:
            logger.warning(
                "Conversation too long for summarization (%d tokens), truncating to %d tokens",
                text_tokens, self._summarizer_max_tokens
            )
            text = self._truncate_for_fallback(text, self._summarizer_max_tokens)

        summarizer = Agent(model=self.model, output_type=str)
        prompt = SUMMARIZATION_REQUEST_PROMPT.format(conversation=text)

        try:
            result = await summarizer.run(prompt)
            return result.output
        except (ValueError, RuntimeError, TimeoutError) as e:
            logger.warning("Summarization failed (%s), using truncation fallback", str(e))
            return self._truncate_for_fallback(text, self.config.target_tokens // 2)

    def create_history_processor(self) -> Callable[[list[ModelMessage]], Awaitable[list[ModelMessage]]]:
        """Create a pydantic-ai compatible history processor."""
        async def processor(messages: list[ModelMessage]) -> list[ModelMessage]:
            return await self.compact(messages)

        return processor

    def create_context_aware_processor(self) -> Callable[[RunContext, list[ModelMessage]], Awaitable[list[ModelMessage]]]:
        """Create a context-aware history processor that uses RunContext."""
        logger.info("Creating context-aware processor (max=%s, target=%s)", self.config.max_tokens, self.config.target_tokens)

        async def processor(_ctx: RunContext, messages: list[ModelMessage]) -> list[ModelMessage]:
            return await self.compact(messages)

        return processor
