"""MCP Proxy Server: central entry point that fronts all backend MCP servers.

Agents connect to the proxy as a single MCP server. The proxy authenticates,
authorizes, meters, and forwards tool calls to the appropriate backend.
"""

import logging
import time
from pathlib import Path
from typing import Any

from fastmcp import FastMCP
from fastmcp.server.dependencies import get_access_token
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from agentic_patterns.core.config.config import DEFAULT_SESSION_ID
from agentic_patterns.core.mcp.errors import ToolFatalError, ToolRetryError
from agentic_patterns.mcp.proxy.accounting import AccountingService
from agentic_patterns.mcp.proxy.audit import AuditEntry, AuditLogger
from agentic_patterns.mcp.proxy.authorization import AuthorizationPolicy
from agentic_patterns.mcp.proxy.circuit_breaker import CircuitBreakerManager
from agentic_patterns.mcp.proxy.config import ProxyConfig
from agentic_patterns.mcp.proxy.observability import MetricsCollector, log_tool_call
from agentic_patterns.mcp.proxy.rate_limiter import RateLimiter
from agentic_patterns.mcp.proxy.registry import ServerRegistry, ServerStatus

logger = logging.getLogger(__name__)


class MCPProxyServer:
    """Enterprise MCP proxy that fronts multiple backend MCP servers."""

    def __init__(self, config: ProxyConfig, audit_db_path: Path | None = None) -> None:
        self._config = config
        self._registry = ServerRegistry(config.backends)
        self._auth_policy = AuthorizationPolicy(config.policies)
        self._rate_limiter = RateLimiter(config.rate_limits)
        self._circuit_breakers = CircuitBreakerManager(config.circuit_breaker)
        self._metrics = MetricsCollector()
        self._accounting = AccountingService(budget_alerts=config.accounting.budget_alerts)
        self._audit = AuditLogger(audit_db_path or Path("data/proxy_audit.db"))
        self._mcp = FastMCP(name="mcp-proxy", instructions="Enterprise MCP Proxy")

    def __str__(self) -> str:
        healthy = len([s for s in self._registry.servers.values() if s.status == ServerStatus.HEALTHY])
        return f"MCPProxyServer(port={self._config.port}, backends={healthy}/{len(self._registry.servers)})"

    @property
    def accounting(self) -> AccountingService:
        return self._accounting

    @property
    def mcp(self) -> FastMCP:
        return self._mcp

    @property
    def metrics(self) -> MetricsCollector:
        return self._metrics

    @property
    def registry(self) -> ServerRegistry:
        return self._registry

    async def start(self) -> None:
        """Discover backends and register proxy tools."""
        await self._registry.discover_all()
        self._register_tools()
        healthy = len([s for s in self._registry.servers.values() if s.status == ServerStatus.HEALTHY])
        logger.info("MCP Proxy started with %d tools from %d backends", len(self._registry.get_all_tools()), healthy)

    async def _call_backend(self, server_name: str, tool_name: str, args: dict) -> str:
        """Open a connection to the backend and call the tool."""
        server = self._registry.servers.get(server_name)
        if not server:
            raise ToolFatalError(f"Unknown server: {server_name}")
        async with streamablehttp_client(server.config.url) as (r, w, _):
            async with ClientSession(r, w) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, args)
                if result.isError:
                    text = "\n".join(c.text for c in result.content if hasattr(c, "text"))
                    raise ToolRetryError(text)
                return "\n".join(c.text for c in result.content if hasattr(c, "text"))

    def _extract_identity(self) -> tuple[str, str, str]:
        """Extract user, tenant, and session from the access token."""
        token = get_access_token()
        if token:
            user = token.claims.get("sub", "anonymous")
            tenant = token.claims.get("org_id", "default")
            session = token.claims.get("session_id", DEFAULT_SESSION_ID)
            return user, tenant, session
        return "anonymous", "default", DEFAULT_SESSION_ID

    def _extract_role(self) -> str:
        """Extract role from the access token claims."""
        token = get_access_token()
        if token:
            return token.claims.get("role", "default")
        return "default"

    async def _forward_tool_call(self, server_name: str, tool_name: str, namespaced_name: str, args: dict) -> str:
        """Forward a tool call through all proxy layers."""
        user, tenant, session = self._extract_identity()

        # Authorization
        role = self._extract_role()
        if not self._auth_policy.is_allowed(role, namespaced_name):
            raise ToolFatalError(f"Access denied: role '{role}' cannot call '{namespaced_name}'")

        # Rate limiting
        if not self._rate_limiter.allow(user, scope="default"):
            raise ToolRetryError("Rate limit exceeded. Try again shortly.")
        if not self._rate_limiter.allow(server_name, scope=f"per_server.{server_name}"):
            raise ToolRetryError(f"Rate limit exceeded for server '{server_name}'. Try again shortly.")

        # Circuit breaker
        breaker = self._circuit_breakers.get(server_name)
        if not breaker.allow_request():
            raise ToolFatalError(f"Server '{server_name}' is temporarily unavailable (circuit open)")

        # Budget check
        if not self._accounting.check_budget(tenant):
            raise ToolFatalError(f"Budget limit exceeded for tenant '{tenant}'")

        # Forward the call
        start = time.monotonic()
        status = "ok"
        try:
            result = await self._call_backend(server_name, tool_name, args)
            breaker.record_success()
            return result
        except Exception:
            status = "error"
            breaker.record_failure()
            raise
        finally:
            duration_ms = (time.monotonic() - start) * 1000
            is_error = status != "ok"
            self._metrics.record(server_name, tool_name, user, tenant, duration_ms, is_error)
            self._accounting.record(user, tenant, session, server_name, duration_ms, is_error)
            log_tool_call(user, tenant, server_name, tool_name, duration_ms, status)
            self._audit.log(AuditEntry(
                timestamp=time.time(), user_id=user, tenant=tenant, session_id=session,
                server=server_name, tool=tool_name, args=args, status=status, duration_ms=duration_ms,
            ))

    def _register_proxy_tool(self, namespaced_name: str, tool: Any) -> None:
        """Register a single proxy tool that forwards to the backend."""
        server_name, tool_name = namespaced_name.split(".", 1)
        description = f"[{server_name}] {tool.description or tool_name}"

        def _make_handler(ns: str = namespaced_name, srv: str = server_name, tl: str = tool_name):
            async def proxy_call(**kwargs: Any) -> str:
                return await self._forward_tool_call(srv, tl, ns, kwargs)
            return proxy_call

        self._mcp.tool(name=namespaced_name, description=description)(_make_handler())

    def _register_tools(self) -> None:
        """Register aggregated tools from all backends on the FastMCP server."""
        for namespaced_name, tool in self._registry.get_all_tools():
            self._register_proxy_tool(namespaced_name, tool)
