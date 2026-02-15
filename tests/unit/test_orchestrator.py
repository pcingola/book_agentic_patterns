import socket
import threading
import time
import unittest
from pathlib import Path

import uvicorn
from pydantic_ai.messages import ToolCallPart

from agentic_patterns.core.agents.orchestrator import AgentSpec, OrchestratorAgent
from agentic_patterns.core.a2a.client import A2AClientExtended
from agentic_patterns.core.a2a.config import A2AClientConfig
from agentic_patterns.core.a2a.mock import MockA2AServer
from agentic_patterns.core.skills.models import Skill
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


def sample_tool(x: int) -> int:
    """Doubles the input."""
    return x * 2


class TestOrchestratorAgent(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = find_free_port()
        cls.loop = asyncio.new_event_loop()

    def setUp(self):
        asyncio.get_event_loop().slow_callback_duration = 0.5
        cls.mock_server = MockA2AServer(
            name="Researcher", description="Researches topics"
        )
        cls.mock_server.on_prompt("Find info", result="Found it!")
        cls.mock_server.set_default("I can help with research")

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

    async def asyncTearDown(self):
        await self.client._client.http_client.aclose()

    async def test_creates_a2a_delegation_tools(self):
        """A2A clients should be converted to delegation tools."""
        model = ModelMock(
            responses=[
                ToolCallPart(tool_name="researcher", args={"prompt": "Find info"}),
                "Done.",
            ]
        )

        spec = AgentSpec(name="coordinator", model=model, a2a_clients=[self.client])

        async with OrchestratorAgent(spec) as agent:
            await agent.run("Research something")

        self.assertIn("Find info", self.mock_server.received_prompts)

    async def test_builds_system_prompt_with_skills(self):
        """Skills should be listed in the system prompt."""
        model = ModelMock(responses=["I see the skill."])
        skill = Skill(
            name="code-review",
            description="Reviews code for issues",
            path=Path("/tmp/code-review"),
            frontmatter={
                "name": "code-review",
                "description": "Reviews code for issues",
            },
            body="# Instructions",
            script_paths=[],
            reference_paths=[],
            asset_paths=[],
        )
        spec = AgentSpec(name="skilled-agent", model=model, skills=[skill])

        async with OrchestratorAgent(spec) as agent:
            system_prompt = agent._build_system_prompt([])

        self.assertIn("code-review", system_prompt)
        self.assertIn("Reviews code", system_prompt)

    async def test_run_without_context_manager_raises(self):
        """Running without entering context manager should raise RuntimeError."""
        model = ModelMock(responses=["Should fail"])
        spec = AgentSpec(name="test", model=model)
        agent = OrchestratorAgent(spec)

        with self.assertRaises(RuntimeError):
            await agent.run("This should fail")

    async def test_cleanup_on_exit(self):
        """Agent and connections should be cleaned up on context exit."""
        model = ModelMock(responses=["Done"])
        spec = AgentSpec(name="cleanup-test", model=model)

        agent = OrchestratorAgent(spec)
        async with agent:
            self.assertIsNotNone(agent._agent)

        self.assertIsNone(agent._agent)
        self.assertIsNone(agent._broker)


if __name__ == "__main__":
    unittest.main()
