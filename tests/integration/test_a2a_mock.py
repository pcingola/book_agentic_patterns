"""Integration tests for A2A using MockA2AServer."""

import logging
import socket
import threading
import time
import unittest

import uvicorn

from agentic_patterns.core.a2a.client import A2AClientExtended, TaskStatus
from agentic_patterns.core.a2a.config import A2AClientConfig
from agentic_patterns.core.a2a.mock import MockA2AServer
from agentic_patterns.core.a2a.utils import extract_text, extract_question

logging.getLogger("agentic_patterns.core.a2a.client").setLevel(logging.CRITICAL)


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


class TestMockA2AServer(unittest.IsolatedAsyncioTestCase):
    """Test MockA2AServer with A2AClientExtended."""

    @classmethod
    def setUpClass(cls):
        cls.port = find_free_port()
        cls.mock_server = MockA2AServer(name="TestAgent", description="Test agent")
        cls.mock_server.on_prompt("hello", result="Hello back!")
        cls.mock_server.on_pattern(r"add \d+ and \d+", result="42")
        cls.mock_server.on_prompt("need info", input_required="What is your name?")
        cls.mock_server.on_prompt("fail please", error="Something went wrong")
        cls.mock_server.set_default("Default response")

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

    async def asyncTearDown(self):
        await self.client._client.http_client.aclose()

    async def test_agent_sends_task_and_receives_response(self):
        """Basic: send task, get response, verify prompt was recorded."""
        status, task = await self.client.send_and_observe("hello")

        self.assertEqual(status, TaskStatus.COMPLETED)
        self.assertEqual(extract_text(task), "Hello back!")
        self.assertIn("hello", self.mock_server.received_prompts)

    async def test_pattern_matching(self):
        """Pattern matching works."""
        status, task = await self.client.send_and_observe("add 5 and 7")

        self.assertEqual(status, TaskStatus.COMPLETED)
        self.assertEqual(extract_text(task), "42")

    async def test_default_response(self):
        """Unmatched prompts get default response."""
        status, task = await self.client.send_and_observe("unknown query")

        self.assertEqual(status, TaskStatus.COMPLETED)
        self.assertEqual(extract_text(task), "Default response")

    async def test_input_required_propagation(self):
        """INPUT_REQUIRED status is properly returned with question."""
        status, task = await self.client.send_and_observe("need info")

        self.assertEqual(status, TaskStatus.INPUT_REQUIRED)
        question = extract_question(task)
        self.assertEqual(question, "What is your name?")

    async def test_failed_task(self):
        """FAILED status is properly returned."""
        status, task = await self.client.send_and_observe("fail please")

        self.assertEqual(status, TaskStatus.FAILED)

    async def test_cancellation_from_client(self):
        """Cancellation callback triggers cancel and is recorded."""
        # Use a delayed response so there's time for cancellation check
        self.mock_server.on_prompt_delayed(
            "cancel me", polls=5, result="Should not see this"
        )

        call_count = 0

        def is_cancelled():
            nonlocal call_count
            call_count += 1
            return call_count > 1  # Cancel on second poll

        status, task = await self.client.send_and_observe(
            "cancel me", is_cancelled=is_cancelled
        )

        self.assertEqual(status, TaskStatus.CANCELLED)

    async def test_get_agent_card(self):
        """Agent card is correctly returned."""
        card = await self.client.get_agent_card()

        self.assertEqual(card["name"], "TestAgent")
        self.assertEqual(card["description"], "Test agent")


if __name__ == "__main__":
    unittest.main()
