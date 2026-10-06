"""In-process sliding-window rate limiting engine with pluggable storage abstraction.

Designed for V1 to operate with zero external dependencies (no Redis required),
while providing an extensible interface that can seamlessly migrate to Redis
for distributed multi-worker deployments in V2.
"""

import threading
import time
from collections import defaultdict, deque
from typing import Protocol

from app.core.errors import AppException


class RateLimiterStorage(Protocol):
    """Storage protocol for rate limit counters and timestamps."""

    def check_and_record(
        self, key: str, limit: int, window_seconds: int
    ) -> tuple[bool, int]:
        """Check if request is allowed and record it.

        Returns:
            (is_allowed, retry_after_seconds)
        """
        ...

    def record_failure(self, key: str, window_seconds: int) -> int:
        """Record a failure event and return current count in window."""
        ...

    def get_failures(self, key: str, window_seconds: int) -> int:
        """Return failure count in the active window."""
        ...

    def reset(self, key: str) -> None:
        """Reset counter/window for a given key."""
        ...

    def increment_attempts(self, key: str, window_seconds: int) -> int:
        """Increment and return attempt counter for a specific cycle."""
        ...

    def clear(self) -> None:
        """Purge all rate limit records (testing)."""
        ...


class InMemoryRateLimiterStorage:
    """Thread-safe sliding-window rate limit storage using in-memory deques."""

    def __init__(self, max_keys: int = 100_000) -> None:
        self._lock = threading.Lock()
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._failures: dict[str, deque[float]] = defaultdict(deque)
        self._attempts: dict[str, int] = defaultdict(int)
        self._max_keys = max_keys
        self._ops_counter = 0

    def _purge_old_entries(self, queue: deque[float], cutoff: float) -> None:
        while queue and queue[0] <= cutoff:
            queue.popleft()

    def _periodic_cleanup(self, now: float) -> None:
        """Prevent memory growth by purging empty keys periodically."""
        self._ops_counter += 1
        if self._ops_counter < 1000:
            return
        self._ops_counter = 0

        # Purge empty keys
        for key in list(self._requests.keys()):
            if not self._requests[key]:
                del self._requests[key]
        for key in list(self._failures.keys()):
            if not self._failures[key]:
                del self._failures[key]

    def check_and_record(
        self, key: str, limit: int, window_seconds: int
    ) -> tuple[bool, int]:
        now = time.time()
        cutoff = now - window_seconds

        with self._lock:
            self._periodic_cleanup(now)
            queue = self._requests[key]
            self._purge_old_entries(queue, cutoff)

            if len(queue) >= limit:
                oldest = queue[0]
                retry_after = max(1, int(oldest + window_seconds - now))
                return False, retry_after

            queue.append(now)
            return True, 0

    def record_failure(self, key: str, window_seconds: int) -> int:
        now = time.time()
        cutoff = now - window_seconds

        with self._lock:
            self._periodic_cleanup(now)
            queue = self._failures[key]
            self._purge_old_entries(queue, cutoff)
            queue.append(now)
            return len(queue)

    def get_failures(self, key: str, window_seconds: int) -> int:
        now = time.time()
        cutoff = now - window_seconds

        with self._lock:
            queue = self._failures.get(key)
            if not queue:
                return 0
            self._purge_old_entries(queue, cutoff)
            return len(queue)

    def reset(self, key: str) -> None:
        with self._lock:
            self._requests.pop(key, None)
            self._failures.pop(key, None)
            self._attempts.pop(key, None)

    def increment_attempts(self, key: str, window_seconds: int) -> int:
        with self._lock:
            self._attempts[key] += 1
            return self._attempts[key]

    def get_attempts(self, key: str) -> int:
        with self._lock:
            return self._attempts.get(key, 0)

    def clear(self) -> None:
        with self._lock:
            self._requests.clear()
            self._failures.clear()
            self._attempts.clear()


class RateLimiter:
    """Authentication and API application-level rate limiter.

    Provides domain-specific policy enforcement tuned for campus NAT environments
    where multiple legitimate students share public university IP addresses.
    """

    def __init__(self, storage: RateLimiterStorage | None = None) -> None:
        self.storage: RateLimiterStorage = storage or InMemoryRateLimiterStorage()

    def _rate_limit_exceeded(self, retry_after: int) -> None:
        raise AppException(
            code="RATE_LIMITED",
            message="Too many requests. Please try again later.",
            status_code=429,
            headers={"Retry-After": str(retry_after)},
        )

    # 1. Login Rate Limiting Policy
    # IP limit: 15 failed attempts per 15 minutes (generous for campus NAT)
    # Account limit: 5 failed attempts per 15 minutes per email (protects single account)
    def check_login_rate_limit(self, client_ip: str, email: str | None = None) -> None:
        window = 15 * 60  # 15 minutes

        # Check IP failure threshold
        ip_failures = self.storage.get_failures(f"login_fail:ip:{client_ip}", window)
        if ip_failures >= 15:
            self._rate_limit_exceeded(retry_after=60)

        # Check Account failure threshold
        if email:
            clean_email = email.lower().strip()
            acct_failures = self.storage.get_failures(f"login_fail:email:{clean_email}", window)
            if acct_failures >= 5:
                self._rate_limit_exceeded(retry_after=120)

    def record_login_failure(self, client_ip: str, email: str | None = None) -> None:
        window = 15 * 60
        self.storage.record_failure(f"login_fail:ip:{client_ip}", window)
        if email:
            self.storage.record_failure(f"login_fail:email:{email.lower().strip()}", window)

    def record_login_success(self, email: str | None = None) -> None:
        if email:
            self.storage.reset(f"login_fail:email:{email.lower().strip()}")

    # 2. Registration Rate Limiting Policy
    # IP limit: 10 registrations per hour (burst capacity for campus dorms/labs)
    def check_registration_rate_limit(self, client_ip: str) -> None:
        allowed, retry_after = self.storage.check_and_record(
            key=f"reg:ip:{client_ip}",
            limit=10,
            window_seconds=3600,
        )
        if not allowed:
            self._rate_limit_exceeded(retry_after=retry_after)

    # 3. Token Refresh Rate Limiting Policy
    # Session / IP limit: 60 requests per minute
    def check_refresh_rate_limit(self, client_ip: str, token_hash: str) -> None:
        allowed, retry_after = self.storage.check_and_record(
            key=f"refresh:{token_hash[:16]}:{client_ip}",
            limit=60,
            window_seconds=60,
        )
        if not allowed:
            self._rate_limit_exceeded(retry_after=retry_after)

    def clear(self) -> None:
        self.storage.clear()


# Global singleton instance
rate_limiter = RateLimiter()
