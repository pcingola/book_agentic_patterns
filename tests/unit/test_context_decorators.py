import unittest

from agentic_patterns.core.context.config import TruncationConfig
from agentic_patterns.core.context.decorators import (
    _detect_content_type,
    _get_extension_for_type,
    _truncate_by_type,
)
from agentic_patterns.core.context.models import FileType


class TestContextDecorators(unittest.TestCase):
    """Tests for agentic_patterns.core.context.decorators module."""

    def test_detect_content_type_json_object(self):
        """Test that content starting with { is detected as JSON."""
        content = '{"key": "value"}'
        result = _detect_content_type(content)
        self.assertEqual(result, FileType.JSON)

    def test_detect_content_type_json_array(self):
        """Test that content starting with [ is detected as JSON."""
        content = "[1, 2, 3]"
        result = _detect_content_type(content)
        self.assertEqual(result, FileType.JSON)

    def test_detect_content_type_csv(self):
        """Test that comma-separated content is detected as CSV."""
        content = "name,age,city\nAlice,30,NYC\nBob,25,LA"
        result = _detect_content_type(content)
        self.assertEqual(result, FileType.CSV)

    def test_detect_content_type_text(self):
        """Test that plain text is detected as TEXT."""
        content = "This is just plain text content."
        result = _detect_content_type(content)
        self.assertEqual(result, FileType.TEXT)

    def test_get_extension_for_type_json(self):
        """Test that JSON type returns .json extension."""
        result = _get_extension_for_type(FileType.JSON)
        self.assertEqual(result, ".json")

    def test_get_extension_for_type_csv(self):
        """Test that CSV type returns .csv extension."""
        result = _get_extension_for_type(FileType.CSV)
        self.assertEqual(result, ".csv")

    def test_get_extension_for_type_text(self):
        """Test that TEXT type returns .txt extension."""
        result = _get_extension_for_type(FileType.TEXT)
        self.assertEqual(result, ".txt")

    def test_truncate_csv_preserves_header_and_head_tail(self):
        """Test that CSV truncation preserves header, head rows, and tail rows."""
        lines = ["header,col"] + [f"row{i},val{i}" for i in range(100)]
        content = "\n".join(lines)
        config = TruncationConfig(rows_head=3, rows_tail=2)
        result = _truncate_by_type(content, FileType.CSV, config)
        self.assertIn("header,col", result)
        self.assertIn("row0,val0", result)
        self.assertIn("row2,val2", result)
        self.assertIn("...", result)
        self.assertIn("row99,val99", result)

    def test_truncate_text_preserves_head_tail_lines(self):
        """Test that TEXT truncation preserves head and tail lines."""
        lines = [f"line{i}" for i in range(100)]
        content = "\n".join(lines)
        config = TruncationConfig(lines_head=5, lines_tail=3)
        result = _truncate_by_type(content, FileType.TEXT, config)
        self.assertIn("line0", result)
        self.assertIn("line4", result)
        self.assertIn("...", result)
        self.assertIn("line99", result)

    def test_truncate_small_content_unchanged(self):
        """Test that content smaller than threshold is returned unchanged."""
        content = "small content"
        config = TruncationConfig(lines_head=50, lines_tail=20)
        result = _truncate_by_type(content, FileType.TEXT, config)
        self.assertEqual(result, content)

    def test_truncate_json_array_preserves_structure(self):
        """Test that JSON array truncation preserves valid JSON structure."""
        import json

        data = [{"id": i, "name": f"item{i}"} for i in range(50)]
        content = json.dumps(data)
        config = TruncationConfig(json_array_head=3, json_array_tail=2)
        result = _truncate_by_type(content, FileType.JSON, config)
        parsed = json.loads(result)
        self.assertIsInstance(parsed, list)
        self.assertEqual(parsed[0]["id"], 0)
        self.assertEqual(parsed[2]["id"], 2)
        self.assertIn("omitted", parsed[3])
        self.assertEqual(parsed[-1]["id"], 49)

    def test_truncate_json_object_limits_keys(self):
        """Test that JSON object truncation limits number of keys."""
        import json

        data = {f"key{i}": f"value{i}" for i in range(50)}
        content = json.dumps(data)
        config = TruncationConfig(json_max_keys=5)
        result = _truncate_by_type(content, FileType.JSON, config)
        parsed = json.loads(result)
        self.assertIsInstance(parsed, dict)
        self.assertEqual(len(parsed), 6)  # 5 keys + 1 omitted indicator
        self.assertIn("key0", parsed)
        self.assertTrue(any("omitted" in k for k in parsed.keys()))

    def test_truncate_json_nested_structure(self):
        """Test that nested JSON structures are truncated recursively."""
        import json

        data = {"items": [{"id": i, "tags": list(range(20))} for i in range(30)]}
        content = json.dumps(data)
        config = TruncationConfig(json_array_head=2, json_array_tail=1)
        result = _truncate_by_type(content, FileType.JSON, config)
        parsed = json.loads(result)
        self.assertEqual(len(parsed["items"]), 4)  # 2 head + 1 omitted + 1 tail
        self.assertEqual(
            len(parsed["items"][0]["tags"]), 4
        )  # nested array also truncated

    def test_truncate_json_small_array_unchanged(self):
        """Test that small JSON arrays are not truncated."""
        import json

        data = [1, 2, 3]
        content = json.dumps(data)
        config = TruncationConfig(json_array_head=10, json_array_tail=5)
        result = _truncate_by_type(content, FileType.JSON, config)
        parsed = json.loads(result)
        self.assertEqual(parsed, [1, 2, 3])

    def test_truncate_json_invalid_falls_back_to_char_truncation(self):
        """Test that invalid JSON falls back to character-based truncation."""
        content = "{invalid json" + "x" * 5000
        config = TruncationConfig(max_preview_tokens=100)
        result = _truncate_by_type(content, FileType.JSON, config)
        self.assertTrue(result.endswith("..."))
        self.assertLess(len(result), len(content))

    def test_truncate_json_deep_nesting_limited(self):
        """Test that deeply nested JSON stops at depth limit."""
        import json

        data = {"a": {"b": {"c": {"d": {"e": {"f": {"g": "deep"}}}}}}}
        content = json.dumps(data)
        config = TruncationConfig()
        result = _truncate_by_type(content, FileType.JSON, config)
        parsed = json.loads(result)
        # Should reach depth limit and return "..." for deepest levels
        self.assertEqual(parsed["a"]["b"]["c"]["d"]["e"]["f"], "...")


if __name__ == "__main__":
    unittest.main()
