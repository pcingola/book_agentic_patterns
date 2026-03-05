"""Configuration models for the MCP proxy."""

from pydantic import BaseModel, Field


class ProxyBackendConfig(BaseModel):
    """Configuration for a backend MCP server behind the proxy."""

    name: str
    url: str
    enabled: bool = True


class CircuitBreakerConfig(BaseModel):
    """Circuit breaker settings."""

    failure_threshold: int = 5
    recovery_timeout: int = 30


class RateLimitConfig(BaseModel):
    """Rate limit settings."""

    requests_per_second: float = 1.0
    burst_capacity: int = 20


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
    backends: list[ProxyBackendConfig] = Field(default_factory=list)
    policies: list[PolicyRule] = Field(default_factory=list)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    circuit_breaker: CircuitBreakerConfig = Field(default_factory=CircuitBreakerConfig)
    accounting: AccountingConfig = Field(default_factory=AccountingConfig)

    def __str__(self) -> str:
        backends = ", ".join(b.name for b in self.backends)
        return f"ProxyConfig(port={self.port}, backends=[{backends}])"
