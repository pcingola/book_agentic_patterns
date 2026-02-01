"""Unit tests for JSON connector operations."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agentic_patterns.core.connectors.json import JsonConnector


class TestJsonConnector(unittest.TestCase):
    """Test JSON connector operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace_dir = Path(self.temp_dir.name)
        self.patcher = patch("agentic_patterns.core.workspace.WORKSPACE_DIR", self.workspace_dir)
        self.patcher.start()

        self.workspace_root = self.workspace_dir / "default_user" / "default_session"
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.connector = JsonConnector()

    def tearDown(self):
        """Clean up test fixtures."""
        self.patcher.stop()
        self.temp_dir.cleanup()

    def _create_json_file(self, filename: str, data: dict | list) -> str:
        """Create a JSON file and return its sandbox path."""
        file_path = self.workspace_root / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        return f"/workspace/{filename}"

    def test_head_json_root_object(self):
        """Test head on root object returns first N keys."""
        data = {f"key_{i}": f"value_{i}" for i in range(20)}
        sandbox_path = self._create_json_file("test.json", data)
        result = self.connector.head(sandbox_path, "$", n=5)
        self.assertIn("key_0", result)
        self.assertIn("key_4", result)
        self.assertNotIn("key_5", result)
        self.assertIn("Showing first 5 of 20", result)

    def test_head_json_array(self):
        """Test head on array returns first N elements."""
        sandbox_path = self._create_json_file("arr.json", {"items": list(range(30))})
        result = self.connector.head(sandbox_path, "$.items", n=5)
        self.assertIn("0", result)
        self.assertIn("4", result)
        self.assertIn("Showing first 5 of 30", result)

    def test_head_json_small(self):
        """Test head on small structure returns everything without truncation info."""
        sandbox_path = self._create_json_file("small.json", {"a": 1, "b": 2})
        result = self.connector.head(sandbox_path, "$", n=10)
        self.assertIn("a", result)
        self.assertIn("b", result)
        self.assertNotIn("Showing", result)

    def test_head_json_file_not_found(self):
        """Test head with non-existent file."""
        result = self.connector.head("/workspace/nonexistent.json")
        self.assertIn("[Error]", result)
        self.assertIn("not found", result)

    def test_tail_json_root_object(self):
        """Test tail on root object returns last N keys."""
        data = {f"key_{i}": f"value_{i}" for i in range(20)}
        sandbox_path = self._create_json_file("test.json", data)
        result = self.connector.tail(sandbox_path, "$", n=5)
        self.assertIn("key_19", result)
        self.assertIn("key_15", result)
        self.assertNotIn("key_14", result)
        self.assertIn("Showing last 5 of 20", result)

    def test_tail_json_array(self):
        """Test tail on array returns last N elements."""
        sandbox_path = self._create_json_file("arr.json", {"items": list(range(30))})
        result = self.connector.tail(sandbox_path, "$.items", n=5)
        self.assertIn("29", result)
        self.assertIn("25", result)
        self.assertIn("Showing last 5 of 30", result)

    def test_get_json_primitive(self):
        """Test getting a primitive value."""
        sandbox_path = self._create_json_file("config.json", {"features": {"rollout": {"percent": 50}}})
        result = self.connector.get(sandbox_path, "$.features.rollout.percent")
        self.assertEqual(result.strip(), "50")

    def test_get_json_object(self):
        """Test getting an object value."""
        sandbox_path = self._create_json_file("config.json", {"features": {"rollout": {"enabled": True, "percent": 50}}})
        result = self.connector.get(sandbox_path, "$.features.rollout")
        self.assertIn("enabled", result)
        self.assertIn("percent", result)

    def test_get_json_array_index(self):
        """Test getting array element by index."""
        sandbox_path = self._create_json_file("users.json", {"users": [{"name": "Alice"}, {"name": "Bob"}]})
        result = self.connector.get(sandbox_path, "$.users[0].name")
        self.assertIn("Alice", result)

    def test_get_json_not_found(self):
        """Test getting non-existent path."""
        sandbox_path = self._create_json_file("test.json", {"key": "value"})
        result = self.connector.get(sandbox_path, "$.nonexistent")
        self.assertIn("[Error]", result)
        self.assertIn("not found", result)

    def test_keys_json_object(self):
        """Test listing keys of an object."""
        sandbox_path = self._create_json_file("config.json", {"features": {"rollout": {}, "darkMode": True, "analytics": {}}})
        result = self.connector.keys(sandbox_path, "$.features")
        self.assertIn("rollout", result)
        self.assertIn("darkMode", result)
        self.assertIn("analytics", result)

    def test_keys_json_array(self):
        """Test listing keys of an array."""
        sandbox_path = self._create_json_file("users.json", {"users": [1, 2, 3, 4, 5]})
        result = self.connector.keys(sandbox_path, "$.users")
        self.assertIn("Array", result)
        self.assertIn("5 items", result)

    def test_keys_json_root(self):
        """Test listing keys at root."""
        sandbox_path = self._create_json_file("config.json", {"features": {}, "version": "1.0", "env": "prod"})
        result = self.connector.keys(sandbox_path, "$")
        self.assertIn("features", result)
        self.assertIn("version", result)
        self.assertIn("env", result)

    def test_validate_json_valid(self):
        """Test validating a valid JSON file."""
        sandbox_path = self._create_json_file("valid.json", {"key1": "value1", "key2": "value2"})
        result = self.connector.validate(sandbox_path)
        self.assertIn("Valid JSON", result)
        self.assertIn("2 keys", result)

    def test_validate_json_invalid(self):
        """Test validating an invalid JSON file."""
        file_path = self.workspace_root / "invalid.json"
        file_path.write_text('{"key": "value",}')  # Trailing comma - invalid JSON
        result = self.connector.validate("/workspace/invalid.json")
        self.assertIn("[Error]", result)
        self.assertIn("Invalid JSON", result)

    def test_set_json_primitive(self):
        """Test setting a primitive value."""
        sandbox_path = self._create_json_file("config.json", {"features": {"rollout": {"percent": 50}}})
        result = self.connector.set(sandbox_path, "$.features.rollout.percent", "75")
        self.assertIn("Updated", result)
        self.assertNotIn("[Error]", result)

        with open(self.workspace_root / "config.json", "r") as f:
            data = json.load(f)
        self.assertEqual(data["features"]["rollout"]["percent"], 75)

    def test_set_json_object(self):
        """Test setting an object value."""
        sandbox_path = self._create_json_file("config.json", {"features": {}})
        result = self.connector.set(sandbox_path, "$.features.newFeature", '{"enabled": true}')
        self.assertIn("Updated", result)

        with open(self.workspace_root / "config.json", "r") as f:
            data = json.load(f)
        self.assertEqual(data["features"]["newFeature"]["enabled"], True)

    def test_set_json_root_rejected(self):
        """Test that setting root is rejected."""
        sandbox_path = self._create_json_file("test.json", {"key": "value"})
        result = self.connector.set(sandbox_path, "$", '{"new": "value"}')
        self.assertIn("[Error]", result)
        self.assertIn("root", result.lower())

    def test_set_json_wildcard_rejected(self):
        """Test that wildcard paths are rejected."""
        sandbox_path = self._create_json_file("users.json", {"users": [{"status": "active"}, {"status": "active"}]})
        result = self.connector.set(sandbox_path, "$.users[*].status", '"inactive"')
        self.assertIn("[Error]", result)
        self.assertIn("Wildcard", result)

    def test_set_json_invalid_json(self):
        """Test setting with invalid JSON value."""
        sandbox_path = self._create_json_file("test.json", {"key": "value"})
        result = self.connector.set(sandbox_path, "$.key", "not valid json")
        self.assertIn("[Error]", result)
        self.assertIn("Invalid JSON", result)

    def test_delete_json_key(self):
        """Test deleting a key."""
        sandbox_path = self._create_json_file("config.json", {"features": {"old": True, "new": False}})
        result = self.connector.delete_key(sandbox_path, "$.features.old")
        self.assertIn("Deleted", result)

        with open(self.workspace_root / "config.json", "r") as f:
            data = json.load(f)
        self.assertNotIn("old", data["features"])
        self.assertIn("new", data["features"])

    def test_delete_json_root_rejected(self):
        """Test that deleting root is rejected."""
        sandbox_path = self._create_json_file("test.json", {"key": "value"})
        result = self.connector.delete_key(sandbox_path, "$")
        self.assertIn("[Error]", result)
        self.assertIn("root", result.lower())

    def test_delete_json_wildcard_rejected(self):
        """Test that wildcard deletes are rejected."""
        sandbox_path = self._create_json_file("users.json", {"users": [{"temp": True}, {"temp": True}]})
        result = self.connector.delete_key(sandbox_path, "$.users[*].temp")
        self.assertIn("[Error]", result)
        self.assertIn("Wildcard", result)

    def test_delete_json_not_found(self):
        """Test deleting non-existent key."""
        sandbox_path = self._create_json_file("test.json", {"key": "value"})
        result = self.connector.delete_key(sandbox_path, "$.nonexistent")
        self.assertIn("[Error]", result)
        self.assertIn("not found", result)

    def test_append_json(self):
        """Test appending to an array."""
        sandbox_path = self._create_json_file("users.json", {"users": [{"id": 1}, {"id": 2}]})
        result = self.connector.append(sandbox_path, "$.users", '{"id": 3}')
        self.assertIn("Appended", result)
        self.assertIn("3 items", result)

        with open(self.workspace_root / "users.json", "r") as f:
            data = json.load(f)
        self.assertEqual(len(data["users"]), 3)
        self.assertEqual(data["users"][2]["id"], 3)

    def test_append_json_not_array(self):
        """Test appending to non-array."""
        sandbox_path = self._create_json_file("test.json", {"notArray": {"key": "value"}})
        result = self.connector.append(sandbox_path, "$.notArray", '"value"')
        self.assertIn("[Error]", result)
        self.assertIn("not an array", result)

    def test_append_json_invalid_value(self):
        """Test appending with invalid JSON value."""
        sandbox_path = self._create_json_file("test.json", {"arr": []})
        result = self.connector.append(sandbox_path, "$.arr", "not json")
        self.assertIn("[Error]", result)
        self.assertIn("Invalid JSON", result)

    def test_merge_json(self):
        """Test merging into an object."""
        sandbox_path = self._create_json_file("config.json", {"features": {"rollout": {"percent": 50, "enabled": True}}})
        result = self.connector.merge(sandbox_path, "$.features.rollout", '{"percent": 75, "regions": ["us-east-1"]}')
        self.assertIn("Merged", result)
        self.assertIn("2 keys", result)

        with open(self.workspace_root / "config.json", "r") as f:
            data = json.load(f)
        self.assertEqual(data["features"]["rollout"]["percent"], 75)
        self.assertIn("regions", data["features"]["rollout"])
        self.assertTrue(data["features"]["rollout"]["enabled"])

    def test_merge_json_not_object(self):
        """Test merging into non-object."""
        sandbox_path = self._create_json_file("test.json", {"notObject": [1, 2, 3]})
        result = self.connector.merge(sandbox_path, "$.notObject", '{"key": "value"}')
        self.assertIn("[Error]", result)
        self.assertIn("not an object", result)

    def test_merge_json_invalid_updates(self):
        """Test merging with invalid JSON updates."""
        sandbox_path = self._create_json_file("test.json", {"obj": {}})
        result = self.connector.merge(sandbox_path, "$.obj", "not json")
        self.assertIn("[Error]", result)
        self.assertIn("Invalid JSON", result)

    def test_merge_json_updates_not_dict(self):
        """Test merging with non-object updates."""
        sandbox_path = self._create_json_file("test.json", {"obj": {}})
        result = self.connector.merge(sandbox_path, "$.obj", '"string value"')
        self.assertIn("[Error]", result)
        self.assertIn("must be a JSON object", result)

    def test_bracket_notation(self):
        """Test JSONPath with bracket notation."""
        sandbox_path = self._create_json_file("test.json", {"key-with-dash": "value"})
        result = self.connector.get(sandbox_path, "$['key-with-dash']")
        self.assertIn("value", result)

    def test_negative_array_index(self):
        """Test negative array indexing."""
        sandbox_path = self._create_json_file("arr.json", {"items": [1, 2, 3, 4, 5]})
        result = self.connector.get(sandbox_path, "$.items[-1]")
        self.assertIn("5", result)

    def test_null_value(self):
        """Test handling null values."""
        sandbox_path = self._create_json_file("test.json", {"nullable": None})
        result = self.connector.get(sandbox_path, "$.nullable")
        self.assertEqual(result.strip(), "null")

    def test_empty_array(self):
        """Test handling empty arrays."""
        sandbox_path = self._create_json_file("test.json", {"empty": []})
        result = self.connector.keys(sandbox_path, "$.empty")
        self.assertIn("0 items", result)

    def test_empty_object(self):
        """Test handling empty objects."""
        sandbox_path = self._create_json_file("test.json", {"empty": {}})
        result = self.connector.keys(sandbox_path, "$.empty")
        self.assertIn("Keys at $.empty:", result)

    def test_special_characters_in_keys(self):
        """Test keys with special characters."""
        sandbox_path = self._create_json_file("test.json", {"key with spaces": "value", "key.with.dots": "value2"})
        result = self.connector.keys(sandbox_path, "$")
        self.assertIn("key with spaces", result)
        self.assertIn("key.with.dots", result)

    def test_unicode_values(self):
        """Test handling unicode values."""
        sandbox_path = self._create_json_file("test.json", {"name": "Alice", "greeting": "Hello world"})
        result = self.connector.get(sandbox_path, "$.greeting")
        self.assertIn("Hello", result)

    def test_boolean_values(self):
        """Test handling boolean values."""
        sandbox_path = self._create_json_file("test.json", {"active": True, "deleted": False})
        result = self.connector.get(sandbox_path, "$.active")
        self.assertEqual(result.strip(), "true")

    def test_inherited_file_delete(self):
        """Test that inherited delete (file) works on JSON files."""
        sandbox_path = self._create_json_file("test.json", {"key": "value"})
        result = self.connector.delete(sandbox_path)
        self.assertIn("Deleted", result)
        self.assertFalse((self.workspace_root / "test.json").exists())


if __name__ == "__main__":
    unittest.main()
