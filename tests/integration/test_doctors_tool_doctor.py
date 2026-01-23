import asyncio
import unittest

from agentic_patterns.core.doctors import ToolDoctor, ToolRecommendation, tool_doctor


def well_defined_tool(name: str, count: int = 1) -> str:
    """Greet a user multiple times.

    Args:
        name: The name of the person to greet.
        count: Number of times to repeat the greeting.

    Returns:
        A greeting string repeated count times.
    """
    return f"Hello, {name}! " * count


def poorly_defined_tool(x, y):
    return x + y


class TestToolDoctor(unittest.IsolatedAsyncioTestCase):
    """Integration tests for ToolDoctor."""

    def setUp(self):
        loop = asyncio.get_event_loop()
        loop.slow_callback_duration = 30.0

    async def test_tool_doctor_single_well_defined(self):
        """Test analyzing a well-defined tool."""
        doctor = ToolDoctor()
        result = await doctor.analyze(well_defined_tool)

        self.assertIsInstance(result, ToolRecommendation)
        self.assertEqual(result.name, "well_defined_tool")

    async def test_tool_doctor_single_poorly_defined(self):
        """Test analyzing a poorly-defined tool."""
        doctor = ToolDoctor()
        result = await doctor.analyze(poorly_defined_tool)

        self.assertIsInstance(result, ToolRecommendation)
        self.assertEqual(result.name, "poorly_defined_tool")
        # Poorly-defined tool should need improvement (no types, no docstring)
        self.assertTrue(result.needs_improvement)

    async def test_tool_doctor_batch(self):
        """Test analyzing multiple tools."""
        tools = [well_defined_tool, poorly_defined_tool]
        results = await tool_doctor(tools, batch_size=5)

        self.assertEqual(len(results), 2)
        self.assertIsInstance(results[0], ToolRecommendation)
        self.assertIsInstance(results[1], ToolRecommendation)

    async def test_tool_doctor_batching(self):
        """Test that batching works correctly with multiple batches."""

        def tool_a(x: int) -> int:
            """Tool A."""
            return x

        def tool_b(x: int) -> int:
            """Tool B."""
            return x

        def tool_c(x: int) -> int:
            """Tool C."""
            return x

        tools = [tool_a, tool_b, tool_c]
        results = await tool_doctor(tools, batch_size=2)

        self.assertEqual(len(results), 3)


if __name__ == "__main__":
    unittest.main()
