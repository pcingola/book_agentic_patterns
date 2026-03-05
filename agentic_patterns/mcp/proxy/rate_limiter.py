"""Token-bucket rate limiter for the MCP proxy."""

import time
from dataclasses import dataclass, field

from agentic_patterns.mcp.proxy.config import RateLimitConfig


@dataclass
class TokenBucket:
    """Simple token bucket for rate limiting."""

    capacity: float
    refill_rate: float  # tokens per second
    tokens: float = 0.0
    last_refill: float = field(default_factory=time.monotonic)

    def __post_init__(self) -> None:
        self.tokens = self.capacity

    def consume(self) -> bool:
        """Try to consume one token. Returns True if allowed, False if rate-limited."""
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False


class RateLimiter:
    """Per-key rate limiter using token buckets."""

    def __init__(self, configs: dict[str, RateLimitConfig]) -> None:
        self._configs = configs
        self._buckets: dict[str, TokenBucket] = {}

    def allow(self, key: str, scope: str = "default") -> bool:
        """Check if a request is allowed for the given key (e.g., user_id or server_name)."""
        bucket_key = f"{scope}:{key}"
        if bucket_key not in self._buckets:
            config = self._configs.get(scope) or self._configs.get("default")
            if not config:
                return True
            rpm = config.requests_per_minute
            self._buckets[bucket_key] = TokenBucket(capacity=float(rpm), refill_rate=rpm / 60.0)
        return self._buckets[bucket_key].consume()
