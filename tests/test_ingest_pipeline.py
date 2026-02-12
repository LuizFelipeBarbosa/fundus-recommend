from datetime import datetime, timezone
import unittest
from unittest.mock import patch

from fundus_recommend.ingest import pipeline
from fundus_recommend.ingest.types import AdapterType, PublisherConfig, PublisherCrawlResult, PublisherRunDiagnostics
from fundus_recommend.models.db import CrawlRun, CrawlRunPublisher


class _FakeSession:
    def __init__(self, run: CrawlRun):
        self.run = run
        self.added: list[object] = []
        self.commits = 0

    def get(self, model, key):
        if model is CrawlRun and key == self.run.id:
            return self.run
        return None

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.commits += 1


class _FakeSessionContext:
    def __init__(self, session):
        self.session = session

    def __enter__(self):
        return self.session

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeSessionFactory:
    def __init__(self, run: CrawlRun):
        self.session = _FakeSession(run)

    def __call__(self):
        return _FakeSessionContext(self.session)


class IngestPipelineTests(unittest.TestCase):
    def test_persist_run_results_updates_run_and_adds_rows(self) -> None:
        run = CrawlRun(id=10, run_label="test", requested_publishers=[], resolved_publishers=[], status="running")
        factory = _FakeSessionFactory(run)

        now = datetime.now(timezone.utc)
        results = [
            PublisherCrawlResult(
                publisher_id="cnn",
                inserted_article_ids=[1, 2],
                diagnostics=PublisherRunDiagnostics(
                    publisher_id="cnn",
                    display_name="CNN",
                    adapter="rss",
                    outcome="success",
                    inserted_count=2,
                    crawled_count=2,
                    skipped_count=0,
                    status_histogram={"200": 2},
                    started_at=now,
                    finished_at=now,
                ),
            ),
            PublisherCrawlResult(
                publisher_id="reuters",
                inserted_article_ids=[],
                diagnostics=PublisherRunDiagnostics(
                    publisher_id="reuters",
                    display_name="Reuters",
                    adapter="licensed_feed",
                    outcome="skipped",
                    inserted_count=0,
                    crawled_count=0,
                    skipped_count=1,
                    status_histogram={"skip": 1},
                    skip_reason="missing_contract_or_feed",
                    started_at=now,
                    finished_at=now,
                ),
            ),
        ]

        with patch("fundus_recommend.ingest.pipeline.SyncSessionLocal", side_effect=factory):
            pipeline._persist_run_results(10, results)

        self.assertEqual(run.total_publishers, 2)
        self.assertEqual(run.succeeded_publishers, 1)
        self.assertEqual(run.skipped_publishers, 1)
        self.assertEqual(run.failed_publishers, 0)
        self.assertEqual(run.total_inserted, 2)
        self.assertEqual(run.status, "success")

        rows = [row for row in factory.session.added if isinstance(row, CrawlRunPublisher)]
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].status_histogram, {"200": 2})

    @patch("fundus_recommend.ingest.pipeline._persist_run_results")
    @patch("fundus_recommend.ingest.pipeline._create_run", return_value=77)
    @patch("fundus_recommend.ingest.pipeline._worker_crawl_and_insert")
    @patch("fundus_recommend.ingest.pipeline.resolve_publisher_tokens")
    def test_crawl_publishers_once_returns_results_and_persists(
        self,
        mock_resolve,
        mock_worker,
        _mock_create,
        mock_persist,
    ) -> None:
        config = PublisherConfig(
            publisher_id="cnn",
            display_name="CNN",
            adapter=AdapterType.RSS,
            feed_urls=("http://rss.cnn.com/rss/edition.rss",),
        )
        mock_resolve.return_value = ([config], [], [])
        now = datetime.now(timezone.utc)
        mock_worker.return_value = {
            "publisher_id": "cnn",
            "inserted_article_ids": [10],
            "diagnostics": {
                "publisher_id": "cnn",
                "display_name": "CNN",
                "adapter": "rss",
                "outcome": "success",
                "inserted_count": 1,
                "crawled_count": 1,
                "skipped_count": 0,
                "status_histogram": {"200": 1},
                "skip_reason": None,
                "error_message": None,
                "started_at": now.isoformat(),
                "finished_at": now.isoformat(),
            },
        }

        result = pipeline.crawl_publishers_once(
            publisher_tokens=["cnn"],
            max_articles=5,
            language=None,
            workers=1,
            run_label="test",
            emit_logs=False,
        )

        self.assertEqual(result.run_id, 77)
        self.assertEqual(len(result.publisher_results), 1)
        self.assertEqual(result.publisher_results[0].publisher_id, "cnn")
        self.assertEqual(result.publisher_results[0].inserted_article_ids, [10])
        mock_persist.assert_called_once()


if __name__ == "__main__":
    unittest.main()
