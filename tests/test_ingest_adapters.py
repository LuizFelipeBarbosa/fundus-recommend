import os
import unittest
from unittest.mock import patch

from fundus_recommend.ingest.adapters.licensed_feed import LicensedFeedAdapter
from fundus_recommend.ingest.adapters.official_api import OfficialAPIAdapter
from fundus_recommend.ingest.adapters.rss import RSSAdapter
from fundus_recommend.ingest.fetcher import FetchResponse, HttpFetcher
from fundus_recommend.ingest.policy import build_policy_state
from fundus_recommend.ingest.types import AdapterType, FetchPolicy, PublisherConfig


class _Response:
    def __init__(self, status_code: int, text: str = "", url: str = "https://example.com") -> None:
        self.status_code = status_code
        self.text = text
        self.url = url


class _FakeFetcher:
    def __init__(self, payloads: dict[str, FetchResponse]) -> None:
        self.payloads = payloads

    def fetch(self, url, headers, state, histogram):
        return self.payloads[url]


class IngestAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = FetchPolicy(
            timeout_seconds=5,
            max_retries=0,
            backoff_seconds=0.0,
            rate_limit_per_minute=1000,
            circuit_breaker_threshold=5,
            circuit_breaker_cooldown_seconds=60,
        )

    def test_rss_adapter_success(self) -> None:
        feed_url = "https://example.com/feed.xml"
        article_url = "https://example.com/article"

        feed_xml = f"""<?xml version=\"1.0\"?><rss><channel>
        <item><title>Headline</title><link>{article_url}</link><pubDate>Tue, 10 Feb 2026 00:00:00 GMT</pubDate></item>
        </channel></rss>"""
        article_html = """
        <html lang='en'>
          <head><title>Example Title</title><meta property='og:image' content='https://img.example.com/a.jpg'/></head>
          <body><p>This is a sufficiently long paragraph for extraction in tests.</p></body>
        </html>
        """

        config = PublisherConfig(
            publisher_id="test",
            display_name="Test Publisher",
            adapter=AdapterType.RSS,
            feed_urls=(feed_url,),
            default_language="en",
        )
        fetcher = _FakeFetcher(
            {
                feed_url: FetchResponse(ok=True, status_code=200, text=feed_xml, final_url=feed_url),
                article_url: FetchResponse(ok=True, status_code=200, text=article_html, final_url=article_url),
            }
        )

        adapter = RSSAdapter()
        out = adapter.crawl(
            config=config,
            max_articles=5,
            language=None,
            policy=self.policy,
            fetcher=fetcher,
            state=build_policy_state(self.policy),
            status_histogram={},
        )

        self.assertEqual(out.outcome, "success")
        self.assertEqual(len(out.candidates), 1)
        self.assertEqual(out.candidates[0].url, article_url)
        self.assertEqual(out.candidates[0].publisher, "Test Publisher")

    def test_rss_adapter_records_blocked_status_and_circuit_open(self) -> None:
        feed_url = "https://example.com/feed.xml"
        feed_xml = """<?xml version='1.0'?><rss><channel>
        <item><link>https://example.com/a1</link></item>
        <item><link>https://example.com/a2</link></item>
        <item><link>https://example.com/a3</link></item>
        </channel></rss>"""

        policy = FetchPolicy(
            timeout_seconds=5,
            max_retries=0,
            backoff_seconds=0.0,
            rate_limit_per_minute=1000,
            circuit_breaker_threshold=1,
            circuit_breaker_cooldown_seconds=600,
        )
        state = build_policy_state(policy)
        fetcher = HttpFetcher(policy)

        config = PublisherConfig(
            publisher_id="blocked",
            display_name="Blocked",
            adapter=AdapterType.RSS,
            feed_urls=(feed_url,),
        )

        with patch(
            "fundus_recommend.ingest.fetcher.requests.get",
            side_effect=[_Response(200, text=feed_xml, url=feed_url), _Response(403, text="blocked")],
        ):
            histogram: dict[str, int] = {}
            out = RSSAdapter().crawl(
                config=config,
                max_articles=5,
                language=None,
                policy=policy,
                fetcher=fetcher,
                state=state,
                status_histogram=histogram,
            )

        self.assertEqual(out.outcome, "success")
        self.assertEqual(len(out.candidates), 0)
        self.assertGreaterEqual(histogram.get("403", 0), 1)
        self.assertGreaterEqual(histogram.get("circuit_open", 0), 1)

    def test_official_api_stub_skips_without_credentials(self) -> None:
        config = PublisherConfig(
            publisher_id="nyt",
            display_name="New York Times",
            adapter=AdapterType.OFFICIAL_API,
            requires_credentials=True,
            credential_env="NYT_API_KEY",
        )

        with patch.dict(os.environ, {}, clear=False):
            out = OfficialAPIAdapter().crawl(
                config=config,
                max_articles=10,
                language=None,
                policy=self.policy,
                fetcher=_FakeFetcher({}),
                state=build_policy_state(self.policy),
                status_histogram={},
            )

        self.assertEqual(out.outcome, "skipped")
        self.assertEqual(out.skip_reason, "missing_credentials")

    def test_licensed_feed_stub_skips_without_feed_config(self) -> None:
        config = PublisherConfig(
            publisher_id="reuters",
            display_name="Reuters",
            adapter=AdapterType.LICENSED_FEED,
            requires_credentials=True,
            credential_env="REUTERS_LICENSED_FEED_URL",
        )

        with patch.dict(os.environ, {}, clear=False):
            out = LicensedFeedAdapter().crawl(
                config=config,
                max_articles=10,
                language=None,
                policy=self.policy,
                fetcher=_FakeFetcher({}),
                state=build_policy_state(self.policy),
                status_histogram={},
            )

        self.assertEqual(out.outcome, "skipped")
        self.assertEqual(out.skip_reason, "missing_contract_or_feed")


if __name__ == "__main__":
    unittest.main()
