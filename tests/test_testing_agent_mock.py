import asyncio
import unittest

from agentic_patterns.testing.agent_mock import AgentMock, AgentRunMock, MockResult


class TestAgentMock(unittest.TestCase):
    """Tests for agentic_patterns.testing.agent_mock module."""

    def test_mock_result_str(self):
        """Test that MockResult has proper string representation."""
        result = MockResult(output="test output")
        self.assertIn("test output", str(result))

    def test_agent_run_mock_iterates_over_nodes(self):
        """Test that AgentRunMock yields all nodes in order."""
        nodes = ["node1", "node2", "node3"]
        run_mock = AgentRunMock(nodes, result_output="final")

        loop = asyncio.get_event_loop()

        async def collect_nodes():
            collected = []
            async for node in run_mock:
                collected.append(node)
            return collected

        collected = loop.run_until_complete(collect_nodes())
        self.assertEqual(collected, nodes)

    def test_agent_run_mock_has_result(self):
        """Test that AgentRunMock provides access to the result."""
        run_mock = AgentRunMock([], result_output="the result")
        self.assertIsInstance(run_mock.result, MockResult)
        self.assertEqual(run_mock.result.output, "the result")

    def test_agent_mock_iter_returns_run_mock(self):
        """Test that AgentMock.iter() returns an AgentRunMock."""
        agent = AgentMock(nodes=["a", "b"], result_output="done")
        run = agent.iter(user_prompt="test")
        self.assertIsInstance(run, AgentRunMock)

    def test_agent_mock_context_manager(self):
        """Test that AgentMock can be used as async context manager."""
        agent = AgentMock(nodes=[], result_output=None)

        loop = asyncio.get_event_loop()

        async def use_context():
            async with agent as a:
                return a

        result = loop.run_until_complete(use_context())
        self.assertIs(result, agent)


if __name__ == "__main__":
    unittest.main()
