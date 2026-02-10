"""Test that an agent using A2A tools correctly delegates to remote agents."""

import socket
import threading
import time
import unittest

import uvicorn
from pydantic_ai.messages import ToolCallPart

from agentic_patterns.core.a2a.client import A2AClientExtended
from agentic_patterns.core.a2a.config import A2AClientConfig
from agentic_patterns.core.a2a.mock import MockA2AServer
from agentic_patterns.core.a2a.tool import create_a2a_tool
from agentic_patterns.core.agents import get_agent
from agentic_patterns.testing import ModelMock


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


class ServerThread(threading.Thread):
    def __init__(self, app, port: int):
        super().__init__(daemon=True)
        self.app = app
        self.port = port
        self.server = None

    def run(self):
        config = uvicorn.Config(
            self.app, host="127.0.0.1", port=self.port, log_level="error", ws="none"
        )
        self.server = uvicorn.Server(config)
        self.server.run()

    def stop(self):
        if self.server:
            self.server.should_exit = True


class TestAgentDelegatesViaA2A(unittest.IsolatedAsyncioTestCase):
    """Test that an agent using A2A tools correctly delegates to remote agents."""

    @classmethod
    def setUpClass(cls):
        cls.port = find_free_port()
        cls.mock_server = MockA2AServer(
            name="Calculator", description="Performs calculations"
        )
        cls.mock_server.on_prompt("calculate 2+3", result="The answer is 5")
        cls.mock_server.on_pattern(r"multiply \d+ and \d+", result="42")
        cls.mock_server.set_default("I can help with calculations")

        app = cls.mock_server.to_app()
        cls.server_thread = ServerThread(app, cls.port)
        cls.server_thread.start()
        time.sleep(0.5)

    @classmethod
    def tearDownClass(cls):
        cls.server_thread.stop()

    def setUp(self):
        self.config = A2AClientConfig(
            url=f"http://127.0.0.1:{self.port}", timeout=10, poll_interval=0.1
        )
        self.client = A2AClientExtended(self.config)
        self.mock_server.received_prompts.clear()
        self.mock_server.cancelled_task_ids.clear()

    async def asyncTearDown(self):
        await self.client._client.http_client.aclose()

    async def test_agent_delegates_task_to_a2a(self):
        """Agent calls A2A tool, mock receives the prompt, agent gets the result."""
        card = await self.client.get_agent_card()
        a2a_tool = create_a2a_tool(self.client, card)

        model = ModelMock(
            responses=[
                ToolCallPart(tool_name="calculator", args={"prompt": "calculate 2+3"}),
                "Based on the calculation, the answer is 5.",
            ]
        )

        agent = get_agent(model=model, tools=[a2a_tool])
        result = await agent.run("What is 2 plus 3?")

        self.assertIn("calculate 2+3", self.mock_server.received_prompts)
        self.assertIn("5", result.output)

    async def test_a2a_tool_returns_completed_format(self):
        """Verify the tool returns [COMPLETED] formatted string."""
        card = await self.client.get_agent_card()
        a2a_tool = create_a2a_tool(self.client, card)

        tool_func = a2a_tool.function
        result = await tool_func(None, "multiply 7 and 6")

        self.assertTrue(result.startswith("[COMPLETED]"))
        self.assertIn("42", result)


if __name__ == "__main__":
    unittest.main()
