import shutil
import tempfile
import unittest
from pathlib import Path

from agentic_patterns.core.tasks.models import EventType, Task, TaskEvent
from agentic_patterns.core.tasks.state import TaskState
from agentic_patterns.core.tasks.store import TaskStoreJson


class TestTaskStoreJson(unittest.IsolatedAsyncioTestCase):
    """Tests for TaskStoreJson file-backed storage."""

    def setUp(self) -> None:
        self._temp_dir = Path(tempfile.mkdtemp())
        self.store = TaskStoreJson(directory=self._temp_dir)

    def tearDown(self) -> None:
        shutil.rmtree(self._temp_dir)

    async def test_create_and_get(self) -> None:
        """Created task can be retrieved by id."""
        task = Task(input="hello")
        await self.store.create(task)
        got = await self.store.get(task.id)
        self.assertEqual(got.id, task.id)
        self.assertEqual(got.input, "hello")
        self.assertEqual(got.state, TaskState.PENDING)

    async def test_get_nonexistent(self) -> None:
        """Getting a nonexistent task returns None."""
        self.assertIsNone(await self.store.get("nonexistent-id"))

    async def test_update_state(self) -> None:
        """State update persists correctly."""
        task = Task(input="test")
        await self.store.create(task)
        updated = await self.store.update_state(task.id, TaskState.RUNNING)
        self.assertEqual(updated.state, TaskState.RUNNING)
        got = await self.store.get(task.id)
        self.assertEqual(got.state, TaskState.RUNNING)

    async def test_update_state_with_result(self) -> None:
        """State update with result persists both fields."""
        task = Task(input="test")
        await self.store.create(task)
        await self.store.update_state(task.id, TaskState.COMPLETED, result="done")
        got = await self.store.get(task.id)
        self.assertEqual(got.state, TaskState.COMPLETED)
        self.assertEqual(got.result, "done")

    async def test_update_state_with_error(self) -> None:
        """State update with error persists both fields."""
        task = Task(input="test")
        await self.store.create(task)
        await self.store.update_state(task.id, TaskState.FAILED, error="oops")
        got = await self.store.get(task.id)
        self.assertEqual(got.state, TaskState.FAILED)
        self.assertEqual(got.error, "oops")

    async def test_update_state_nonexistent(self) -> None:
        """Updating a nonexistent task returns None."""
        self.assertIsNone(await self.store.update_state("bad-id", TaskState.RUNNING))

    async def test_list_by_state(self) -> None:
        """Tasks are filtered correctly by state."""
        t1 = Task(input="one")
        t2 = Task(input="two")
        await self.store.create(t1)
        await self.store.create(t2)
        await self.store.update_state(t2.id, TaskState.RUNNING)
        pending = await self.store.list_by_state(TaskState.PENDING)
        running = await self.store.list_by_state(TaskState.RUNNING)
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0].id, t1.id)
        self.assertEqual(len(running), 1)
        self.assertEqual(running[0].id, t2.id)

    async def test_next_pending(self) -> None:
        """Returns the oldest pending task."""
        t1 = Task(input="first")
        t2 = Task(input="second")
        await self.store.create(t1)
        await self.store.create(t2)
        nxt = await self.store.next_pending()
        self.assertEqual(nxt.id, t1.id)

    async def test_next_pending_empty(self) -> None:
        """Returns None when no pending tasks exist."""
        self.assertIsNone(await self.store.next_pending())

    async def test_add_event(self) -> None:
        """Events are appended to the task."""
        task = Task(input="test")
        await self.store.create(task)
        event = TaskEvent(
            task_id=task.id, event_type=EventType.LOG, payload={"msg": "hi"}
        )
        await self.store.add_event(task.id, event)
        got = await self.store.get(task.id)
        self.assertEqual(len(got.events), 1)
        self.assertEqual(got.events[0].event_type, EventType.LOG)


if __name__ == "__main__":
    unittest.main()
