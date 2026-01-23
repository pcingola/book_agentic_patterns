import unittest
import sys
from pathlib import Path

# Add test data to path for importing test modules
TEST_DATA_DIR = Path(__file__).parent.parent / "data" / "doctors"


class TestCLIImport(unittest.TestCase):
    """Tests for CLI _import_tools function."""

    @classmethod
    def setUpClass(cls):
        # Add test data directory to path
        sys.path.insert(0, str(TEST_DATA_DIR))

    @classmethod
    def tearDownClass(cls):
        # Remove test data directory from path
        if str(TEST_DATA_DIR) in sys.path:
            sys.path.remove(str(TEST_DATA_DIR))

    def test_import_tools_module_only(self):
        """Test importing all tools from a module."""
        from agentic_patterns.core.doctors.__main__ import _import_tools

        tools = _import_tools("sample_tools")
        # Should find callable functions with docstrings
        tool_names = [t.__name__ for t in tools]
        self.assertIn("add_numbers", tool_names)
        self.assertIn("greet_user", tool_names)

    def test_import_tools_module_with_attr(self):
        """Test importing specific attribute from module."""
        from agentic_patterns.core.doctors.__main__ import _import_tools

        tools = _import_tools("sample_tools:add_numbers")
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0].__name__, "add_numbers")

    def test_import_tools_module_with_list_attr(self):
        """Test importing list of tools from module."""
        from agentic_patterns.core.doctors.__main__ import _import_tools

        tools = _import_tools("sample_tools:TOOLS_LIST")
        self.assertEqual(len(tools), 2)
        tool_names = [t.__name__ for t in tools]
        self.assertIn("add_numbers", tool_names)
        self.assertIn("greet_user", tool_names)

    def test_import_tools_excludes_private(self):
        """Test that private functions (starting with _) are excluded."""
        from agentic_patterns.core.doctors.__main__ import _import_tools

        tools = _import_tools("sample_tools")
        tool_names = [t.__name__ for t in tools]
        self.assertNotIn("_private_helper", tool_names)

    def test_import_tools_nonexistent_module(self):
        """Test importing from nonexistent module raises error."""
        from agentic_patterns.core.doctors.__main__ import _import_tools

        with self.assertRaises(ModuleNotFoundError):
            _import_tools("nonexistent_module_xyz")


if __name__ == "__main__":
    unittest.main()
