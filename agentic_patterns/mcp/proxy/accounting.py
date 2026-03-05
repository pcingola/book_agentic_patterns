"""Accounting and cost attribution for the MCP proxy."""

import logging
from dataclasses import dataclass, field

from agentic_patterns.mcp.proxy.config import BudgetAlertConfig

logger = logging.getLogger(__name__)


@dataclass
class UsageRecord:
    """Accumulated usage for a key (user, tenant, session)."""

    call_count: int = 0
    total_duration_ms: float = 0.0
    error_count: int = 0

    def __str__(self) -> str:
        return f"UsageRecord(calls={self.call_count}, duration={self.total_duration_ms:.0f}ms, errors={self.error_count})"

    def add(self, duration_ms: float, is_error: bool) -> None:
        self.call_count += 1
        self.total_duration_ms += duration_ms
        if is_error:
            self.error_count += 1


@dataclass
class AccountingService:
    """Tracks usage per user, tenant, session, and server. Enforces budget alerts."""

    budget_alerts: list[BudgetAlertConfig] = field(default_factory=list)
    _by_tenant: dict[str, UsageRecord] = field(default_factory=dict)
    _by_user: dict[str, UsageRecord] = field(default_factory=dict)
    _by_session: dict[str, UsageRecord] = field(default_factory=dict)
    _by_server: dict[str, UsageRecord] = field(default_factory=dict)
    _alerted: set[str] = field(default_factory=set)

    def get_usage_by_server(self) -> dict[str, UsageRecord]:
        return dict(self._by_server)

    def get_usage_by_session(self) -> dict[str, UsageRecord]:
        return dict(self._by_session)

    def get_usage_by_tenant(self) -> dict[str, UsageRecord]:
        return dict(self._by_tenant)

    def get_usage_by_user(self) -> dict[str, UsageRecord]:
        return dict(self._by_user)

    def check_budget(self, tenant: str) -> bool:
        """Check if tenant is within budget. Returns False if hard limit exceeded."""
        return self._check_budget(tenant)

    def record(self, user: str, tenant: str, session: str, server: str, duration_ms: float, is_error: bool) -> None:
        """Record a tool call."""
        for store, key in [(self._by_user, user), (self._by_tenant, tenant), (self._by_session, session), (self._by_server, server)]:
            record = store.setdefault(key, UsageRecord())
            record.add(duration_ms, is_error)

    def _check_budget(self, tenant: str) -> bool:
        """Check budget alerts for a tenant. Returns False if hard limit exceeded."""
        record = self._by_tenant.get(tenant)
        if not record:
            return True
        for alert in self.budget_alerts:
            if alert.tenant != "*" and alert.tenant != tenant:
                continue
            if record.call_count >= alert.hard_limit:
                logger.warning("Hard limit reached for tenant %s (%d calls)", tenant, record.call_count)
                return False
            alert_key = f"{tenant}:{alert.warn_at}"
            if record.call_count >= alert.warn_at and alert_key not in self._alerted:
                logger.warning("Budget warning for tenant %s: %d calls (warn_at=%d)", tenant, record.call_count, alert.warn_at)
                self._alerted.add(alert_key)
        return True
