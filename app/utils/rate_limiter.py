"""Token bucket rate limiter per client IP."""

import time
from threading import Lock
from collections import defaultdict
from typing import Dict

from app.core.config import settings


class TokenBucket:
    """Token bucket for rate limiting."""

    def __init__(self, rate: float, capacity: int):
        self.rate = rate          # tokens per second
        self.capacity = capacity  # max burst
        self.tokens = float(capacity)
        self.last_update = time.time()
        self.lock = Lock()

    def allow(self) -> bool:
        with self.lock:
            now = time.time()
            elapsed = now - self.last_update
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_update = now

            if self.tokens >= 1:
                self.tokens -= 1
                return True
            return False


class RateLimiter:
    """Per-IP rate limiter using token buckets."""

    def __init__(self):
        rate = settings.rate_limit_per_minute / 60.0
        capacity = settings.rate_limit_burst
        self.buckets: Dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(rate, capacity)
        )
        self.lock = Lock()

    def is_allowed(self, client_ip: str) -> bool:
        """Check if request from client_ip is allowed."""
        bucket = self.buckets[client_ip]
        return bucket.allow()

    def cleanup(self):
        """Remove stale buckets (call periodically in production)."""
        # In production, track last access time and remove old entries
        pass


rate_limiter = RateLimiter()
