import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from pydantic_ai.messages import ToolCallPart

from agentic_patterns.core.agents.orchestrator import AgentSpec, OrchestratorAgent
from agentic_patterns.core.a2a.client import A2AClientExtended, TaskStatus
from agentic_patterns.core.skills.models import Skill
from agentic_patterns.testing import ModelMock


def sample_tool(x: int) -> int:
    """Doubles the input."""
    return x * 2


class TestOrchestratorAgent(unittest.IsolatedAsyncioTestCase):

    async def test_creates_a2a_delegation_tools(self):
        """A2A clients should be converted to delegation tools."""
        model = ModelMock(responses=[
            ToolCallPart(tool_name="researcher", args={"prompt": "Find info"}),
            "Done.",
        ])

        mock_a2a_client = MagicMock(spec=A2AClientExtended)
        mock_a2a_client.get_agent_card = AsyncMock(return_value={
            "name": "Researcher",
            "description": "Researches topics",
        })
        mock_a2a_client.send_and_observe = AsyncMock(return_value=(
            TaskStatus.COMPLETED,
            {"id": "task-123", "status": {"state": "completed"}, "artifacts": [{"parts": [{"text": "Found it!"}]}]},
        ))

        spec = AgentSpec(name="coordinator", model=model, a2a_clients=[mock_a2a_client])

        async with OrchestratorAgent(spec) as agent:
            await agent.run("Research something")

        mock_a2a_client.send_and_observe.assert_called_once()

    async def test_builds_system_prompt_with_skills(self):
        """Skills should be listed in the system prompt."""
        model = ModelMock(responses=["I see the skill."])
        skill = Skill(
            name="code-review",
            description="Reviews code for issues",
            path=Path("/tmp/code-review"),
            frontmatter={"name": "code-review", "description": "Reviews code for issues"},
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
        self.assertEqual(agent._mcp_connections, [])


if __name__ == "__main__":
    unittest.main()
