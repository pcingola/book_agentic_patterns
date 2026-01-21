import unittest
from pathlib import Path

from agentic_patterns.core.prompt import load_prompt


DATA_DIR = Path(__file__).parent / "data" / "prompts"


class TestPrompt(unittest.TestCase):
    """Tests for agentic_patterns.core.prompt module."""

    def test_load_prompt_no_variables(self):
        """Test loading a prompt template without variables."""
        result = load_prompt(DATA_DIR / "simple.md")
        self.assertEqual(result, "This is a simple prompt without variables.")

    def test_load_prompt_with_variables(self):
        """Test variable substitution in prompt template."""
        result = load_prompt(DATA_DIR / "with_vars.md", name="Alice", location="Paris")
        self.assertEqual(result, "Hello Alice, welcome to Paris.")

    def test_load_prompt_missing_variable(self):
        """Test that missing variables raise ValueError."""
        with self.assertRaises(ValueError) as ctx:
            load_prompt(DATA_DIR / "with_vars.md", name="Alice")
        self.assertIn("location", str(ctx.exception))

    def test_load_prompt_unused_variable(self):
        """Test that unused variables raise ValueError."""
        with self.assertRaises(ValueError) as ctx:
            load_prompt(DATA_DIR / "simple.md", extra="unused")
        self.assertIn("extra", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
