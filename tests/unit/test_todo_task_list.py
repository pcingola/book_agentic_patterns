"""Unit tests for the Todo TaskList model."""

import unittest
from typing import cast

from agentic_patterns.toolkits.todo.models import Task, TaskList, TaskState


class TestTaskListModel(unittest.TestCase):
    """Test cases for the TaskList model."""

    def setUp(self):
        self.task_list = TaskList()
        self.task1 = self.task_list.add_task("Task 1")
        self.task2 = self.task_list.add_task("Task 2")
        task1_subtasks = cast(TaskList, self.task1.subtasks)
        self.subtask1 = task1_subtasks.add_task("Subtask 1.1")

    def test_add_task(self):
        task_list = TaskList()
        task = task_list.add_task("New task")
        self.assertEqual(len(task_list.tasks), 1)
        self.assertEqual(task_list.tasks[0], task)
        self.assertEqual(task.description, "New task")
        self.assertEqual(task.parent, task_list)

    def test_get_task_by_id(self):
        self.assertEqual(self.task_list.get_task_by_id("1"), self.task1)
        self.assertEqual(self.task_list.get_task_by_id("2"), self.task2)
        self.assertEqual(self.task_list.get_task_by_id("1.1"), self.subtask1)
        self.assertIsNone(self.task_list.get_task_by_id("3"))
        self.assertIsNone(self.task_list.get_task_by_id("1.2"))

    def test_update_task_state(self):
        self.task_list.update_task_state("1", TaskState.IN_PROGRESS)
        self.assertEqual(self.task1.state, TaskState.IN_PROGRESS)

        self.task_list.update_task_state("1.1", TaskState.COMPLETED)
        self.assertEqual(self.subtask1.state, TaskState.COMPLETED)

        result = self.task_list.update_task_state("3", TaskState.FAILED)
        self.assertFalse(result)

    def test_to_markdown(self):
        markdown = self.task_list.to_markdown()
        self.assertIn("# Task List", markdown)
        self.assertIn("- [ ] 1: Task 1", markdown)
        self.assertIn("- [ ] 2: Task 2", markdown)
        self.assertIn("- [ ] 1.1: Subtask 1.1", markdown)

    def test_delete_task_and_renumber(self):
        task_list = TaskList()
        for i in range(1, 11):
            task_list.add_task(f"Main Task {i}")

        task1 = task_list.get_task_by_id("1")
        assert task1 is not None
        assert task1.subtasks is not None
        subtask1 = task1.subtasks.add_task("Subtask 1.1")

        assert subtask1.subtasks is not None
        subtask1.subtasks.add_task("Nested Task 1.1.1")
        subtask1.subtasks.add_task("Nested Task 1.1.2")

        markdown = task_list.to_markdown()
        self.assertIn("- [ ] 1.1.1: Nested Task 1.1.1", markdown)
        self.assertIn("- [ ] 1.1.2: Nested Task 1.1.2", markdown)

        task_list.delete("1.1.1")

        updated_markdown = task_list.to_markdown()
        self.assertIn("- [ ] 1.1.1: Nested Task 1.1.2", updated_markdown)
        self.assertNotIn("- [ ] 1.1.2:", updated_markdown)

        updated_subsubtask = subtask1.subtasks.get_task_by_id("1")
        assert updated_subsubtask is not None
        self.assertEqual(updated_subsubtask.description, "Nested Task 1.1.2")
        self.assertEqual(updated_subsubtask.get_id("1.1"), "1.1.1")

    def test_delete_method(self):
        task_list = TaskList()
        task1 = task_list.add_task("Task 1")
        task_list.add_task("Task 2")
        task_list.add_task("Task 3")

        subtask1 = task1.add_task("Subtask 1.1")
        task1.add_task("Subtask 1.2")
        subtask1.add_task("Nested 1.1.1")

        # Delete top-level task
        self.assertTrue(task_list.delete("2"))
        self.assertEqual(len(task_list.tasks), 2)
        self.assertEqual(task_list.tasks[0].description, "Task 1")
        self.assertEqual(task_list.tasks[1].description, "Task 3")
        self.assertEqual(task_list.tasks[1].get_id(), "2")

        # Delete subtask
        self.assertTrue(task_list.delete("1.2"))
        assert task1.subtasks is not None
        self.assertEqual(len(task1.subtasks.tasks), 1)
        self.assertEqual(task1.subtasks.tasks[0].description, "Subtask 1.1")

        # Delete nested subtask
        self.assertTrue(task_list.delete("1.1.1"))
        assert subtask1.subtasks is not None
        self.assertEqual(len(subtask1.subtasks.tasks), 0)

        # Non-existent tasks
        self.assertFalse(task_list.delete("4"))
        self.assertFalse(task_list.delete("1.3"))
        self.assertFalse(task_list.delete("1.1.2"))

    def test_task_list_equality(self):
        task_list1 = TaskList()
        task_list2 = TaskList()
        self.assertEqual(task_list1, task_list2)

        task1_1 = task_list1.add_task("Task 1")
        task_list1.add_task("Task 2")
        task2_1 = task_list2.add_task("Task 1")
        task_list2.add_task("Task 2")
        self.assertEqual(task_list1, task_list2)

        task1_1.add_task("Subtask 1.1")
        self.assertNotEqual(task_list1, task_list2)

        task2_1.add_task("Subtask 1.1")
        self.assertEqual(task_list1, task_list2)

        # parent_task references don't cause infinite recursion
        task = Task(description="Parent")
        task_list3 = TaskList(parent_task=task)
        task_list4 = TaskList()
        self.assertEqual(task_list3, task_list4)

        task_list3.add_task("Task in list 3")
        self.assertNotEqual(task_list3, task_list4)

    def test_delete_subtask_specific(self):
        task_list = TaskList()
        parent_task = task_list.add_task("Parent Task")
        parent_task.add_task("Subtask to keep")
        subtask2 = parent_task.add_task("Subtask to delete")

        assert parent_task.subtasks is not None
        self.assertEqual(len(parent_task.subtasks.tasks), 2)

        subtask2_id = subtask2.get_id("1")
        success = task_list.delete(subtask2_id)

        self.assertTrue(success)
        self.assertEqual(len(parent_task.subtasks.tasks), 1)
        self.assertEqual(parent_task.subtasks.tasks[0].description, "Subtask to keep")
        self.assertIsNone(task_list.get_task_by_id(subtask2_id))


if __name__ == "__main__":
    unittest.main()
