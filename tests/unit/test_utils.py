import unittest

from agentic_patterns.core.utils import str2bool


class TestStr2Bool(unittest.TestCase):
    """Tests for str2bool function in agentic_patterns.core.utils."""

    def test_none_returns_false(self):
        """Test that None input returns False."""
        self.assertFalse(str2bool(None))

    def test_empty_string_returns_false(self):
        """Test that empty string returns False."""
        self.assertFalse(str2bool(""))

    def test_true_values(self):
        """Test that 'yes', 'true', 'on', '1' return True (case insensitive)."""
        for value in ("yes", "YES", "Yes", "true", "TRUE", "True", "on", "ON", "1"):
            with self.subTest(value=value):
                self.assertTrue(str2bool(value))

    def test_false_values(self):
        """Test that other strings return False."""
        for value in ("no", "false", "off", "0", "random", "nope"):
            with self.subTest(value=value):
                self.assertFalse(str2bool(value))


if __name__ == "__main__":
    unittest.main()
