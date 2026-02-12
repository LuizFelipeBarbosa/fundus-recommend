from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from fundus_recommend.ingest.types import FetchPolicy


class TokenBucketRateLimiter:
    def __init__(self, rate_per_minute: int) -> None:
        self._rate = max(1, rate_per_minute)
        self._capacity = float(self._rate)
        self._tokens = float(self._rate)
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        while True:
            with self._lock:
                now = time.monotonic()
                elapsed = now - self._last_refill
                refill = elapsed * (self._rate / 60.0)
                if refill > 0:
                    self._tokens = min(self._capacity, self._tokens + refill)
                    self._last_refill = now

                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return

                deficit = 1.0 - self._tokens
                wait_seconds = deficit / (self._rate / 60.0)

            time.sleep(max(wait_seconds, 0.01))


class CircuitBreaker:
    def __init__(self, threshold: int, cooldown_seconds: int) -> None:
        self.threshold = max(1, threshold)
        self.cooldown_seconds = max(1, cooldown_seconds)
        self.failure_count = 0
        self.open_until = 0.0

    def is_open(self) -> bool:
        return time.monotonic() < self.open_until

    def allow_request(self) -> bool:
        if self.is_open():
            return False
        return True

    def record_success(self) -> None:
        self.failure_count = 0

    def record_failure(self) -> None:
        self.failure_count += 1
        if self.failure_count >= self.threshold:
            self.open_until = time.monotonic() + self.cooldown_seconds


@dataclass(slots=True)
class PolicyState:
    rate_limiter: TokenBucketRateLimiter
    circuit_breaker: CircuitBreaker


def build_policy_state(policy: FetchPolicy) -> PolicyState:
    return PolicyState(
        rate_limiter=TokenBucketRateLimiter(policy.rate_limit_per_minute),
        circuit_breaker=CircuitBreaker(
            threshold=policy.circuit_breaker_threshold,
            cooldown_seconds=policy.circuit_breaker_cooldown_seconds,
        ),
    )
