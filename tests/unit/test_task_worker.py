import shutil
import tempfile
import unittest
from pathlib import Path

from agentic_patterns.core.tasks.models import Task
from agentic_patterns.core.tasks.state import TaskState
from agentic_patterns.core.tasks.store import TaskStoreJson
from agentic_patterns.core.tasks.worker import Worker
from agentic_patterns.testing import ModelMock


class TestWorker(unittest.IsolatedAsyncioTestCase):
    """Tests for the task Worker."""

    def setUp(self) -> None:
        self._temp_dir = Path(tempfile.mkdtemp())
        self.store = TaskStoreJson(directory=self._temp_dir)

    def tearDown(self) -> None:
        shutil.rmtree(self._temp_dir)

    async def test_execute_success(self) -> None:
        """Worker completes a task with the agent's response."""
        task = Task(input="What is 2+2?")
        await self.store.create(task)
        worker = Worker(self.store, model=ModelMock(responses=["4"]))
        await worker.execute(task.id)
        got = await self.store.get(task.id)
        self.assertEqual(got.state, TaskState.COMPLETED)
        self.assertEqual(got.result, "4")

    async def test_execute_failure(self) -> None:
        """Worker marks task as failed when agent raises."""
        task = Task(input="fail please")
        await self.store.create(task)
        worker = Worker(self.store, model=ModelMock(responses=[RuntimeError("boom")]))
        with self.assertLogs(
            "agentic_patterns.core.tasks.worker", level="ERROR"
        ) as logs:
            await worker.execute(task.id)
        self.assertTrue(any("boom" in msg for msg in logs.output))
        got = await self.store.get(task.id)
        self.assertEqual(got.state, TaskState.FAILED)
        self.assertIn("boom", got.error)

    async def test_execute_nonexistent(self) -> None:
        """Worker silently returns when task is not found."""
        worker = Worker(self.store, model=ModelMock(responses=["ignored"]))
        with self.assertLogs(
            "agentic_patterns.core.tasks.worker", level="WARNING"
        ) as logs:
            await worker.execute("nonexistent-id")
        self.assertTrue(any("not found" in msg for msg in logs.output))

    async def test_execute_records_events(self) -> None:
        """Worker records state-change events during execution."""
        task = Task(input="hello")
        await self.store.create(task)
        worker = Worker(self.store, model=ModelMock(responses=["world"]))
        await worker.execute(task.id)
        got = await self.store.get(task.id)
        states = [e.payload.get("state") for e in got.events]
        self.assertIn("running", states)
        self.assertIn("completed", states)


if __name__ == "__main__":
    unittest.main()
