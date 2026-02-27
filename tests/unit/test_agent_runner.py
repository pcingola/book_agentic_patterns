"""Unit tests for AgentRunner."""

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from agentic_patterns.core.agents.agent_runner import AgentResult, AgentRunner
from agentic_patterns.core.agents.agent_status import AgentStatus


class TestAgentRunner(unittest.IsolatedAsyncioTestCase):
    def _make_mock_spec(self, name: str = "test-agent"):
        spec = AsyncMock()
        spec.name = name
        spec.description = f"Mock {name}"
        return spec

    async def test_launch_unknown_agent_raises(self):
        runner = AgentRunner({"known": self._make_mock_spec("known")})
        with self.assertRaises(ValueError) as ctx:
            await runner.launch("unknown", "do something")
        self.assertIn("Unknown agent", str(ctx.exception))

    async def test_launch_foreground_completed(self):
        spec = self._make_mock_spec("worker")
        runner = AgentRunner({"worker": spec})

        with patch.object(runner, "_run_local", new_callable=AsyncMock) as mock_run:

            async def fake_run(agent_id, agent_name, prompt):
                runner._results[agent_id].output = "result text"
                runner._results[agent_id].status = AgentStatus.COMPLETED

            mock_run.side_effect = fake_run

            result = await runner.launch("worker", "do something")
            self.assertEqual(result.status, AgentStatus.COMPLETED)
            self.assertEqual(result.output, "result text")

    async def test_launch_background_returns_running(self):
        spec = self._make_mock_spec("worker")
        runner = AgentRunner({"worker": spec})

        with patch.object(runner, "_run_local", new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = lambda *a: asyncio.sleep(10)

            result = await runner.launch(
                "worker", "do something", run_in_background=True
            )
            self.assertEqual(result.status, AgentStatus.RUNNING)
            self.assertIn(result.agent_id, runner._running_tasks)

            await runner.cancel_all()

    async def test_stop_running_agent(self):
        spec = self._make_mock_spec("worker")
        runner = AgentRunner({"worker": spec})

        with patch.object(runner, "_run_local", new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = lambda *a: asyncio.sleep(10)

            result = await runner.launch("worker", "task", run_in_background=True)
            self.assertTrue(runner.stop(result.agent_id))

            final = runner.get_output(result.agent_id)
            self.assertEqual(final.status, AgentStatus.CANCELLED)

    async def test_stop_nonexistent_returns_false(self):
        runner = AgentRunner({"worker": self._make_mock_spec()})
        self.assertFalse(runner.stop("nonexistent"))

    async def test_cancel_all(self):
        spec = self._make_mock_spec("worker")
        runner = AgentRunner({"worker": spec})

        with patch.object(runner, "_run_local", new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = lambda *a: asyncio.sleep(10)

            await runner.launch("worker", "task1", run_in_background=True)
            await runner.launch("worker", "task2", run_in_background=True)
            self.assertEqual(len(runner._running_tasks), 2)

            await runner.cancel_all()
            self.assertEqual(len(runner._running_tasks), 0)

    async def test_get_output(self):
        runner = AgentRunner({"worker": self._make_mock_spec()})
        self.assertIsNone(runner.get_output("nonexistent"))

        runner._results["abc"] = AgentResult(
            agent_id="abc",
            agent_name="worker",
            status=AgentStatus.COMPLETED,
            output="done",
        )
        result = runner.get_output("abc")
        self.assertEqual(result.output, "done")

    async def test_catalog_includes_local_and_remote(self):
        local_spec = self._make_mock_spec("local-agent")
        mock_client = AsyncMock()
        mock_card = {"name": "remote-agent", "description": "A remote agent"}
        runner = AgentRunner(
            local_agents={"local-agent": local_spec},
            remote_agents={"remote-agent": (mock_client, mock_card)},
        )
        cat = runner.catalog()
        self.assertIn("local-agent", cat)
        self.assertIn("remote-agent", cat)
        self.assertEqual(cat["remote-agent"], "A remote agent")

    async def test_launch_routes_to_remote(self):
        mock_client = AsyncMock()
        mock_client.send_message_only = AsyncMock(return_value="remote-task-123")
        mock_card = {"name": "remote", "description": "Remote agent"}
        runner = AgentRunner(remote_agents={"remote": (mock_client, mock_card)})

        # Background launch for remote
        result = await runner.launch("remote", "hello", run_in_background=True)
        self.assertEqual(result.status, AgentStatus.RUNNING)
        self.assertEqual(result._remote_task_id, "remote-task-123")
        mock_client.send_message_only.assert_awaited_once_with("hello")


if __name__ == "__main__":
    unittest.main()
