import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from fundus_recommend.cli import schedule
from fundus_recommend.ingest.types import CrawlRunResult, PublisherCrawlResult, PublisherRunDiagnostics


def _publisher_result(publisher_id: str, inserted_ids: list[int]) -> PublisherCrawlResult:
    now = datetime.now(timezone.utc)
    return PublisherCrawlResult(
        publisher_id=publisher_id,
        inserted_article_ids=inserted_ids,
        diagnostics=PublisherRunDiagnostics(
            publisher_id=publisher_id,
            display_name=publisher_id,
            adapter="rss",
            outcome="success",
            inserted_count=len(inserted_ids),
            crawled_count=len(inserted_ids),
            skipped_count=0,
            status_histogram={"200": len(inserted_ids)},
            started_at=now,
            finished_at=now,
        ),
    )


class SchedulePipelineTests(unittest.TestCase):
    @patch("fundus_recommend.cli.schedule.refresh_stale_embeddings", return_value=0)
    @patch("fundus_recommend.cli.schedule.run_dedup_pass", return_value=0)
    @patch("fundus_recommend.cli.schedule.categorize_new_articles")
    @patch("fundus_recommend.cli.schedule.embed_new_articles")
    @patch("fundus_recommend.cli.schedule.translate_new_articles")
    @patch("fundus_recommend.cli.schedule.crawl_publishers_once")
    def test_run_cycle_embeds_before_categorizes(
        self,
        mock_crawl_once,
        mock_translate,
        mock_embed,
        mock_categorize,
        mock_dedup,
        _mock_refresh,
    ) -> None:
        events: list[str] = []
        mock_crawl_once.return_value = CrawlRunResult(
            run_id=1,
            publisher_results=[_publisher_result("cnn", [1, 2])],
        )
        mock_translate.side_effect = lambda article_ids: events.append("translate") or len(article_ids)
        mock_embed.side_effect = lambda article_ids, batch_size: events.append("embed") or len(article_ids)
        mock_categorize.side_effect = lambda article_ids: events.append("categorize") or len(article_ids)

        with patch("fundus_recommend.cli.schedule.get_dedup_stats", return_value=(0, 0, 0)):
            schedule.run_cycle(["cnn"], max_articles=10, language=None, batch_size=64, workers=1)

        self.assertEqual(events[:3], ["translate", "embed", "categorize"])
        mock_translate.assert_called_once_with([1, 2])
        mock_embed.assert_called_once_with([1, 2], 64)
        mock_categorize.assert_called_once_with([1, 2])
        mock_dedup.assert_called_once_with([1, 2])

    @patch("fundus_recommend.cli.schedule.refresh_stale_embeddings", return_value=0)
    @patch("fundus_recommend.cli.schedule.run_dedup_pass", return_value=0)
    @patch("fundus_recommend.cli.schedule.categorize_new_articles")
    @patch("fundus_recommend.cli.schedule.embed_new_articles")
    @patch("fundus_recommend.cli.schedule.translate_new_articles")
    @patch("fundus_recommend.cli.schedule.crawl_publishers_once")
    def test_run_cycle_skips_downstream_steps_when_no_new_articles(
        self,
        mock_crawl_once,
        mock_translate,
        mock_embed,
        mock_categorize,
        mock_dedup,
        _mock_refresh,
    ) -> None:
        mock_crawl_once.return_value = CrawlRunResult(
            run_id=1,
            publisher_results=[_publisher_result("cnn", [])],
        )

        with patch("fundus_recommend.cli.schedule.get_dedup_stats", return_value=(0, 0, 0)):
            schedule.run_cycle(["cnn"], max_articles=10, language=None, batch_size=64, workers=1)

        mock_translate.assert_not_called()
        mock_embed.assert_not_called()
        mock_categorize.assert_not_called()
        mock_dedup.assert_called_once_with([])


if __name__ == "__main__":
    unittest.main()
