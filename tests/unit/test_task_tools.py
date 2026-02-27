"""Unit tests for the task tool functions."""

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

from agentic_patterns.core.tasks.task_list import TaskList
from agentic_patterns.core.tasks.task_tools import get_task_tools


class TestTaskTools(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.task_list = TaskList(self.tmp_dir / "tasks")
        tools = get_task_tools(self.task_list)
        self.task_create = tools[0]
        self.task_get = tools[1]
        self.task_list_all = tools[2]
        self.task_update = tools[3]
        self.ctx = AsyncMock()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    async def test_create_and_get(self):
        result = await self.task_create(self.ctx, "Do work", "Details")
        self.assertIn("Task #1 created", result)

        result = await self.task_get(self.ctx, "1")
        self.assertIn("Do work", result)
        self.assertIn("Details", result)

    async def test_get_not_found(self):
        result = await self.task_get(self.ctx, "999")
        self.assertIn("not found", result)

    async def test_list_all(self):
        await self.task_create(self.ctx, "First", "Desc 1")
        await self.task_create(self.ctx, "Second", "Desc 2")
        result = await self.task_list_all(self.ctx)
        self.assertIn("First", result)
        self.assertIn("Second", result)

    async def test_list_all_empty(self):
        result = await self.task_list_all(self.ctx)
        self.assertEqual(result, "No tasks.")

    async def test_update_status(self):
        await self.task_create(self.ctx, "Work", "Details")
        result = await self.task_update(self.ctx, "1", status="in_progress")
        self.assertIn("Updated task #1", result)
        self.assertIn("status=in_progress", result)

    async def test_update_not_found(self):
        result = await self.task_update(self.ctx, "999", subject="Nope")
        self.assertIn("not found", result)

    async def test_update_blocked_task(self):
        await self.task_create(self.ctx, "Blocker", "Desc")
        await self.task_create(self.ctx, "Blocked", "Desc")
        await self.task_update(self.ctx, "2", add_blocked_by=["1"])
        result = await self.task_update(self.ctx, "2", status="in_progress")
        self.assertIn("blocked", result)

    async def test_delete(self):
        await self.task_create(self.ctx, "To delete", "Desc")
        result = await self.task_update(self.ctx, "1", status="deleted")
        self.assertIn("deleted", result)


if __name__ == "__main__":
    unittest.main()
