import unittest

from agentic_patterns.testing.agent_mock import AgentMock, AgentRunMock, MockResult


class TestAgentMock(unittest.IsolatedAsyncioTestCase):
    """Tests for agentic_patterns.testing.agent_mock module."""

    def test_mock_result_str(self):
        """Test that MockResult has proper string representation."""
        result = MockResult(output="test output")
        self.assertIn("test output", str(result))

    async def test_agent_run_mock_iterates_over_nodes(self):
        """Test that AgentRunMock yields all nodes in order."""
        nodes = ["node1", "node2", "node3"]
        run_mock = AgentRunMock(nodes, result_output="final")

        collected = []
        async for node in run_mock:
            collected.append(node)

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

    async def test_agent_mock_context_manager(self):
        """Test that AgentMock can be used as async context manager."""
        agent = AgentMock(nodes=[], result_output=None)

        async with agent as a:
            self.assertIs(a, agent)


if __name__ == "__main__":
    unittest.main()
