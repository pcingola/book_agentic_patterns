import unittest

from agentic_patterns.core.tools import ToolSelector
from agentic_patterns.testing import ModelMock, final_result_tool


def tool_read_file(path: str) -> str:
    """Read contents from a file."""
    return f"content of {path}"


def tool_write_file(path: str, content: str) -> bool:
    """Write content to a file."""
    return True


def tool_search(query: str, limit: int = 10) -> list[str]:
    """Search for items matching the query."""
    return [f"result_{i}" for i in range(limit)]


def tool_delete(path: str) -> bool:
    """Delete a file at the given path."""
    return True


class TestToolsSelection(unittest.IsolatedAsyncioTestCase):
    """Tests for agentic_patterns.core.tools.selection module."""

    async def test_select_returns_matching_tools(self):
        """Test that select() returns tools whose names are returned by the model."""
        tools = [tool_read_file, tool_write_file, tool_search, tool_delete]
        model = ModelMock(responses=[final_result_tool(["tool_read_file", "tool_search"])])
        selector = ToolSelector(tools, model=model)

        result = await selector.select("find and read files")

        self.assertEqual(len(result), 2)
        self.assertIn(tool_read_file, result)
        self.assertIn(tool_search, result)

    async def test_select_ignores_unknown_tool_names(self):
        """Test that select() ignores tool names not in the tools list."""
        tools = [tool_read_file, tool_write_file]
        model = ModelMock(responses=[final_result_tool(["tool_read_file", "nonexistent_tool"])])
        selector = ToolSelector(tools, model=model)

        result = await selector.select("read something")

        self.assertEqual(result, [tool_read_file])

    async def test_select_returns_empty_on_no_match(self):
        """Test that select() returns empty list when model returns no matching names."""
        tools = [tool_read_file, tool_write_file]
        model = ModelMock(responses=[final_result_tool([])])
        selector = ToolSelector(tools, model=model)

        result = await selector.select("do something unrelated")

        self.assertEqual(result, [])

    def test_describe_tools_includes_all_tools(self):
        """Test that _describe_tools generates descriptions for all tools."""
        tools = [tool_read_file, tool_write_file, tool_search, tool_delete]
        selector = ToolSelector(tools)
        desc = selector._describe_tools()

        for tool in tools:
            self.assertIn(tool.__name__, desc)


if __name__ == "__main__":
    unittest.main()
