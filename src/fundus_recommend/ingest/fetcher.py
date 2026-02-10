from __future__ import annotations

import random
import time
from dataclasses import dataclass

import requests

from fundus_recommend.ingest.policy import PolicyState
from fundus_recommend.ingest.types import FetchPolicy


@dataclass(slots=True)
class FetchResponse:
    ok: bool
    status_code: int | None
    text: str | None
    final_url: str
    error_kind: str | None = None
    error_message: str | None = None


def _inc(histogram: dict[str, int], key: str) -> None:
    histogram[key] = histogram.get(key, 0) + 1


class HttpFetcher:
    def __init__(self, policy: FetchPolicy) -> None:
        self.policy = policy

    def _sleep_backoff(self, attempt: int) -> None:
        base = self.policy.backoff_seconds * (2**attempt)
        jitter = random.uniform(0.0, max(base * 0.25, 0.05))
        time.sleep(base + jitter)

    def fetch(
        self,
        url: str,
        headers: dict[str, str] | None,
        state: PolicyState,
        histogram: dict[str, int],
    ) -> FetchResponse:
        if not state.circuit_breaker.allow_request():
            _inc(histogram, "circuit_open")
            return FetchResponse(
                ok=False,
                status_code=None,
                text=None,
                final_url=url,
                error_kind="circuit_open",
                error_message="Circuit breaker is open",
            )

        max_attempts = max(1, self.policy.max_retries + 1)
        for attempt in range(max_attempts):
            state.rate_limiter.acquire()
            try:
                response = requests.get(url, headers=headers, timeout=self.policy.timeout_seconds, allow_redirects=True)
            except requests.Timeout as exc:
                _inc(histogram, "timeout")
                state.circuit_breaker.record_failure()
                if attempt < max_attempts - 1:
                    self._sleep_backoff(attempt)
                    continue
                return FetchResponse(False, None, None, url, "timeout", str(exc))
            except requests.ConnectionError as exc:
                _inc(histogram, "connection_error")
                state.circuit_breaker.record_failure()
                if attempt < max_attempts - 1:
                    self._sleep_backoff(attempt)
                    continue
                return FetchResponse(False, None, None, url, "connection_error", str(exc))
            except requests.RequestException as exc:
                _inc(histogram, "fetch_error")
                state.circuit_breaker.record_failure()
                return FetchResponse(False, None, None, url, "fetch_error", str(exc))

            status = int(response.status_code)
            _inc(histogram, str(status))
            if 500 <= status < 600:
                _inc(histogram, "5xx")

            if status >= 400:
                if status in {401, 403, 429} or 500 <= status < 600:
                    state.circuit_breaker.record_failure()
                retriable = status == 429 or 500 <= status < 600
                if retriable and attempt < max_attempts - 1:
                    self._sleep_backoff(attempt)
                    continue
                return FetchResponse(
                    ok=False,
                    status_code=status,
                    text=response.text,
                    final_url=str(response.url),
                    error_kind="http_error",
                    error_message=f"HTTP {status}",
                )

            state.circuit_breaker.record_success()
            return FetchResponse(ok=True, status_code=status, text=response.text, final_url=str(response.url))

        return FetchResponse(False, None, None, url, "unknown", "Exhausted attempts")
