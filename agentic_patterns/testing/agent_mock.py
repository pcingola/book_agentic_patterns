"""Mock agent that replays previously recorded nodes for testing purposes."""

from typing import Any


class AgentMock:
    """
    Mock agent that replays previously recorded nodes.
    Used for testing or replaying agent runs without executing the actual agent.

    Example:
        # Run an agent and save its nodes
        agent = get_agent(...)
        ret, nodes = await run_agent(agent, prompt, ...)

        # Use AgentMock to replay the nodes
        agent_mock = AgentMock(nodes=nodes, result_output=str(ret.result))

        # Now we can use agent_mock in place of the original agent
        ret, nodes = await run_agent(agent_mock, prompt, ...)
    """

    def __init__(self, nodes: list[Any], result_output: str | None = None):
        """
        Initialize the mock agent with pre-recorded nodes.

        Args:
            nodes: List of nodes from a previous agent run
            result_output: Optional output to return as the final result
        """
        self.nodes = nodes
        self.result_output = result_output

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    def iter(self, **kwargs) -> "AgentRunMock":  # noqa: ARG002
        """
        Create an async iterator that replays the recorded nodes.

        Returns:
            An async iterator that yields the recorded nodes
        """
        return AgentRunMock(self.nodes, self.result_output)


class AgentRunMock:
    """Mock agent run that yields pre-recorded nodes."""

    def __init__(self, nodes: list[Any], result_output: str | None = None):
        self.nodes = nodes
        self.result = MockResult(result_output)
        self._index = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._index >= len(self.nodes):
            raise StopAsyncIteration
        node = self.nodes[self._index]
        self._index += 1
        return node


class MockResult:
    """Mock result object that mimics the agent result structure."""

    def __init__(self, output: str | None = None):
        self.output = output

    def __str__(self):
        return f"MockResult(output={self.output})"
