"""Test that INPUT_REQUIRED from A2A server propagates correctly through the agent."""

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
        config = uvicorn.Config(self.app, host="127.0.0.1", port=self.port, log_level="error", ws="none")
        self.server = uvicorn.Server(config)
        self.server.run()

    def stop(self):
        if self.server:
            self.server.should_exit = True


class TestInputRequiredPropagation(unittest.IsolatedAsyncioTestCase):
    """Test that INPUT_REQUIRED from A2A server propagates correctly through the agent."""

    @classmethod
    def setUpClass(cls):
        cls.port = find_free_port()
        cls.mock_server = MockA2AServer(name="FormBot", description="Collects user information")
        cls.mock_server.on_prompt("start form", input_required="What is your name?")
        cls.mock_server.on_pattern(r"name is .*", result="Thank you, form completed")

        app = cls.mock_server.to_app()
        cls.server_thread = ServerThread(app, cls.port)
        cls.server_thread.start()
        time.sleep(0.5)

    @classmethod
    def tearDownClass(cls):
        cls.server_thread.stop()

    def setUp(self):
        self.config = A2AClientConfig(url=f"http://127.0.0.1:{self.port}", timeout=10, poll_interval=0.1)
        self.client = A2AClientExtended(self.config)
        self.mock_server.received_prompts.clear()

    async def asyncTearDown(self):
        await self.client._client.http_client.aclose()

    async def test_input_required_returns_question_with_task_id(self):
        """When A2A returns INPUT_REQUIRED, tool returns formatted response with task_id."""
        card = await self.client.get_agent_card()
        a2a_tool = create_a2a_tool(self.client, card)

        tool_func = a2a_tool.function
        result = await tool_func(None, "start form")

        self.assertTrue(result.startswith("[INPUT_REQUIRED:task_id="))
        self.assertIn("What is your name?", result)

    async def test_agent_receives_input_required_in_tool_result(self):
        """Agent calling tool receives INPUT_REQUIRED status and can ask user."""
        card = await self.client.get_agent_card()
        a2a_tool = create_a2a_tool(self.client, card)

        model = ModelMock(responses=[
            ToolCallPart(tool_name="formbot", args={"prompt": "start form"}),
            "The form bot is asking: What is your name?",
        ])

        agent = get_agent(model=model, tools=[a2a_tool])
        result = await agent.run("Fill out the form")

        self.assertIn("start form", self.mock_server.received_prompts)
        self.assertIn("name", result.output.lower())


if __name__ == "__main__":
    unittest.main()
