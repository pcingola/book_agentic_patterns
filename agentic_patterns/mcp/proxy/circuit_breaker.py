"""Circuit breaker for backend MCP servers."""

import time
from dataclasses import dataclass, field
from enum import Enum

from agentic_patterns.mcp.proxy.config import CircuitBreakerConfig


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    """Per-server circuit breaker. Tracks failures and opens circuit when threshold is reached."""

    config: CircuitBreakerConfig
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure_time: float = 0.0

    def __str__(self) -> str:
        return f"CircuitBreaker(state={self.state.value}, failures={self.failure_count})"

    def allow_request(self) -> bool:
        match self.state:
            case CircuitState.CLOSED:
                return True
            case CircuitState.OPEN:
                elapsed = time.monotonic() - self.last_failure_time
                if elapsed >= self.config.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    return True
                return False
            case CircuitState.HALF_OPEN:
                return True

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.monotonic()
        if self.failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN

    def record_success(self) -> None:
        self.failure_count = 0
        self.state = CircuitState.CLOSED


@dataclass
class CircuitBreakerManager:
    """Manages circuit breakers per backend server."""

    config: CircuitBreakerConfig
    _breakers: dict[str, CircuitBreaker] = field(default_factory=dict)

    def get(self, server_name: str) -> CircuitBreaker:
        if server_name not in self._breakers:
            self._breakers[server_name] = CircuitBreaker(config=self.config)
        return self._breakers[server_name]
