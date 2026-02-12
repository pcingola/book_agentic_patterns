"""Unit tests for the TodoItem model."""

import unittest
from typing import cast

from agentic_patterns.toolkits.todo.models import TodoItem, TodoList, TodoState


class TestTodoItemModel(unittest.TestCase):
    """Test cases for the TodoItem model."""

    def setUp(self):
        self.todo_list = TodoList()
        self.item = TodoItem(description="Test item")

    def test_item_initialization(self):
        self.assertEqual(self.item.description, "Test item")
        self.assertEqual(self.item.state, TodoState.PENDING)
        self.assertIsNone(self.item.parent)
        self.assertIsNotNone(self.item.subtasks)
        self.assertIsInstance(self.item.subtasks, TodoList)
        item_subtasks = cast(TodoList, self.item.subtasks)
        self.assertEqual(len(item_subtasks.items), 0)

    def test_item_id_generation(self):
        item1 = self.todo_list.add_item("Item 1")
        item2 = self.todo_list.add_item("Item 2")

        self.assertEqual(item1.get_id(), "1")
        self.assertEqual(item2.get_id(), "2")

        item_list1 = cast(TodoList, item1.subtasks)
        sub_item1 = item_list1.add_item("Sub-item 1.1")
        sub_item2 = item_list1.add_item("Sub-item 1.2")

        self.assertEqual(sub_item1.get_id("1"), "1.1")
        self.assertEqual(sub_item2.get_id("1"), "1.2")

        sub_item_list = cast(TodoList, sub_item1.subtasks)
        sub_sub_item = sub_item_list.add_item("Sub-sub-item 1.1.1")
        self.assertEqual(sub_sub_item.get_id("1.1"), "1.1.1")

    def test_to_markdown(self):
        item = self.todo_list.add_item("Main item")
        item_subtasks = cast(TodoList, item.subtasks)
        sub_item1 = item_subtasks.add_item("Sub-item 1")
        item_subtasks.add_item("Sub-item 2")
        sub_item1.state = TodoState.COMPLETED

        markdown = item.to_markdown()
        self.assertIn("- [ ] 1: Main item", markdown)
        self.assertIn("- [x] 1.1: Sub-item 1", markdown)
        self.assertIn("- [ ] 1.2: Sub-item 2", markdown)

    def test_item_equality(self):
        item1 = TodoItem(description="Test item")
        item2 = TodoItem(description="Test item")
        self.assertEqual(item1, item2)

        item2.state = TodoState.COMPLETED
        self.assertNotEqual(item1, item2)

        item2.state = TodoState.PENDING
        item1.add_item("Sub-item 1")
        self.assertNotEqual(item1, item2)

        item2.add_item("Sub-item 1")
        self.assertEqual(item1, item2)

        # Parent references don't cause infinite recursion
        todo_list = TodoList()
        item3 = todo_list.add_item("Parent item")
        item3.add_item("Sub-item 1")
        item4 = TodoItem(description="Parent item")
        item4.add_item("Sub-item 1")
        self.assertEqual(item3, item4)


if __name__ == "__main__":
    unittest.main()
