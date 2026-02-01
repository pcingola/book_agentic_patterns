import tempfile
import unittest
from pathlib import Path, PurePosixPath
from unittest.mock import patch

from agentic_patterns.core.user_session import set_user_session
from agentic_patterns.core.workspace import (
    WorkspaceError,
    workspace_to_host_path,
    host_to_workspace_path,
    list_workspace_files,
    read_from_workspace,
    store_result,
    write_to_workspace,
)


class TestWorkspace(unittest.TestCase):
    """Tests for agentic_patterns.core.workspace module."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace_dir = Path(self.temp_dir.name)
        self.patcher = patch("agentic_patterns.core.workspace.WORKSPACE_DIR", self.workspace_dir)
        self.patcher.start()
        set_user_session("default_user", "default_session")

    def tearDown(self):
        self.patcher.stop()
        self.temp_dir.cleanup()

    def test_workspace_to_host_path_converts_valid_path(self):
        """Test converting sandbox path to host path."""
        path = PurePosixPath("/workspace/docs/file.txt")
        result = workspace_to_host_path(path)
        expected = self.workspace_dir / "default_user" / "default_session" / "docs" / "file.txt"
        self.assertEqual(result, expected)

    def test_workspace_to_host_path_rejects_invalid_prefix(self):
        """Test that paths not starting with /workspace are rejected."""
        path = PurePosixPath("/other/docs/file.txt")
        with self.assertRaises(WorkspaceError) as ctx:
            workspace_to_host_path(path)
        self.assertIn("/workspace", str(ctx.exception))

    def test_workspace_to_host_path_rejects_traversal(self):
        """Test that path traversal attempts are rejected."""
        path = PurePosixPath("/workspace/../../../etc/passwd")
        with self.assertRaises(WorkspaceError) as ctx:
            workspace_to_host_path(path)
        self.assertIn("traversal", str(ctx.exception))

    def test_host_to_workspace_path_converts_valid_path(self):
        """Test converting host path back to sandbox path."""
        host_path = self.workspace_dir / "user1" / "sess1" / "docs" / "file.txt"
        host_path.parent.mkdir(parents=True, exist_ok=True)
        host_path.touch()
        result = host_to_workspace_path(host_path)
        self.assertEqual(result, PurePosixPath("/workspace/docs/file.txt"))

    def test_write_and_read_workspace(self):
        """Test writing and reading content from workspace."""
        content = "Hello, workspace!"
        write_to_workspace("/workspace/test.txt", content)
        result = read_from_workspace("/workspace/test.txt")
        self.assertEqual(result, content)

    def test_read_nonexistent_raises_error(self):
        """Test that reading nonexistent file raises WorkspaceError."""
        with self.assertRaises(WorkspaceError) as ctx:
            read_from_workspace("/workspace/nonexistent.txt")
        self.assertIn("not found", str(ctx.exception))

    def test_list_workspace_files_returns_matching(self):
        """Test listing files matching a pattern."""
        write_to_workspace("/workspace/docs/a.txt", "a")
        write_to_workspace("/workspace/docs/b.txt", "b")
        write_to_workspace("/workspace/other/c.md", "c")
        results = list_workspace_files("*.txt")
        self.assertEqual(len(results), 2)
        self.assertTrue(all(".txt" in r for r in results))

    def test_store_result_creates_file_with_extension(self):
        """Test that store_result creates file with correct extension."""
        path = store_result('{"key": "value"}', "json")
        self.assertTrue(path.startswith("/workspace/results/"))
        self.assertTrue(path.endswith(".json"))
        content = read_from_workspace(path)
        self.assertEqual(content, '{"key": "value"}')

    def test_user_session_isolation(self):
        """Test that different user/session get different paths."""
        set_user_session("alice", "sess1")
        path_alice = workspace_to_host_path(PurePosixPath("/workspace/file.txt"))

        set_user_session("bob", "sess2")
        path_bob = workspace_to_host_path(PurePosixPath("/workspace/file.txt"))

        self.assertNotEqual(path_alice, path_bob)
        self.assertIn("alice", str(path_alice))
        self.assertIn("bob", str(path_bob))


if __name__ == "__main__":
    unittest.main()
