import unittest

from agentic_patterns.core.tools import func_to_description


def simple_func():
    """A simple function."""
    return "hello"


def func_with_args(name: str, count: int = 5) -> str:
    """Greets a person multiple times."""
    return name * count


def func_with_generic_type(items: list[str]) -> dict[str, int]:
    """Processes a list of strings."""
    return {item: len(item) for item in items}


def func_no_docstring(x: int) -> int:
    return x * 2


class TestToolsUtils(unittest.TestCase):
    """Tests for agentic_patterns.core.tools.utils module."""

    def test_func_to_description_simple(self):
        """Test description generation for a simple function."""
        desc = func_to_description(simple_func)
        self.assertIn("Tool: simple_func()", desc)
        self.assertIn("A simple function.", desc)

    def test_func_to_description_with_args(self):
        """Test description includes parameter types and defaults."""
        desc = func_to_description(func_with_args)
        self.assertIn("name: str", desc)
        self.assertIn("count: int = 5", desc)
        self.assertIn("-> str", desc)

    def test_func_to_description_generic_types(self):
        """Test description handles generic types like list[str]."""
        desc = func_to_description(func_with_generic_type)
        self.assertIn("list[str]", desc)
        self.assertIn("dict[str, int]", desc)

    def test_func_to_description_no_docstring(self):
        """Test description generation for function without docstring."""
        desc = func_to_description(func_no_docstring)
        self.assertIn("Tool: func_no_docstring", desc)
        self.assertNotIn("Description:", desc)


if __name__ == "__main__":
    unittest.main()
