"""Test the create_coordinator() factory with multiple A2A agents."""

import socket
import threading
import time
import unittest

import uvicorn
from pydantic_ai.messages import ToolCallPart

from agentic_patterns.core.a2a.config import A2AClientConfig
from agentic_patterns.core.a2a.mock import MockA2AServer
from agentic_patterns.core.a2a.coordinator import create_coordinator
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


class TestCoordinatorMultiAgent(unittest.IsolatedAsyncioTestCase):
    """Test the create_coordinator() factory with multiple A2A agents."""

    @classmethod
    def setUpClass(cls):
        cls.port1 = find_free_port()
        cls.port2 = find_free_port()

        cls.math_server = MockA2AServer(
            name="MathAgent", description="Does math calculations"
        )
        cls.math_server.on_pattern(r".*add.*|.*sum.*|.*plus.*", result="The sum is 10")
        cls.math_server.set_default("I do math")

        cls.text_server = MockA2AServer(name="TextAgent", description="Processes text")
        cls.text_server.on_pattern(r".*count.*|.*words.*", result="There are 5 words")
        cls.text_server.set_default("I process text")

        app1 = cls.math_server.to_app()
        app2 = cls.text_server.to_app()

        cls.thread1 = ServerThread(app1, cls.port1)
        cls.thread2 = ServerThread(app2, cls.port2)
        cls.thread1.start()
        cls.thread2.start()
        time.sleep(0.5)

    @classmethod
    def tearDownClass(cls):
        cls.thread1.stop()
        cls.thread2.stop()

    def setUp(self):
        self.config1 = A2AClientConfig(
            url=f"http://127.0.0.1:{self.port1}", timeout=10, poll_interval=0.1
        )
        self.config2 = A2AClientConfig(
            url=f"http://127.0.0.1:{self.port2}", timeout=10, poll_interval=0.1
        )
        self.math_server.received_prompts.clear()
        self.text_server.received_prompts.clear()

    async def test_coordinator_delegates_to_correct_agent(self):
        """Coordinator with multiple agents delegates to the right one based on task."""
        coordinator = await create_coordinator([self.config1, self.config2])

        model = ModelMock(
            responses=[
                ToolCallPart(tool_name="mathagent", args={"prompt": "add 5 and 5"}),
                "The math agent calculated the sum is 10.",
            ]
        )
        coordinator._model = model

        result = await coordinator.run("What is 5 + 5?")

        self.assertIn("add 5 and 5", self.math_server.received_prompts)
        self.assertEqual(len(self.text_server.received_prompts), 0)


if __name__ == "__main__":
    unittest.main()
