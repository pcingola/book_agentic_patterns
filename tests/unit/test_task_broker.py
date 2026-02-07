import shutil
import tempfile
import unittest
from pathlib import Path

from agentic_patterns.core.tasks.broker import TaskBroker
from agentic_patterns.core.tasks.models import Task
from agentic_patterns.core.tasks.state import TaskState
from agentic_patterns.core.tasks.store import TaskStoreJson
from agentic_patterns.testing import ModelMock


class TestTaskBroker(unittest.IsolatedAsyncioTestCase):
    """Tests for the TaskBroker."""

    def setUp(self) -> None:
        self._temp_dir = Path(tempfile.mkdtemp())
        self.store = TaskStoreJson(directory=self._temp_dir)

    def tearDown(self) -> None:
        shutil.rmtree(self._temp_dir)

    async def test_submit_creates_task(self) -> None:
        """Submit creates a pending task and returns its id."""
        broker = TaskBroker(store=self.store, poll_interval=10)
        task_id = await broker.submit("hello")
        task = await self.store.get(task_id)
        self.assertIsNotNone(task)
        self.assertEqual(task.state, TaskState.PENDING)
        self.assertEqual(task.input, "hello")

    async def test_poll_returns_task(self) -> None:
        """Poll returns the current task state."""
        broker = TaskBroker(store=self.store, poll_interval=10)
        task_id = await broker.submit("test")
        task = await broker.poll(task_id)
        self.assertIsNotNone(task)
        self.assertEqual(task.state, TaskState.PENDING)

    async def test_cancel_pending_task(self) -> None:
        """Cancelling a pending task sets state to CANCELLED."""
        broker = TaskBroker(store=self.store, poll_interval=10)
        task_id = await broker.submit("to cancel")
        task = await broker.cancel(task_id)
        self.assertEqual(task.state, TaskState.CANCELLED)

    async def test_cancel_terminal_task_is_noop(self) -> None:
        """Cancelling a completed task has no effect."""
        task = Task(input="done")
        await self.store.create(task)
        await self.store.update_state(task.id, TaskState.COMPLETED, result="ok")
        broker = TaskBroker(store=self.store, poll_interval=10)
        result = await broker.cancel(task.id)
        self.assertEqual(result.state, TaskState.COMPLETED)

    async def test_submit_and_wait(self) -> None:
        """End-to-end: submit, dispatch loop processes, wait returns completed task."""
        model = ModelMock(responses=["the answer"])
        async with TaskBroker(store=self.store, model=model, poll_interval=0.05) as broker:
            task_id = await broker.submit("question")
            task = await broker.wait(task_id)
            self.assertEqual(task.state, TaskState.COMPLETED)
            self.assertEqual(task.result, "the answer")

    async def test_notify_callback_fires(self) -> None:
        """Registered callback fires on matching state change."""
        received = []

        async def on_complete(task: Task) -> None:
            received.append(task)

        model = ModelMock(responses=["result"])
        async with TaskBroker(store=self.store, model=model, poll_interval=0.05) as broker:
            task_id = await broker.submit("notify me")
            await broker.notify(task_id, {TaskState.COMPLETED}, on_complete)
            await broker.wait(task_id)
            self.assertEqual(len(received), 1)
            self.assertEqual(received[0].state, TaskState.COMPLETED)

    async def test_submit_metadata_stored(self) -> None:
        """Metadata passed to submit is stored on the task."""
        broker = TaskBroker(store=self.store, poll_interval=10)
        task_id = await broker.submit("test", system_prompt="Be concise.")
        task = await self.store.get(task_id)
        self.assertEqual(task.metadata["system_prompt"], "Be concise.")


if __name__ == "__main__":
    unittest.main()
