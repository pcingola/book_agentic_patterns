"""Observability: structured logging and metrics for the MCP proxy."""

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ToolCallMetrics:
    """Accumulated metrics for a specific tool."""

    call_count: int = 0
    error_count: int = 0
    total_duration_ms: float = 0.0

    def __str__(self) -> str:
        return f"ToolCallMetrics(calls={self.call_count}, errors={self.error_count}, avg={self.avg_duration_ms:.1f}ms)"

    @property
    def avg_duration_ms(self) -> float:
        return self.total_duration_ms / self.call_count if self.call_count else 0.0


@dataclass
class MetricsCollector:
    """Collects per-tool, per-server, and per-user metrics."""

    _by_tool: dict[str, ToolCallMetrics] = field(default_factory=dict)
    _by_server: dict[str, ToolCallMetrics] = field(default_factory=dict)
    _by_user: dict[str, ToolCallMetrics] = field(default_factory=dict)
    _by_tenant: dict[str, ToolCallMetrics] = field(default_factory=dict)

    def get_by_server(self) -> dict[str, ToolCallMetrics]:
        return dict(self._by_server)

    def get_by_tenant(self) -> dict[str, ToolCallMetrics]:
        return dict(self._by_tenant)

    def get_by_tool(self) -> dict[str, ToolCallMetrics]:
        return dict(self._by_tool)

    def get_by_user(self) -> dict[str, ToolCallMetrics]:
        return dict(self._by_user)

    def record(self, server: str, tool: str, user: str, tenant: str, duration_ms: float, is_error: bool) -> None:
        for store, key in [(self._by_tool, f"{server}.{tool}"), (self._by_server, server), (self._by_user, user), (self._by_tenant, tenant)]:
            metrics = store.setdefault(key, ToolCallMetrics())
            metrics.call_count += 1
            metrics.total_duration_ms += duration_ms
            if is_error:
                metrics.error_count += 1


def log_tool_call(user: str, tenant: str, server: str, tool: str, duration_ms: float, status: str) -> None:
    """Emit a structured log entry for a tool invocation."""
    logger.info(
        "tool_call user=%s tenant=%s server=%s tool=%s duration_ms=%.1f status=%s",
        user, tenant, server, tool, duration_ms, status,
    )
