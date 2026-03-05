"""MCP Proxy Server: central entry point that fronts all backend MCP servers.

Uses FastMCP's as_proxy() and mount() for server composition, preserving
tool schemas, prompts, and resources. Enterprise concerns (authorization,
circuit breaking, audit, accounting) are implemented as FastMCP middleware.
"""

import json
import logging
from dataclasses import asdict
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.server.middleware.logging import LoggingMiddleware
from fastmcp.server.middleware.rate_limiting import RateLimitingMiddleware

from agentic_patterns.core.mcp.middleware import AuthSessionMiddleware
from agentic_patterns.mcp.proxy.accounting import AccountingService
from agentic_patterns.mcp.proxy.audit import AuditLogger
from agentic_patterns.mcp.proxy.authorization import AuthorizationPolicy
from agentic_patterns.mcp.proxy.circuit_breaker import CircuitBreakerManager
from agentic_patterns.mcp.proxy.config import ProxyConfig
from agentic_patterns.mcp.proxy.middleware import (
    AccountingMiddleware,
    AuditMiddleware,
    AuthorizationMiddleware,
    CircuitBreakerMiddleware,
)

logger = logging.getLogger(__name__)


class MCPProxyServer:
    """Enterprise MCP proxy that fronts multiple backend MCP servers.

    Uses FastMCP composition (as_proxy + mount) to aggregate backends
    and FastMCP middleware for cross-cutting concerns.
    """

    def __init__(self, config: ProxyConfig, audit_path: Path | None = None) -> None:
        self._config = config
        self._accounting = AccountingService(budget_alerts=config.accounting.budget_alerts)
        self._audit = AuditLogger(audit_path or Path("data/proxy_audit.jsonl"))
        self._mcp = self._build_server(config)

    def __str__(self) -> str:
        backends = ", ".join(b.name for b in self._config.backends if b.enabled)
        return f"MCPProxyServer(port={self._config.port}, backends=[{backends}])"

    @property
    def accounting(self) -> AccountingService:
        return self._accounting

    @property
    def audit(self) -> AuditLogger:
        return self._audit

    @property
    def mcp(self) -> FastMCP:
        return self._mcp

    def _build_server(self, config: ProxyConfig) -> FastMCP:
        """Build the FastMCP server with mounted backends and middleware."""
        mcp = FastMCP(name="mcp-proxy", instructions="Enterprise MCP Proxy")

        # Mount each backend using as_proxy (preserves schemas, prompts, resources)
        backend_names = []
        for backend in config.backends:
            if not backend.enabled:
                continue
            proxy = FastMCP.as_proxy(backend.url)
            mcp.mount(proxy, prefix=backend.name)
            backend_names.append(backend.name)
            logger.info("Mounted backend: %s -> %s", backend.name, backend.url)

        # Introspection tools (on the proxy itself, not on backends)
        self._register_introspection_tools(mcp)

        # Middleware stack (outermost first):
        # 1. AuthSession: set identity from JWT for all requests
        # 2. Logging: structured logs for every operation
        # 3. Audit: log all attempts (including denied ones)
        # 4. Authorization: reject unauthorized tool calls
        # 5. RateLimit: enforce per-second call limits
        # 6. Accounting: check budget + record usage (only for authorized calls)
        # 7. CircuitBreaker: reject if backend is down
        mcp.add_middleware(AuthSessionMiddleware())
        mcp.add_middleware(LoggingMiddleware())
        mcp.add_middleware(AuditMiddleware(self._audit))
        if config.policies:
            mcp.add_middleware(AuthorizationMiddleware(
                AuthorizationPolicy(config.policies),
            ))
        mcp.add_middleware(RateLimitingMiddleware(
            max_requests_per_second=config.rate_limit.requests_per_second,
            burst_capacity=config.rate_limit.burst_capacity,
        ))
        mcp.add_middleware(AccountingMiddleware(self._accounting))
        mcp.add_middleware(CircuitBreakerMiddleware(
            CircuitBreakerManager(config.circuit_breaker),
            backend_names=backend_names,
        ))

        return mcp

    def _register_introspection_tools(self, mcp: FastMCP) -> None:
        """Register proxy introspection tools for audit and accounting."""
        audit = self._audit
        accounting = self._accounting

        @mcp.tool()
        def proxy_audit_read(limit: int = 20) -> str:
            """Read recent audit log entries."""
            entries = audit.read(limit)
            return json.dumps([asdict(e) for e in entries], indent=2)

        @mcp.tool()
        def proxy_accounting_usage() -> str:
            """Get usage statistics by user, tenant, and server."""
            result = {}
            for label, getter in [
                ("by_user", accounting.get_usage_by_user),
                ("by_tenant", accounting.get_usage_by_tenant),
                ("by_server", accounting.get_usage_by_server),
            ]:
                result[label] = {
                    k: {"calls": v.call_count, "duration_ms": round(v.total_duration_ms), "errors": v.error_count}
                    for k, v in getter().items()
                }
            return json.dumps(result, indent=2)
