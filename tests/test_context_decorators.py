import unittest

from agentic_patterns.core.context.config import TruncationConfig
from agentic_patterns.core.context.decorators import _detect_content_type, _get_extension_for_type, _truncate_by_type
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
        content = '[1, 2, 3]'
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


if __name__ == "__main__":
    unittest.main()
