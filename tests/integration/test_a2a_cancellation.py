"""Test that cancellation from agent is correctly propagated to A2A server."""

import socket
import threading
import time
import unittest

import uvicorn

from agentic_patterns.core.a2a.client import A2AClientExtended
from agentic_patterns.core.a2a.config import A2AClientConfig
from agentic_patterns.core.a2a.mock import MockA2AServer
from agentic_patterns.core.a2a.tool import create_a2a_tool


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


class TestCancellationPropagation(unittest.IsolatedAsyncioTestCase):
    """Test that cancellation from agent is correctly propagated to A2A server."""

    @classmethod
    def setUpClass(cls):
        cls.port = find_free_port()
        cls.mock_server = MockA2AServer(
            name="SlowAgent", description="Takes time to respond"
        )
        cls.mock_server.on_prompt_delayed(
            "slow task", polls=10, result="Eventually done"
        )

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

    async def test_cancellation_callback_triggers_cancel_on_a2a(self):
        """When is_cancelled returns True, the task is cancelled on the A2A server."""
        call_count = 0

        def is_cancelled():
            nonlocal call_count
            call_count += 1
            return call_count > 2

        card = await self.client.get_agent_card()
        a2a_tool = create_a2a_tool(self.client, card, is_cancelled=is_cancelled)

        tool_func = a2a_tool.function
        result = await tool_func(None, "slow task")

        self.assertEqual(result, "[CANCELLED] Task was cancelled")
        self.assertEqual(len(self.mock_server.cancelled_task_ids), 1)


if __name__ == "__main__":
    unittest.main()
