import unittest
from pathlib import Path

from agentic_patterns.core.context.models import FileType
from agentic_patterns.core.context.reader import (
    _detect_file_type,
    read_file,
    read_file_as_string,
)


DATA_DIR = Path(__file__).parent.parent / "data" / "context"


class TestContextReader(unittest.TestCase):
    """Tests for agentic_patterns.core.context.reader module."""

    def test_detect_file_type_python(self):
        """Test that .py files are detected as CODE type."""
        result = _detect_file_type(Path("test.py"))
        self.assertEqual(result, FileType.CODE)

    def test_detect_file_type_json(self):
        """Test that .json files are detected as JSON type."""
        result = _detect_file_type(Path("test.json"))
        self.assertEqual(result, FileType.JSON)

    def test_detect_file_type_csv(self):
        """Test that .csv files are detected as CSV type."""
        result = _detect_file_type(Path("test.csv"))
        self.assertEqual(result, FileType.CSV)

    def test_detect_file_type_markdown(self):
        """Test that .md files are detected as MARKDOWN type."""
        result = _detect_file_type(Path("test.md"))
        self.assertEqual(result, FileType.MARKDOWN)

    def test_detect_file_type_text(self):
        """Test that .txt files are detected as TEXT type."""
        result = _detect_file_type(Path("test.txt"))
        self.assertEqual(result, FileType.TEXT)

    def test_detect_file_type_unknown(self):
        """Test that unknown extensions are detected as BINARY type."""
        result = _detect_file_type(Path("test.xyz"))
        self.assertEqual(result, FileType.BINARY)

    def test_read_file_text_success(self):
        """Test that read_file successfully reads a text file."""
        result = read_file(DATA_DIR / "sample.txt")
        self.assertTrue(result.success)
        self.assertEqual(result.file_type, FileType.TEXT)
        self.assertIn("simple text file", result.content)

    def test_read_file_json_success(self):
        """Test that read_file successfully reads a JSON file."""
        result = read_file(DATA_DIR / "sample.json")
        self.assertTrue(result.success)
        self.assertEqual(result.file_type, FileType.JSON)
        self.assertIn("test", result.content)

    def test_read_file_csv_success(self):
        """Test that read_file successfully reads a CSV file."""
        result = read_file(DATA_DIR / "sample.csv")
        self.assertTrue(result.success)
        self.assertEqual(result.file_type, FileType.CSV)
        self.assertIn("Alice", result.content)

    def test_read_file_code_success(self):
        """Test that read_file successfully reads a Python file."""
        result = read_file(DATA_DIR / "sample.py")
        self.assertTrue(result.success)
        self.assertEqual(result.file_type, FileType.CODE)
        self.assertIn("def hello", result.content)

    def test_read_file_not_found(self):
        """Test that read_file returns error for non-existent file."""
        result = read_file(DATA_DIR / "nonexistent.txt")
        self.assertFalse(result.success)
        self.assertIn("not found", result.error_message)

    def test_read_file_as_string_success(self):
        """Test that read_file_as_string returns content string."""
        content = read_file_as_string(DATA_DIR / "sample.txt")
        self.assertIn("simple text file", content)

    def test_read_file_as_string_not_found(self):
        """Test that read_file_as_string returns error message for non-existent file."""
        content = read_file_as_string(DATA_DIR / "nonexistent.txt")
        self.assertIn("Error", content)


if __name__ == "__main__":
    unittest.main()
