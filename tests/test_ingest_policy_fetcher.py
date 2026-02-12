import unittest
from unittest.mock import patch

from fundus_recommend.ingest.fetcher import HttpFetcher
from fundus_recommend.ingest.policy import build_policy_state
from fundus_recommend.ingest.types import FetchPolicy


class _Response:
    def __init__(self, status_code: int, text: str = "ok", url: str = "https://example.com") -> None:
        self.status_code = status_code
        self.text = text
        self.url = url


class IngestFetcherTests(unittest.TestCase):
    def test_fetcher_retries_transient_5xx(self) -> None:
        policy = FetchPolicy(
            timeout_seconds=5,
            max_retries=2,
            backoff_seconds=0.0,
            rate_limit_per_minute=1000,
            circuit_breaker_threshold=5,
            circuit_breaker_cooldown_seconds=60,
        )
        fetcher = HttpFetcher(policy)
        state = build_policy_state(policy)
        histogram: dict[str, int] = {}

        with patch("fundus_recommend.ingest.fetcher.requests.get", side_effect=[_Response(503), _Response(200)]):
            with patch("fundus_recommend.ingest.fetcher.time.sleep", return_value=None):
                response = fetcher.fetch("https://example.com", headers=None, state=state, histogram=histogram)

        self.assertTrue(response.ok)
        self.assertEqual(histogram.get("503"), 1)
        self.assertEqual(histogram.get("5xx"), 1)
        self.assertEqual(histogram.get("200"), 1)

    def test_circuit_breaker_short_circuits_after_repeated_403(self) -> None:
        policy = FetchPolicy(
            timeout_seconds=5,
            max_retries=0,
            backoff_seconds=0.0,
            rate_limit_per_minute=1000,
            circuit_breaker_threshold=2,
            circuit_breaker_cooldown_seconds=3600,
        )
        fetcher = HttpFetcher(policy)
        state = build_policy_state(policy)
        histogram: dict[str, int] = {}

        with patch("fundus_recommend.ingest.fetcher.requests.get", side_effect=[_Response(403), _Response(403)]) as mock_get:
            first = fetcher.fetch("https://example.com/1", headers=None, state=state, histogram=histogram)
            second = fetcher.fetch("https://example.com/2", headers=None, state=state, histogram=histogram)
            third = fetcher.fetch("https://example.com/3", headers=None, state=state, histogram=histogram)

        self.assertFalse(first.ok)
        self.assertFalse(second.ok)
        self.assertFalse(third.ok)
        self.assertEqual(mock_get.call_count, 2)
        self.assertEqual(third.error_kind, "circuit_open")
        self.assertEqual(histogram.get("403"), 2)
        self.assertEqual(histogram.get("circuit_open"), 1)


if __name__ == "__main__":
    unittest.main()
