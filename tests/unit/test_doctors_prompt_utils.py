import unittest

from agentic_patterns.core.doctors.prompt_doctor import (
    _extract_placeholders,
    _format_prompt_for_analysis,
)


class TestPromptUtils(unittest.TestCase):
    """Tests for prompt doctor utility functions."""

    def test_extract_placeholders_single(self):
        """Test extracting a single placeholder."""
        content = "Hello {name}, welcome!"
        result = _extract_placeholders(content)
        self.assertEqual(result, ["name"])

    def test_extract_placeholders_multiple(self):
        """Test extracting multiple placeholders."""
        content = "User: {user_name}\nTask: {task_description}\nContext: {context}"
        result = _extract_placeholders(content)
        self.assertEqual(sorted(result), ["context", "task_description", "user_name"])

    def test_extract_placeholders_duplicates_removed(self):
        """Test that duplicate placeholders are removed."""
        content = "{name} said hello to {name} and {other}"
        result = _extract_placeholders(content)
        self.assertEqual(sorted(result), ["name", "other"])

    def test_extract_placeholders_none_found(self):
        """Test extracting placeholders when none exist."""
        content = "This is a plain prompt without any placeholders."
        result = _extract_placeholders(content)
        self.assertEqual(result, [])

    def test_extract_placeholders_underscore_names(self):
        """Test placeholders with underscores."""
        content = "{user_first_name} {_private} {name123}"
        result = _extract_placeholders(content)
        self.assertEqual(sorted(result), ["_private", "name123", "user_first_name"])

    def test_extract_placeholders_ignores_invalid(self):
        """Test that invalid placeholder patterns are ignored."""
        content = "{123invalid} {valid_name} {}"
        result = _extract_placeholders(content)
        self.assertEqual(result, ["valid_name"])

    def test_extract_placeholders_nested_braces(self):
        """Test with JSON-like content (nested braces)."""
        content = 'Output as JSON: {"key": "value"}\nUse {placeholder} here.'
        result = _extract_placeholders(content)
        self.assertEqual(result, ["placeholder"])

    def test_format_prompt_for_analysis_with_placeholders(self):
        """Test formatting prompt with placeholders."""
        name = "system_prompt.md"
        content = "Hello {user}, your task is {task}."
        result = _format_prompt_for_analysis(name, content)

        self.assertIn("### Prompt: system_prompt.md", result)
        self.assertIn("Placeholders:", result)
        self.assertIn("user", result)
        self.assertIn("task", result)
        self.assertIn("Hello {user}", result)

    def test_format_prompt_for_analysis_no_placeholders(self):
        """Test formatting prompt without placeholders."""
        name = "simple.md"
        content = "This is a simple prompt."
        result = _format_prompt_for_analysis(name, content)

        self.assertIn("### Prompt: simple.md", result)
        self.assertIn("Placeholders: (none)", result)
        self.assertIn("This is a simple prompt.", result)

    def test_format_prompt_for_analysis_multiline(self):
        """Test formatting multiline prompt content."""
        name = "multi.md"
        content = "Line 1\nLine 2\nLine 3"
        result = _format_prompt_for_analysis(name, content)

        self.assertIn("### Prompt: multi.md", result)
        self.assertIn("Line 1", result)
        self.assertIn("Line 2", result)
        self.assertIn("Line 3", result)


if __name__ == "__main__":
    unittest.main()
