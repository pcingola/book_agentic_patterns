"""Integration tests for A2A client with a real server."""

import socket
import threading
import time
import unittest
import warnings

import uvicorn

from agentic_patterns.core.agents import get_agent
from agentic_patterns.core.a2a.client import A2AClientExtended, TaskStatus
from agentic_patterns.core.a2a.config import A2AClientConfig
from agentic_patterns.core.a2a.utils import extract_text


def find_free_port() -> int:
    """Find an available port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


def multiply(a: int, b: int) -> int:
    """Multiply two numbers."""
    return a * b


class ServerThread(threading.Thread):
    """Thread that runs a uvicorn server."""

    def __init__(self, app, port: int):
        super().__init__(daemon=True)
        self.app = app
        self.port = port
        self.server = None

    def run(self):
        config = uvicorn.Config(
            self.app,
            host="127.0.0.1",
            port=self.port,
            log_level="error"
        )
        self.server = uvicorn.Server(config)
        self.server.run()

    def stop(self):
        if self.server:
            self.server.should_exit = True


class TestA2AClientIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration tests for A2AClientExtended."""

    @classmethod
    def setUpClass(cls):
        warnings.filterwarnings("ignore", category=ResourceWarning)
        cls.port = find_free_port()
        agent = get_agent(
            tools=[add, multiply],
            system_prompt="You are a calculator. Use the tools to compute results. Always use the tools."
        )
        app = agent.to_a2a()
        cls.server_thread = ServerThread(app, cls.port)
        cls.server_thread.start()
        time.sleep(1)

    @classmethod
    def tearDownClass(cls):
        cls.server_thread.stop()

    def setUp(self):
        self.config = A2AClientConfig(
            url=f"http://127.0.0.1:{self.port}",
            timeout=60,
            poll_interval=0.5,
            max_retries=3,
            retry_delay=0.5
        )
        self.client = A2AClientExtended(self.config)

    async def test_get_agent_card(self):
        """Test fetching agent card from server."""
        card = await self.client.get_agent_card()
        self.assertIsNotNone(card)
        self.assertIn("name", card)

    async def test_send_and_observe_simple_task(self):
        """Test sending a simple message and getting a response."""
        status, task = await self.client.send_and_observe("What is 2 + 3?")
        self.assertEqual(status, TaskStatus.COMPLETED)
        self.assertIsNotNone(task)
        text = extract_text(task)
        self.assertIn("5", text)

    async def test_send_and_observe_with_multiplication(self):
        """Test using a different tool."""
        status, task = await self.client.send_and_observe("What is 7 times 6?")
        self.assertEqual(status, TaskStatus.COMPLETED)
        self.assertIsNotNone(task)
        text = extract_text(task)
        self.assertIn("42", text)

    async def test_cancellation_callback(self):
        """Test that cancellation callback is checked."""
        def is_cancelled():
            return True

        status, task = await self.client.send_and_observe(
            "What is 1 + 1?",
            is_cancelled=is_cancelled
        )
        self.assertEqual(status, TaskStatus.CANCELLED)


if __name__ == "__main__":
    unittest.main()
