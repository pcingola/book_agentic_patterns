"""FastMCP middleware for the MCP proxy: authorization, circuit breaking, audit, accounting."""

import logging
import time

from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_access_token
from fastmcp.server.middleware import Middleware, MiddlewareContext

from agentic_patterns.core.user_session import get_session_id, get_user_id
from agentic_patterns.mcp.proxy.accounting import AccountingService
from agentic_patterns.mcp.proxy.audit import AuditEntry, AuditLogger
from agentic_patterns.mcp.proxy.authorization import AuthorizationPolicy
from agentic_patterns.mcp.proxy.circuit_breaker import CircuitBreakerManager

logger = logging.getLogger(__name__)


def _get_role() -> str:
    """Extract role from the access token. Falls back to 'default'."""
    token = get_access_token()
    if token:
        return token.claims.get("role", "default")
    return "default"


def _get_tenant() -> str:
    """Extract tenant from the access token. Falls back to 'default'."""
    token = get_access_token()
    if token:
        return token.claims.get("org_id", "default")
    return "default"


class AccountingMiddleware(Middleware):
    """Tracks usage and enforces budget limits."""

    def __init__(self, accounting: AccountingService) -> None:
        self._accounting = accounting

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        user = get_user_id()
        tenant = _get_tenant()
        session = get_session_id()
        tool_name = context.message.name
        if not self._accounting.check_budget(tenant):
            raise ToolError(f"Budget limit exceeded for tenant '{tenant}'")
        start = time.monotonic()
        is_error = False
        try:
            result = await call_next(context)
            return result
        except Exception:
            is_error = True
            raise
        finally:
            duration_ms = (time.monotonic() - start) * 1000
            self._accounting.record(user, tenant, session, tool_name, duration_ms, is_error)


class AuditMiddleware(Middleware):
    """Logs every tool call to an append-only audit store."""

    def __init__(self, audit_logger: AuditLogger) -> None:
        self._audit = audit_logger

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        user = get_user_id()
        tenant = _get_tenant()
        session = get_session_id()
        tool_name = context.message.name
        args = context.message.arguments or {}
        start = time.monotonic()
        status = "ok"
        try:
            result = await call_next(context)
            return result
        except Exception:
            status = "error"
            raise
        finally:
            duration_ms = (time.monotonic() - start) * 1000
            self._audit.log(AuditEntry(
                timestamp=time.time(), user_id=user, tenant=tenant, session_id=session,
                server="proxy", tool=tool_name, args=args, status=status, duration_ms=duration_ms,
            ))


class AuthorizationMiddleware(Middleware):
    """Enforces policy-based authorization on tool calls."""

    def __init__(self, policy: AuthorizationPolicy) -> None:
        self._policy = policy

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        role = _get_role()
        tool_name = context.message.name
        if not self._policy.is_allowed(role, tool_name):
            raise ToolError(f"Access denied: role '{role}' cannot call '{tool_name}'")
        return await call_next(context)


class CircuitBreakerMiddleware(Middleware):
    """Per-server circuit breaker on tool calls."""

    def __init__(self, manager: CircuitBreakerManager, backend_names: list[str] | None = None) -> None:
        self._manager = manager
        # Sort longest-first so "demo_v2" matches before "demo"
        self._backend_names = sorted(backend_names or [], key=len, reverse=True)

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        tool_name = context.message.name
        server_name = self._extract_server(tool_name)
        breaker = self._manager.get(server_name)
        if not breaker.allow_request():
            raise ToolError(f"Server '{server_name}' temporarily unavailable (circuit open)")
        try:
            result = await call_next(context)
            breaker.record_success()
            return result
        except Exception:
            breaker.record_failure()
            raise

    def _extract_server(self, tool_name: str) -> str:
        """Extract server name from a namespaced tool name."""
        for name in self._backend_names:
            if tool_name.startswith(name + "_"):
                return name
        return tool_name
