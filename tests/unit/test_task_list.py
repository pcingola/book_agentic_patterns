"""Unit tests for the TaskList storage and operations."""

import shutil
import tempfile
import unittest
from pathlib import Path

from agentic_patterns.core.tasks.task_list import TaskList
from agentic_patterns.core.tasks.task_status import TaskStatus


class TestTaskList(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.task_list = TaskList(self.tmp_dir / "tasks")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    async def test_create_assigns_incrementing_ids(self):
        t1 = await self.task_list.create("First", "First task")
        t2 = await self.task_list.create("Second", "Second task")
        t3 = await self.task_list.create("Third", "Third task")
        self.assertEqual(t1.id, "1")
        self.assertEqual(t2.id, "2")
        self.assertEqual(t3.id, "3")
        self.assertEqual(t1.status, TaskStatus.PENDING)

    async def test_get_task(self):
        created = await self.task_list.create("Test", "Desc", active_form="Testing")
        fetched = await self.task_list.get(created.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.subject, "Test")
        self.assertEqual(fetched.active_form, "Testing")

    async def test_get_nonexistent_returns_none(self):
        result = await self.task_list.get("999")
        self.assertIsNone(result)

    async def test_list_all(self):
        await self.task_list.create("A", "desc A")
        await self.task_list.create("B", "desc B")
        tasks = await self.task_list.list_all()
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0].subject, "A")
        self.assertEqual(tasks[1].subject, "B")
        # list_all strips metadata
        self.assertEqual(tasks[0].metadata, {})

    async def test_update_status(self):
        t = await self.task_list.create("Work", "Do work")
        updated = await self.task_list.update(t.id, status=TaskStatus.IN_PROGRESS)
        self.assertEqual(updated.status, TaskStatus.IN_PROGRESS)
        updated = await self.task_list.update(t.id, status=TaskStatus.COMPLETED)
        self.assertEqual(updated.status, TaskStatus.COMPLETED)

    async def test_update_nonexistent_returns_none(self):
        result = await self.task_list.update("999", subject="Nope")
        self.assertIsNone(result)

    async def test_delete_removes_file(self):
        t = await self.task_list.create("Delete me", "Desc")
        result = await self.task_list.update(t.id, status=TaskStatus.DELETED)
        self.assertEqual(result.status, TaskStatus.DELETED)
        self.assertIsNone(await self.task_list.get(t.id))

    async def test_metadata_merge(self):
        t = await self.task_list.create("Meta", "Desc", metadata={"a": 1, "b": 2})
        # Add key, update key, delete key
        updated = await self.task_list.update(
            t.id, metadata={"b": 99, "c": 3, "a": None}
        )
        self.assertNotIn("a", updated.metadata)
        self.assertEqual(updated.metadata["b"], 99)
        self.assertEqual(updated.metadata["c"], 3)

    async def test_bidirectional_dependency_add_blocked_by(self):
        t1 = await self.task_list.create("Prereq", "Prereq task")
        t2 = await self.task_list.create("Dependent", "Depends on prereq")
        await self.task_list.update(t2.id, add_blocked_by=[t1.id])

        # t2 should have t1 in blocked_by
        t2_refreshed = await self.task_list.get(t2.id)
        self.assertIn(t1.id, t2_refreshed.blocked_by)

        # t1 should have t2 in blocks (bidirectional sync)
        t1_refreshed = await self.task_list.get(t1.id)
        self.assertIn(t2.id, t1_refreshed.blocks)

    async def test_bidirectional_dependency_add_blocks(self):
        t1 = await self.task_list.create("Prereq", "Prereq task")
        t2 = await self.task_list.create("Dependent", "Depends on prereq")
        await self.task_list.update(t1.id, add_blocks=[t2.id])

        t1_refreshed = await self.task_list.get(t1.id)
        self.assertIn(t2.id, t1_refreshed.blocks)

        t2_refreshed = await self.task_list.get(t2.id)
        self.assertIn(t1.id, t2_refreshed.blocked_by)

    async def test_blocked_task_cannot_start(self):
        t1 = await self.task_list.create("Blocker", "Must finish first")
        t2 = await self.task_list.create("Blocked", "Waiting")
        await self.task_list.update(t2.id, add_blocked_by=[t1.id])

        with self.assertRaises(ValueError):
            await self.task_list.update(t2.id, status=TaskStatus.IN_PROGRESS)

    async def test_unblocked_after_blocker_completes(self):
        t1 = await self.task_list.create("Blocker", "Must finish first")
        t2 = await self.task_list.create("Blocked", "Waiting")
        await self.task_list.update(t2.id, add_blocked_by=[t1.id])

        # Complete the blocker
        await self.task_list.update(t1.id, status=TaskStatus.IN_PROGRESS)
        await self.task_list.update(t1.id, status=TaskStatus.COMPLETED)

        # Now t2 should be able to start
        result = await self.task_list.update(t2.id, status=TaskStatus.IN_PROGRESS)
        self.assertEqual(result.status, TaskStatus.IN_PROGRESS)

    async def test_diamond_dependency(self):
        """Diamond: t1, t2 -> t3 -> t4, t5 -> t6"""
        t1 = await self.task_list.create("Investigate A", "Desc")
        t2 = await self.task_list.create("Investigate B", "Desc")
        t3 = await self.task_list.create("Plan", "Desc")
        await self.task_list.update(t3.id, add_blocked_by=[t1.id, t2.id])

        # t3 blocked by both t1 and t2
        with self.assertRaises(ValueError):
            await self.task_list.update(t3.id, status=TaskStatus.IN_PROGRESS)

        # Complete t1 only -- still blocked
        await self.task_list.update(t1.id, status=TaskStatus.IN_PROGRESS)
        await self.task_list.update(t1.id, status=TaskStatus.COMPLETED)
        with self.assertRaises(ValueError):
            await self.task_list.update(t3.id, status=TaskStatus.IN_PROGRESS)

        # Complete t2 -- now unblocked
        await self.task_list.update(t2.id, status=TaskStatus.IN_PROGRESS)
        await self.task_list.update(t2.id, status=TaskStatus.COMPLETED)
        result = await self.task_list.update(t3.id, status=TaskStatus.IN_PROGRESS)
        self.assertEqual(result.status, TaskStatus.IN_PROGRESS)

    async def test_next_available_skips_blocked_and_non_pending(self):
        t1 = await self.task_list.create("Blocker", "Desc")
        t2 = await self.task_list.create("Blocked", "Desc")
        t3 = await self.task_list.create("Free", "Desc")
        await self.task_list.update(t2.id, add_blocked_by=[t1.id])
        await self.task_list.update(t1.id, status=TaskStatus.IN_PROGRESS)

        # t1 is in_progress, t2 is blocked -> next available is t3
        nxt = await self.task_list.next_available()
        self.assertEqual(nxt.id, t3.id)

    async def test_next_available_with_owner_filter(self):
        await self.task_list.create("Task A", "Desc")
        t2 = await self.task_list.create("Task B", "Desc")
        await self.task_list.update(t2.id, owner="backend")

        nxt = await self.task_list.next_available(owner="backend")
        self.assertEqual(nxt.id, t2.id)

    async def test_next_available_returns_none_when_empty(self):
        self.assertIsNone(await self.task_list.next_available())

    async def test_file_persistence(self):
        """Tasks survive re-instantiation of TaskList."""
        await self.task_list.create(
            "Persistent", "Should survive", active_form="Working"
        )
        # Create a new TaskList pointing to the same directory
        new_list = TaskList(self.task_list.base_dir)
        task = await new_list.get("1")
        self.assertIsNotNone(task)
        self.assertEqual(task.subject, "Persistent")
        self.assertEqual(task.active_form, "Working")


if __name__ == "__main__":
    unittest.main()
