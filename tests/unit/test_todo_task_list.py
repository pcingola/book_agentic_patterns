"""Unit tests for the TodoList model."""

import unittest
from typing import cast

from agentic_patterns.toolkits.todo.models import TodoItem, TodoList, TodoState


class TestTodoListModel(unittest.TestCase):
    """Test cases for the TodoList model."""

    def setUp(self):
        self.todo_list = TodoList()
        self.item1 = self.todo_list.add_item("Item 1")
        self.item2 = self.todo_list.add_item("Item 2")
        item1_subtasks = cast(TodoList, self.item1.subtasks)
        self.sub_item1 = item1_subtasks.add_item("Sub-item 1.1")

    def test_add_item(self):
        todo_list = TodoList()
        item = todo_list.add_item("New item")
        self.assertEqual(len(todo_list.items), 1)
        self.assertEqual(todo_list.items[0], item)
        self.assertEqual(item.description, "New item")
        self.assertEqual(item.parent, todo_list)

    def test_get_item_by_id(self):
        self.assertEqual(self.todo_list.get_item_by_id("1"), self.item1)
        self.assertEqual(self.todo_list.get_item_by_id("2"), self.item2)
        self.assertEqual(self.todo_list.get_item_by_id("1.1"), self.sub_item1)
        self.assertIsNone(self.todo_list.get_item_by_id("3"))
        self.assertIsNone(self.todo_list.get_item_by_id("1.2"))

    def test_update_item_state(self):
        self.todo_list.update_item_state("1", TodoState.IN_PROGRESS)
        self.assertEqual(self.item1.state, TodoState.IN_PROGRESS)

        self.todo_list.update_item_state("1.1", TodoState.COMPLETED)
        self.assertEqual(self.sub_item1.state, TodoState.COMPLETED)

        result = self.todo_list.update_item_state("3", TodoState.FAILED)
        self.assertFalse(result)

    def test_to_markdown(self):
        markdown = self.todo_list.to_markdown()
        self.assertIn("# Todo List", markdown)
        self.assertIn("- [ ] 1: Item 1", markdown)
        self.assertIn("- [ ] 2: Item 2", markdown)
        self.assertIn("- [ ] 1.1: Sub-item 1.1", markdown)

    def test_delete_item_and_renumber(self):
        todo_list = TodoList()
        for i in range(1, 11):
            todo_list.add_item(f"Main Item {i}")

        item1 = todo_list.get_item_by_id("1")
        assert item1 is not None
        assert item1.subtasks is not None
        sub_item1 = item1.subtasks.add_item("Sub-item 1.1")

        assert sub_item1.subtasks is not None
        sub_item1.subtasks.add_item("Nested Item 1.1.1")
        sub_item1.subtasks.add_item("Nested Item 1.1.2")

        markdown = todo_list.to_markdown()
        self.assertIn("- [ ] 1.1.1: Nested Item 1.1.1", markdown)
        self.assertIn("- [ ] 1.1.2: Nested Item 1.1.2", markdown)

        todo_list.delete("1.1.1")

        updated_markdown = todo_list.to_markdown()
        self.assertIn("- [ ] 1.1.1: Nested Item 1.1.2", updated_markdown)
        self.assertNotIn("- [ ] 1.1.2:", updated_markdown)

        updated_sub_sub_item = sub_item1.subtasks.get_item_by_id("1")
        assert updated_sub_sub_item is not None
        self.assertEqual(updated_sub_sub_item.description, "Nested Item 1.1.2")
        self.assertEqual(updated_sub_sub_item.get_id("1.1"), "1.1.1")

    def test_delete_method(self):
        todo_list = TodoList()
        item1 = todo_list.add_item("Item 1")
        todo_list.add_item("Item 2")
        todo_list.add_item("Item 3")

        sub_item1 = item1.add_item("Sub-item 1.1")
        item1.add_item("Sub-item 1.2")
        sub_item1.add_item("Nested 1.1.1")

        # Delete top-level item
        self.assertTrue(todo_list.delete("2"))
        self.assertEqual(len(todo_list.items), 2)
        self.assertEqual(todo_list.items[0].description, "Item 1")
        self.assertEqual(todo_list.items[1].description, "Item 3")
        self.assertEqual(todo_list.items[1].get_id(), "2")

        # Delete sub-item
        self.assertTrue(todo_list.delete("1.2"))
        assert item1.subtasks is not None
        self.assertEqual(len(item1.subtasks.items), 1)
        self.assertEqual(item1.subtasks.items[0].description, "Sub-item 1.1")

        # Delete nested sub-item
        self.assertTrue(todo_list.delete("1.1.1"))
        assert sub_item1.subtasks is not None
        self.assertEqual(len(sub_item1.subtasks.items), 0)

        # Non-existent items
        self.assertFalse(todo_list.delete("4"))
        self.assertFalse(todo_list.delete("1.3"))
        self.assertFalse(todo_list.delete("1.1.2"))

    def test_todo_list_equality(self):
        todo_list1 = TodoList()
        todo_list2 = TodoList()
        self.assertEqual(todo_list1, todo_list2)

        item1_1 = todo_list1.add_item("Item 1")
        todo_list1.add_item("Item 2")
        item2_1 = todo_list2.add_item("Item 1")
        todo_list2.add_item("Item 2")
        self.assertEqual(todo_list1, todo_list2)

        item1_1.add_item("Sub-item 1.1")
        self.assertNotEqual(todo_list1, todo_list2)

        item2_1.add_item("Sub-item 1.1")
        self.assertEqual(todo_list1, todo_list2)

        # parent_item references don't cause infinite recursion
        item = TodoItem(description="Parent")
        todo_list3 = TodoList(parent_item=item)
        todo_list4 = TodoList()
        self.assertEqual(todo_list3, todo_list4)

        todo_list3.add_item("Item in list 3")
        self.assertNotEqual(todo_list3, todo_list4)

    def test_delete_sub_item_specific(self):
        todo_list = TodoList()
        parent_item = todo_list.add_item("Parent Item")
        parent_item.add_item("Sub-item to keep")
        sub_item2 = parent_item.add_item("Sub-item to delete")

        assert parent_item.subtasks is not None
        self.assertEqual(len(parent_item.subtasks.items), 2)

        sub_item2_id = sub_item2.get_id("1")
        success = todo_list.delete(sub_item2_id)

        self.assertTrue(success)
        self.assertEqual(len(parent_item.subtasks.items), 1)
        self.assertEqual(parent_item.subtasks.items[0].description, "Sub-item to keep")
        self.assertIsNone(todo_list.get_item_by_id(sub_item2_id))


if __name__ == "__main__":
    unittest.main()
