import unittest

from agentic_patterns.core.tools import (
    ToolPermission,
    ToolPermissionError,
    tool_permission,
    get_permissions,
    filter_tools_by_permission,
    enforce_tools_permissions,
)
from agentic_patterns.core.tools.permissions import enforce_tool_permission


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

    def test_enforce_tool_permission_callable_allowed(self):
        """Test that a callable returning sufficient permissions allows execution."""
        provider = lambda: {ToolPermission.READ, ToolPermission.CONNECT}
        wrapped = enforce_tool_permission(read_connect_func, provider)
        self.assertEqual(wrapped(), "read_connect")

    def test_enforce_tool_permission_callable_denied(self):
        """Test that a callable returning insufficient permissions raises error."""
        provider = lambda: {ToolPermission.READ}
        wrapped = enforce_tool_permission(read_connect_func, provider)
        with self.assertRaises(ToolPermissionError):
            wrapped()

    def test_enforce_tool_permission_callable_invoked_each_call(self):
        """Test that the callable is evaluated on every invocation, not just once."""
        call_count = 0

        def provider():
            nonlocal call_count
            call_count += 1
            return {ToolPermission.READ}

        wrapped = enforce_tool_permission(read_func, provider)
        wrapped()
        wrapped()
        self.assertEqual(call_count, 2)

    def test_enforce_tool_permission_dynamic_change(self):
        """Test that permission changes mid-conversation are respected."""
        permissions = {ToolPermission.READ, ToolPermission.CONNECT}
        wrapped = enforce_tool_permission(read_connect_func, lambda: permissions)

        # First call succeeds
        self.assertEqual(wrapped(), "read_connect")

        # Remove CONNECT mid-conversation
        permissions.discard(ToolPermission.CONNECT)
        with self.assertRaises(ToolPermissionError):
            wrapped()


if __name__ == "__main__":
    unittest.main()
