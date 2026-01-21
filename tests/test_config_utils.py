import unittest
from pathlib import Path

from agentic_patterns.core.config.utils import all_parents, get_project_root


class TestConfigUtils(unittest.TestCase):
    """Tests for agentic_patterns.core.config.utils module."""

    def test_all_parents_yields_parent_directories(self):
        """Test that all_parents yields all parent directories of a path."""
        path = Path("/a/b/c/d")
        parents = list(all_parents(path))
        expected = [Path("/a/b/c/d"), Path("/a/b/c"), Path("/a/b"), Path("/a")]
        self.assertEqual(parents, expected)

    def test_all_parents_single_level(self):
        """Test all_parents with a single level path."""
        path = Path("/a")
        parents = list(all_parents(path))
        expected = [Path("/a")]
        self.assertEqual(parents, expected)

    def test_get_project_root_returns_path(self):
        """Test that get_project_root returns a Path object."""
        root = get_project_root()
        self.assertIsInstance(root, Path)
        self.assertTrue(root.exists())


if __name__ == "__main__":
    unittest.main()
