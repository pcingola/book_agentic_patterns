import asyncio
import tempfile
import unittest
import warnings
from pathlib import Path

from agentic_patterns.core.doctors import (
    PromptDoctor,
    PromptRecommendation,
    prompt_doctor,
)

# PydanticAI agents create an internal async HTTP client (via OpenAI/OpenRouter
# provider) whose lifecycle is tied to the provider, not the agent. When the
# agent goes out of scope after run_agent() the underlying transport is not
# explicitly closed, causing Python to emit ResourceWarning about unclosed
# sockets. This is a known PydanticAI behavior -- the transport is cleaned up
# by GC, but the warning fires before that in tests. Filtering it here because
# there is no public API to close the provider's HTTP client from our code.
warnings.filterwarnings("ignore", category=ResourceWarning, module=r"asyncio\.selector_events")


WELL_DEFINED_PROMPT = """## System Prompt

You are a helpful assistant that answers questions about programming.

When responding:
1. Be concise and accurate
2. Provide code examples when helpful
3. Explain your reasoning

User query: {user_query}
"""

POORLY_DEFINED_PROMPT = """do stuff with {thing}"""


class TestPromptDoctor(unittest.IsolatedAsyncioTestCase):
    """Integration tests for PromptDoctor."""

    def setUp(self):
        loop = asyncio.get_event_loop()
        loop.slow_callback_duration = 30.0

    async def test_prompt_doctor_string_well_defined(self):
        """Test analyzing a well-defined prompt string."""
        doctor = PromptDoctor()
        result = await doctor.analyze(WELL_DEFINED_PROMPT)

        self.assertIsInstance(result, PromptRecommendation)
        self.assertIn("user_query", result.placeholders_found)

    async def test_prompt_doctor_string_poorly_defined(self):
        """Test analyzing a poorly-defined prompt string."""
        doctor = PromptDoctor()
        result = await doctor.analyze(POORLY_DEFINED_PROMPT)

        self.assertIsInstance(result, PromptRecommendation)
        self.assertIn("thing", result.placeholders_found)
        # Poorly-defined prompt should need improvement
        self.assertTrue(result.needs_improvement)

    async def test_prompt_doctor_file(self):
        """Test analyzing a prompt file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(WELL_DEFINED_PROMPT)
            temp_path = Path(f.name)

        try:
            doctor = PromptDoctor()
            result = await doctor.analyze(temp_path)

            self.assertIsInstance(result, PromptRecommendation)
            self.assertEqual(result.name, temp_path.name)
            self.assertIn("user_query", result.placeholders_found)
        finally:
            temp_path.unlink()

    async def test_prompt_doctor_batch(self):
        """Test analyzing multiple prompts."""
        prompts = [WELL_DEFINED_PROMPT, POORLY_DEFINED_PROMPT]
        results = await prompt_doctor(prompts, batch_size=5)

        self.assertEqual(len(results), 2)
        self.assertIsInstance(results[0], PromptRecommendation)
        self.assertIsInstance(results[1], PromptRecommendation)

    async def test_prompt_doctor_mixed_input(self):
        """Test analyzing mix of strings and files."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(WELL_DEFINED_PROMPT)
            temp_path = Path(f.name)

        try:
            prompts = [POORLY_DEFINED_PROMPT, temp_path]
            results = await prompt_doctor(prompts, batch_size=5)

            self.assertEqual(len(results), 2)
        finally:
            temp_path.unlink()


if __name__ == "__main__":
    unittest.main()
