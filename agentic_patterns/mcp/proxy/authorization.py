"""Policy-based authorization for the MCP proxy."""

import fnmatch
import logging

from agentic_patterns.mcp.proxy.config import PolicyRule

logger = logging.getLogger(__name__)


class AuthorizationPolicy:
    """Evaluates access rules against role, server, and tool."""

    def __init__(self, rules: list[PolicyRule]) -> None:
        self._rules = rules

    def __str__(self) -> str:
        return f"AuthorizationPolicy(rules={len(self._rules)})"

    def is_allowed(self, role: str, namespaced_tool: str) -> bool:
        """Check if a role is allowed to call a namespaced tool (server.tool).

        Rules are evaluated in order. First matching deny wins, then first matching allow.
        If no rule matches, access is denied by default.
        """
        for rule in self._rules:
            if rule.role != "*" and rule.role != role:
                continue
            if any(fnmatch.fnmatch(namespaced_tool, pattern) for pattern in rule.deny):
                logger.info(
                    "Denied %s for role %s (matched deny rule)", namespaced_tool, role
                )
                return False
            if any(fnmatch.fnmatch(namespaced_tool, pattern) for pattern in rule.allow):
                return True
        return False
