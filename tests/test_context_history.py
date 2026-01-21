"""Tests for agentic_patterns.core.context.history module - history compaction with tool call/return pairing."""

import logging
import unittest

from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)

from agentic_patterns.core.context.history import CompactionConfig, HistoryCompactor
from agentic_patterns.testing.model_mock import ModelMock


class TestHistoryCompactor(unittest.IsolatedAsyncioTestCase):
    """Tests for HistoryCompactor class with focus on tool call/return pairing."""

    def setUp(self):
        self.config = CompactionConfig(max_tokens=100, target_tokens=50)
        self.model = ModelMock(responses=["Summary."])

    def _make_user_message(self, text: str) -> ModelRequest:
        return ModelRequest(parts=[UserPromptPart(content=text)])

    def _make_system_message(self, text: str) -> ModelRequest:
        return ModelRequest(parts=[SystemPromptPart(content=text)])

    def _make_assistant_message(self, text: str) -> ModelResponse:
        return ModelResponse(parts=[TextPart(content=text)])

    def _make_tool_call_message(self, tool_name: str = "test_tool", args: dict | None = None) -> ModelResponse:
        return ModelResponse(parts=[ToolCallPart(tool_name=tool_name, args=args or {})])

    def _make_tool_return_message(self, tool_name: str = "test_tool", content: str = "result") -> ModelRequest:
        return ModelRequest(parts=[ToolReturnPart(tool_name=tool_name, content=content)])

    def test_has_tool_return_part_true(self):
        """Test _has_tool_return_part returns True when message contains ToolReturnPart."""
        compactor = HistoryCompactor(config=self.config, model=self.model)
        msg = self._make_tool_return_message()
        self.assertTrue(compactor._has_tool_return_part(msg))

    def test_has_tool_return_part_false(self):
        """Test _has_tool_return_part returns False for regular messages."""
        compactor = HistoryCompactor(config=self.config, model=self.model)
        msg = self._make_user_message("hello")
        self.assertFalse(compactor._has_tool_return_part(msg))

    def test_has_tool_call_part_true(self):
        """Test _has_tool_call_part returns True when message contains ToolCallPart."""
        compactor = HistoryCompactor(config=self.config, model=self.model)
        msg = self._make_tool_call_message()
        self.assertTrue(compactor._has_tool_call_part(msg))

    def test_has_tool_call_part_false(self):
        """Test _has_tool_call_part returns False for regular messages."""
        compactor = HistoryCompactor(config=self.config, model=self.model)
        msg = self._make_assistant_message("hello")
        self.assertFalse(compactor._has_tool_call_part(msg))

    def test_find_boundary_single_message_returns_negative(self):
        """Test that single message returns -1 (cannot compact)."""
        compactor = HistoryCompactor(config=self.config, model=self.model)
        messages = [self._make_user_message("hello")]
        boundary = compactor._find_safe_compaction_boundary(messages)
        self.assertEqual(boundary, -1)

    def test_find_boundary_normal_messages(self):
        """Test boundary finding with normal user/assistant messages."""
        compactor = HistoryCompactor(config=self.config, model=self.model)
        messages = [
            self._make_user_message("hello"),
            self._make_assistant_message("hi"),
            self._make_user_message("how are you"),
        ]
        boundary = compactor._find_safe_compaction_boundary(messages)
        self.assertEqual(boundary, 2)

    def test_find_boundary_tool_return_keeps_tool_call(self):
        """Test that when last message is tool return, preceding tool call is also kept."""
        compactor = HistoryCompactor(config=self.config, model=self.model)
        messages = [
            self._make_user_message("search for something"),
            self._make_tool_call_message("search", {"query": "test"}),
            self._make_tool_return_message("search", "found results"),
        ]
        boundary = compactor._find_safe_compaction_boundary(messages)
        self.assertEqual(boundary, 1)

    def test_find_boundary_only_tool_pair_returns_negative(self):
        """Test that when only tool call/return pair exists, compaction is skipped."""
        compactor = HistoryCompactor(config=self.config, model=self.model)
        messages = [
            self._make_tool_call_message("search", {"query": "test"}),
            self._make_tool_return_message("search", "found results"),
        ]
        boundary = compactor._find_safe_compaction_boundary(messages)
        self.assertEqual(boundary, -1)

    def test_find_boundary_tool_return_without_call_returns_negative(self):
        """Test that orphaned tool return skips compaction."""
        compactor = HistoryCompactor(config=self.config, model=self.model)
        messages = [
            self._make_user_message("hello"),
            self._make_tool_return_message("search", "found results"),
        ]
        boundary = compactor._find_safe_compaction_boundary(messages)
        self.assertEqual(boundary, -1)

    def test_count_tokens_empty(self):
        """Test token counting for empty message list."""
        compactor = HistoryCompactor(config=self.config, model=self.model)
        self.assertEqual(compactor.count_tokens([]), 0)

    def test_count_tokens_messages(self):
        """Test token counting returns positive value for messages."""
        compactor = HistoryCompactor(config=self.config, model=self.model)
        messages = [self._make_user_message("hello world")]
        tokens = compactor.count_tokens(messages)
        self.assertGreater(tokens, 0)

    def test_needs_compaction_false_under_limit(self):
        """Test needs_compaction returns False when under token limit."""
        config = CompactionConfig(max_tokens=10000, target_tokens=5000)
        compactor = HistoryCompactor(config=config, model=self.model)
        messages = [self._make_user_message("hello")]
        self.assertFalse(compactor.needs_compaction(messages))

    def test_needs_compaction_true_over_limit(self):
        """Test needs_compaction returns True when over token limit."""
        config = CompactionConfig(max_tokens=1, target_tokens=0)
        compactor = HistoryCompactor(config=config, model=self.model)
        messages = [self._make_user_message("hello")]
        self.assertTrue(compactor.needs_compaction(messages))

    async def test_compact_no_compaction_needed(self):
        """Test compact() returns original messages when under limit."""
        config = CompactionConfig(max_tokens=10000, target_tokens=5000)
        compactor = HistoryCompactor(config=config, model=self.model)
        messages = [self._make_user_message("hello")]
        result = await compactor.compact(messages)
        self.assertEqual(result, messages)

    def test_truncate_for_fallback(self):
        """Test _truncate_for_fallback produces truncated summary."""
        config = CompactionConfig(max_tokens=10000, target_tokens=5000)
        model = ModelMock(responses=["Summary"])
        compactor = HistoryCompactor(config=config, model=model)
        long_text = "word " * 1000
        result = compactor._truncate_for_fallback(long_text, max_tokens=100)
        self.assertIn("Previous conversation", result)
        self.assertIn("tokens removed", result)

    async def test_compact_with_summarization(self):
        """Test compact() produces summary message."""
        config = CompactionConfig(max_tokens=10, target_tokens=5)
        model = ModelMock(responses=["Summary of the conversation."])
        compactor = HistoryCompactor(config=config, model=model)
        messages = [
            self._make_user_message("first message with lots of text to exceed token limit"),
            self._make_assistant_message("response with lots of text to exceed token limit"),
            self._make_user_message("final message"),
        ]
        result = await compactor.compact(messages)
        self.assertEqual(len(result), 2)
        self.assertIn("Summary of the conversation", result[0].parts[0].content)

    async def test_compact_preserves_tool_call_return_pair(self):
        """Test that compaction preserves tool call/return pair at the end."""
        config = CompactionConfig(max_tokens=10, target_tokens=5)
        model = ModelMock(responses=["Summary."])
        compactor = HistoryCompactor(config=config, model=model)
        messages = [
            self._make_user_message("first message with content to exceed limit"),
            self._make_assistant_message("response with content to exceed limit"),
            self._make_tool_call_message("search", {"query": "test"}),
            self._make_tool_return_message("search", "results"),
        ]
        result = await compactor.compact(messages)
        self.assertGreater(len(result), 1)
        has_tool_call = any(compactor._has_tool_call_part(m) for m in result)
        has_tool_return = any(compactor._has_tool_return_part(m) for m in result)
        self.assertTrue(has_tool_call)
        self.assertTrue(has_tool_return)

    async def test_compact_skips_when_only_tool_pair(self):
        """Test that compaction is skipped when only tool call/return pair exists."""
        config = CompactionConfig(max_tokens=1, target_tokens=0)
        model = ModelMock(responses=["Summary."])
        compactor = HistoryCompactor(config=config, model=model)
        messages = [
            self._make_tool_call_message("search", {"query": "test"}),
            self._make_tool_return_message("search", "results"),
        ]
        with self.assertLogs("agentic_patterns.core.context.history", level=logging.WARNING):
            result = await compactor.compact(messages)
        self.assertEqual(result, messages)

    async def test_compact_with_model_mock(self):
        """Test compact() uses model for summarization when provided."""
        config = CompactionConfig(max_tokens=10, target_tokens=5)
        model = ModelMock(responses=["Summary of conversation."])
        compactor = HistoryCompactor(config=config, model=model)
        messages = [
            self._make_user_message("first message with lots of text to exceed token limit"),
            self._make_assistant_message("response with lots of text to exceed token limit"),
            self._make_user_message("final message"),
        ]
        result = await compactor.compact(messages)
        self.assertEqual(len(result), 2)
        self.assertIn("Summary of conversation", result[0].parts[0].content)

    async def test_compact_handles_system_prompt(self):
        """Test that compaction properly handles SystemPromptPart in history."""
        config = CompactionConfig(max_tokens=10, target_tokens=5)
        model = ModelMock(responses=["Summary."])
        compactor = HistoryCompactor(config=config, model=model)
        messages = [
            self._make_system_message("You are a helpful assistant"),
            self._make_user_message("first message with lots of text to exceed token limit"),
            self._make_assistant_message("response with lots of text to exceed token limit"),
            self._make_user_message("final message"),
        ]
        result = await compactor.compact(messages)
        self.assertEqual(len(result), 2)

    def test_create_history_processor(self):
        """Test create_history_processor returns callable."""
        compactor = HistoryCompactor(config=self.config, model=self.model)
        processor = compactor.create_history_processor()
        self.assertTrue(callable(processor))

    def test_create_context_aware_processor(self):
        """Test create_context_aware_processor returns callable."""
        compactor = HistoryCompactor(config=self.config, model=self.model)
        processor = compactor.create_context_aware_processor()
        self.assertTrue(callable(processor))

    async def test_on_compaction_callback_called(self):
        """Test that on_compaction callback is called when compaction occurs."""
        callback_results = []

        async def on_compaction(result):
            callback_results.append(result)

        config = CompactionConfig(max_tokens=10, target_tokens=5)
        model = ModelMock(responses=["Summary."])
        compactor = HistoryCompactor(config=config, model=model, on_compaction=on_compaction)
        messages = [
            self._make_user_message("first message with lots of text to exceed token limit"),
            self._make_assistant_message("response with lots of text to exceed token limit"),
            self._make_user_message("final message"),
        ]
        await compactor.compact(messages)
        self.assertEqual(len(callback_results), 1)
        self.assertGreater(callback_results[0].original_messages, callback_results[0].compacted_messages)

    async def test_multi_turn_conversation_with_compaction(self):
        """Test multi-turn conversation where compaction happens and conversation continues."""
        config = CompactionConfig(max_tokens=100, target_tokens=50)
        model = ModelMock(responses=["Summary 1.", "Summary 2.", "Summary 3."])
        compactor = HistoryCompactor(config=config, model=model)

        messages = [
            self._make_user_message("First user message " * 20),
            self._make_assistant_message("First assistant response " * 20),
        ]
        messages = await compactor.compact(messages)
        initial_count = len(messages)

        messages.append(self._make_user_message("Second user message " * 20))
        messages.append(self._make_assistant_message("Second assistant response " * 20))
        messages = await compactor.compact(messages)

        messages.append(self._make_tool_call_message("search", {"q": "test"}))
        messages.append(self._make_tool_return_message("search", "results"))
        messages = await compactor.compact(messages)

        has_tool_call = any(compactor._has_tool_call_part(m) for m in messages)
        has_tool_return = any(compactor._has_tool_return_part(m) for m in messages)
        self.assertTrue(has_tool_call)
        self.assertTrue(has_tool_return)
        self.assertGreaterEqual(len(messages), 2)

    async def test_multi_turn_with_tool_use_mid_conversation(self):
        """Test compaction after tool use in the middle of a conversation."""
        config = CompactionConfig(max_tokens=50, target_tokens=25)
        model = ModelMock(responses=["Summary with tool context."])
        compactor = HistoryCompactor(config=config, model=model)

        messages = [
            self._make_user_message("Search for information " * 10),
            self._make_tool_call_message("search", {"query": "data"}),
            self._make_tool_return_message("search", "Found: relevant data " * 10),
            self._make_assistant_message("Based on the search results " * 10),
            self._make_user_message("Follow up question"),
        ]

        result = await compactor.compact(messages)

        self.assertLessEqual(len(result), len(messages))
        self.assertIsInstance(result[-1], ModelRequest)

    async def test_multi_turn_no_duplicate_system_prompts(self):
        """Test that system prompts are not duplicated after multiple compactions."""
        config = CompactionConfig(max_tokens=100, target_tokens=50)
        model = ModelMock(responses=["Summary 1.", "Summary 2.", "Summary 3."])
        compactor = HistoryCompactor(config=config, model=model)

        messages = [
            self._make_system_message("You are a helpful assistant"),
            self._make_user_message("First message " * 20),
            self._make_assistant_message("First response " * 20),
        ]
        messages = await compactor.compact(messages)

        messages.append(self._make_user_message("Second message " * 20))
        messages.append(self._make_assistant_message("Second response " * 20))
        messages = await compactor.compact(messages)

        messages.append(self._make_user_message("Third message " * 20))
        messages.append(self._make_assistant_message("Third response " * 20))
        messages = await compactor.compact(messages)

        system_prompt_count = sum(
            1 for m in messages
            for p in m.parts
            if isinstance(p, SystemPromptPart)
        )
        self.assertLessEqual(system_prompt_count, 1)

    async def test_multi_turn_no_duplicate_user_prompts(self):
        """Test that original user prompts are replaced by summary, not duplicated."""
        config = CompactionConfig(max_tokens=50, target_tokens=25)
        model = ModelMock(responses=["Summary of conversation."])
        compactor = HistoryCompactor(config=config, model=model)

        original_user_text = "Original user question " * 10
        messages = [
            self._make_user_message(original_user_text),
            self._make_assistant_message("Assistant response " * 10),
            self._make_user_message("Follow up question"),
        ]

        result = await compactor.compact(messages)

        all_content = " ".join(
            p.content for m in result for p in m.parts
            if isinstance(p, UserPromptPart) and isinstance(p.content, str)
        )
        original_word_count = all_content.count("Original user question")
        self.assertLessEqual(original_word_count, 1)


if __name__ == "__main__":
    unittest.main()
