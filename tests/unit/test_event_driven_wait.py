import asyncio
import unittest

from pydantic_ai.messages import ToolCallPart

from agentic_patterns.core.agents.orchestrator import (
    AgentSpec,
    OrchestratorAgent,
    _collect_status,
)
from agentic_patterns.core.tasks.broker import TaskBroker
from agentic_patterns.core.tasks.models import Task
from agentic_patterns.core.tasks.state import TaskState
from agentic_patterns.core.tasks.store import TaskStoreMemory
from agentic_patterns.testing import ModelMock


class TestEventDrivenWait(unittest.IsolatedAsyncioTestCase):
    async def test_broker_signals_activity_on_completion(self) -> None:
        """Broker sets the activity event when a task completes."""
        activity = asyncio.Event()
        store = TaskStoreMemory()
        model = ModelMock(responses=["the answer"])
        async with TaskBroker(
            store=store, model=model, poll_interval=0.05, activity=activity
        ) as broker:
            await broker.submit("question")
            await asyncio.wait_for(activity.wait(), timeout=5)
        self.assertTrue(activity.is_set())

    async def test_broker_signals_activity_on_failure(self) -> None:
        """Broker sets the activity event when a task fails."""
        activity = asyncio.Event()
        store = TaskStoreMemory()
        model = ModelMock(responses=[RuntimeError("boom")])
        with self.assertLogs("agentic_patterns.core.tasks", level="ERROR"):
            async with TaskBroker(
                store=store, model=model, poll_interval=0.05, activity=activity
            ) as broker:
                task_id = await broker.submit("fail")
                await asyncio.wait_for(activity.wait(), timeout=5)
                task = await broker.poll(task_id)
        self.assertEqual(task.state, TaskState.FAILED)

    async def test_broker_without_activity_completes_normally(self) -> None:
        """Broker without activity event does not crash."""
        store = TaskStoreMemory()
        model = ModelMock(responses=["result"])
        async with TaskBroker(store=store, model=model, poll_interval=0.05) as broker:
            task_id = await broker.submit("question")
            task = await broker.wait(task_id)
        self.assertEqual(task.state, TaskState.COMPLETED)

    async def test_collect_status_all_terminal(self) -> None:
        """_collect_status returns all_terminal=True when every task is done."""
        store = TaskStoreMemory()
        task = Task(input="test", metadata={"agent_name": "calc"})
        await store.create(task)
        await store.update_state(task.id, TaskState.COMPLETED, result="42")

        broker = TaskBroker(store=store, poll_interval=10)
        lines, all_terminal = await _collect_status(broker, [task.id])
        self.assertTrue(all_terminal)
        self.assertIn("completed", lines[0])
        self.assertIn("42", lines[0])

    async def test_collect_status_mixed_states(self) -> None:
        """_collect_status returns all_terminal=False when some tasks are pending."""
        store = TaskStoreMemory()
        done = Task(input="done", metadata={"agent_name": "a"})
        pending = Task(input="pending", metadata={"agent_name": "b"})
        await store.create(done)
        await store.create(pending)
        await store.update_state(done.id, TaskState.COMPLETED, result="ok")

        broker = TaskBroker(store=store, poll_interval=10)
        lines, all_terminal = await _collect_status(broker, [done.id, pending.id])
        self.assertFalse(all_terminal)
        self.assertEqual(len(lines), 2)

    async def test_collect_status_failed_task(self) -> None:
        """_collect_status includes error message for failed tasks."""
        store = TaskStoreMemory()
        task = Task(input="fail", metadata={"agent_name": "broken"})
        await store.create(task)
        await store.update_state(task.id, TaskState.FAILED, error="something broke")

        broker = TaskBroker(store=store, poll_interval=10)
        lines, all_terminal = await _collect_status(broker, [task.id])
        self.assertTrue(all_terminal)
        self.assertIn("failed", lines[0])
        self.assertIn("something broke", lines[0])

    async def test_wait_tool_returns_completed_results(self) -> None:
        """Orchestrator: submit_task then wait returns completed task results."""
        sub_model = ModelMock(responses=["42"])
        sub_spec = AgentSpec(name="calc", description="Calculator", model=sub_model)

        orch_model = ModelMock(
            responses=[
                ToolCallPart(
                    tool_name="submit_task",
                    args={"agent_name": "calc", "prompt": "2+2"},
                ),
                ToolCallPart(tool_name="wait", args={}),
                "Done",
            ]
        )
        spec = AgentSpec(name="orch", model=orch_model, sub_agents=[sub_spec])
        async with OrchestratorAgent(spec) as agent:
            result = await agent.run("test")
        self.assertIn("Done", result.output)

    async def test_wait_tool_timeout(self) -> None:
        """Orchestrator: wait with short timeout returns without hanging."""
        sub_model = ModelMock(responses=["result"], sleep_time=10)
        sub_spec = AgentSpec(name="slow", description="Slow agent", model=sub_model)

        orch_model = ModelMock(
            responses=[
                ToolCallPart(
                    tool_name="submit_task",
                    args={"agent_name": "slow", "prompt": "work"},
                ),
                ToolCallPart(tool_name="wait", args={"timeout": 1}),
                "Timed out",
            ]
        )
        spec = AgentSpec(name="orch", model=orch_model, sub_agents=[sub_spec])
        async with OrchestratorAgent(spec) as agent:
            result = await agent.run("test")
        self.assertIn("Timed out", result.output)


if __name__ == "__main__":
    unittest.main()
