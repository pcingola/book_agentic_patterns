"""Unit tests for the Todo Task model."""

import unittest
from typing import cast

from agentic_patterns.mcp.todo.models import Task, TaskList, TaskState


class TestTaskModel(unittest.TestCase):
    """Test cases for the Task model."""

    def setUp(self):
        self.task_list = TaskList()
        self.task = Task(description="Test task")

    def test_task_initialization(self):
        self.assertEqual(self.task.description, "Test task")
        self.assertEqual(self.task.state, TaskState.PENDING)
        self.assertIsNone(self.task.parent)
        self.assertIsNotNone(self.task.subtasks)
        self.assertIsInstance(self.task.subtasks, TaskList)
        task_subtasks = cast(TaskList, self.task.subtasks)
        self.assertEqual(len(task_subtasks.tasks), 0)

    def test_task_id_generation(self):
        task1 = self.task_list.add_task("Task 1")
        task2 = self.task_list.add_task("Task 2")

        self.assertEqual(task1.get_id(), "1")
        self.assertEqual(task2.get_id(), "2")

        task_list1 = cast(TaskList, task1.subtasks)
        subtask1 = task_list1.add_task("Subtask 1.1")
        subtask2 = task_list1.add_task("Subtask 1.2")

        self.assertEqual(subtask1.get_id("1"), "1.1")
        self.assertEqual(subtask2.get_id("1"), "1.2")

        subtask_list = cast(TaskList, subtask1.subtasks)
        subsubtask = subtask_list.add_task("Subsubtask 1.1.1")
        self.assertEqual(subsubtask.get_id("1.1"), "1.1.1")

    def test_to_markdown(self):
        task = self.task_list.add_task("Main task")
        task_subtasks = cast(TaskList, task.subtasks)
        subtask1 = task_subtasks.add_task("Subtask 1")
        task_subtasks.add_task("Subtask 2")
        subtask1.state = TaskState.COMPLETED

        markdown = task.to_markdown()
        self.assertIn("- [ ] 1: Main task", markdown)
        self.assertIn("- [x] 1.1: Subtask 1", markdown)
        self.assertIn("- [ ] 1.2: Subtask 2", markdown)

    def test_task_equality(self):
        task1 = Task(description="Test task")
        task2 = Task(description="Test task")
        self.assertEqual(task1, task2)

        task2.state = TaskState.COMPLETED
        self.assertNotEqual(task1, task2)

        task2.state = TaskState.PENDING
        task1.add_task("Subtask 1")
        self.assertNotEqual(task1, task2)

        task2.add_task("Subtask 1")
        self.assertEqual(task1, task2)

        # Parent references don't cause infinite recursion
        task_list = TaskList()
        task3 = task_list.add_task("Parent task")
        task3.add_task("Subtask 1")
        task4 = Task(description="Parent task")
        task4.add_task("Subtask 1")
        self.assertEqual(task3, task4)


if __name__ == "__main__":
    unittest.main()
