import unittest

from agentic_patterns.core.tools import (
    ToolPermission,
    ToolPermissionError,
    tool_permission,
    get_permissions,
    filter_tools_by_permission,
    enforce_tools_permissions,
)


def plain_func():
    """A function without permission decorator."""
    return "plain"


@tool_permission(ToolPermission.READ)
def read_func():
    """A read-only function."""
    return "read"


@tool_permission(ToolPermission.WRITE)
def write_func():
    """A write function."""
    return "write"


@tool_permission(ToolPermission.READ, ToolPermission.CONNECT)
def read_connect_func():
    """A function requiring both READ and CONNECT."""
    return "read_connect"


class TestToolsPermissions(unittest.TestCase):
    """Tests for agentic_patterns.core.tools.permissions module."""

    def test_get_permissions_default(self):
        """Test that undecorated functions default to READ permission."""
        perms = get_permissions(plain_func)
        self.assertEqual(perms, {ToolPermission.READ})

    def test_get_permissions_single(self):
        """Test getting a single permission from decorated function."""
        perms = get_permissions(read_func)
        self.assertEqual(perms, {ToolPermission.READ})

    def test_get_permissions_multiple(self):
        """Test getting multiple permissions from decorated function."""
        perms = get_permissions(read_connect_func)
        self.assertEqual(perms, {ToolPermission.READ, ToolPermission.CONNECT})

    def test_filter_tools_by_permission(self):
        """Test filtering tools by granted permissions."""
        tools = [plain_func, read_func, write_func, read_connect_func]
        filtered = filter_tools_by_permission(tools, {ToolPermission.READ})
        self.assertEqual(filtered, [plain_func, read_func])

    def test_filter_tools_by_permission_multiple(self):
        """Test filtering with multiple granted permissions."""
        tools = [plain_func, read_func, write_func, read_connect_func]
        filtered = filter_tools_by_permission(tools, {ToolPermission.READ, ToolPermission.CONNECT})
        self.assertEqual(filtered, [plain_func, read_func, read_connect_func])

    def test_enforce_tools_permissions_allowed(self):
        """Test that enforced tools execute when permissions are sufficient."""
        wrapped = enforce_tools_permissions([read_func], {ToolPermission.READ})
        result = wrapped[0]()
        self.assertEqual(result, "read")

    def test_enforce_tools_permissions_denied(self):
        """Test that enforced tools raise ToolPermissionError when permissions are insufficient."""
        wrapped = enforce_tools_permissions([write_func], {ToolPermission.READ})
        with self.assertRaises(ToolPermissionError) as ctx:
            wrapped[0]()
        self.assertIn("write_func", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
