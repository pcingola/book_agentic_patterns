"""Configuration models for the MCP proxy."""

from pydantic import BaseModel, Field


class ProxyBackendConfig(BaseModel):
    """Configuration for a backend MCP server behind the proxy."""

    name: str
    url: str
    url_isolated: str | None = None
    read_timeout: int = Field(default=60)
    enabled: bool = True


class CircuitBreakerConfig(BaseModel):
    """Circuit breaker settings."""

    failure_threshold: int = 5
    recovery_timeout: int = 30


class RateLimitConfig(BaseModel):
    """Rate limit settings for a scope."""

    requests_per_minute: int = 60


class BudgetAlertConfig(BaseModel):
    """Budget alert threshold."""

    tenant: str = "*"
    warn_at: int = 1000
    hard_limit: int = 5000


class AccountingConfig(BaseModel):
    """Accounting settings."""

    budget_alerts: list[BudgetAlertConfig] = Field(default_factory=list)


class PolicyRule(BaseModel):
    """Authorization policy rule."""

    role: str
    allow: list[str] = Field(default_factory=list)
    deny: list[str] = Field(default_factory=list)


class ProxyConfig(BaseModel):
    """Top-level proxy configuration."""

    port: int = 8200
    health_check_interval: int = 30
    backends: list[ProxyBackendConfig] = Field(default_factory=list)
    policies: list[PolicyRule] = Field(default_factory=list)
    rate_limits: dict[str, RateLimitConfig] = Field(default_factory=dict)
    circuit_breaker: CircuitBreakerConfig = Field(default_factory=CircuitBreakerConfig)
    accounting: AccountingConfig = Field(default_factory=AccountingConfig)

    def __str__(self) -> str:
        backends = ", ".join(b.name for b in self.backends)
        return f"ProxyConfig(port={self.port}, backends=[{backends}])"
