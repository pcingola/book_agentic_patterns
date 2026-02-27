"""Unit tests for the Task model."""

import json
import unittest

from agentic_patterns.core.tasks.task import Task
from agentic_patterns.core.tasks.task_status import TaskStatus


class TestTask(unittest.TestCase):
    def test_defaults(self):
        task = Task(id="1", subject="Do something", description="Details here")
        self.assertEqual(task.status, TaskStatus.PENDING)
        self.assertIsNone(task.active_form)
        self.assertIsNone(task.owner)
        self.assertEqual(task.blocks, [])
        self.assertEqual(task.blocked_by, [])
        self.assertEqual(task.metadata, {})

    def test_json_serialization_uses_camel_case(self):
        task = Task(
            id="5",
            subject="Test",
            description="Desc",
            active_form="Testing",
            blocked_by=["1", "2"],
        )
        data = json.loads(task.model_dump_json_file())
        self.assertIn("activeForm", data)
        self.assertIn("blockedBy", data)
        self.assertEqual(data["activeForm"], "Testing")
        self.assertEqual(data["blockedBy"], ["1", "2"])

    def test_from_json_file_roundtrip(self):
        original = Task(
            id="3",
            subject="Build",
            description="Build the thing",
            active_form="Building",
            owner="dev",
            blocks=["4"],
            blocked_by=["1"],
            metadata={"priority": "high"},
        )
        json_str = original.model_dump_json_file()
        restored = Task.from_json_file(json_str)
        self.assertEqual(restored.id, "3")
        self.assertEqual(restored.subject, "Build")
        self.assertEqual(restored.active_form, "Building")
        self.assertEqual(restored.owner, "dev")
        self.assertEqual(restored.blocks, ["4"])
        self.assertEqual(restored.blocked_by, ["1"])
        self.assertEqual(restored.metadata, {"priority": "high"})

    def test_str(self):
        task = Task(
            id="1", subject="Test", description="Desc", owner="dev", blocked_by=["2"]
        )
        s = str(task)
        self.assertIn("#1", s)
        self.assertIn("pending", s)
        self.assertIn("Test", s)
        self.assertIn("owner: dev", s)
        self.assertIn("blockedBy", s)


if __name__ == "__main__":
    unittest.main()
