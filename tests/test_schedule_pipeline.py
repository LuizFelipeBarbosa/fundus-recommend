import unittest
from unittest.mock import patch

from fundus_recommend.cli import schedule


class SchedulePipelineTests(unittest.TestCase):
    @patch("fundus_recommend.cli.schedule.refresh_stale_embeddings", return_value=0)
    @patch("fundus_recommend.cli.schedule.run_dedup_pass", return_value=0)
    @patch("fundus_recommend.cli.schedule.categorize_new_articles")
    @patch("fundus_recommend.cli.schedule.embed_new_articles")
    @patch("fundus_recommend.cli.schedule.translate_new_articles")
    @patch("fundus_recommend.cli.schedule.crawl_articles")
    def test_run_cycle_embeds_before_categorizes(
        self,
        mock_crawl,
        mock_translate,
        mock_embed,
        mock_categorize,
        _mock_dedup,
        _mock_refresh,
    ) -> None:
        events: list[str] = []
        mock_crawl.return_value = [1, 2]
        mock_translate.side_effect = lambda article_ids: events.append("translate") or len(article_ids)
        mock_embed.side_effect = lambda article_ids, batch_size: events.append("embed") or len(article_ids)
        mock_categorize.side_effect = lambda article_ids: events.append("categorize") or len(article_ids)

        schedule.run_cycle(["us"], max_articles=10, language=None, batch_size=64)

        self.assertEqual(events[:3], ["translate", "embed", "categorize"])
        mock_translate.assert_called_once_with([1, 2])
        mock_embed.assert_called_once_with([1, 2], 64)
        mock_categorize.assert_called_once_with([1, 2])

    @patch("fundus_recommend.cli.schedule.refresh_stale_embeddings", return_value=0)
    @patch("fundus_recommend.cli.schedule.run_dedup_pass", return_value=0)
    @patch("fundus_recommend.cli.schedule.categorize_new_articles")
    @patch("fundus_recommend.cli.schedule.embed_new_articles")
    @patch("fundus_recommend.cli.schedule.translate_new_articles")
    @patch("fundus_recommend.cli.schedule.crawl_articles")
    def test_run_cycle_skips_downstream_steps_when_no_new_articles(
        self,
        mock_crawl,
        mock_translate,
        mock_embed,
        mock_categorize,
        _mock_dedup,
        _mock_refresh,
    ) -> None:
        mock_crawl.return_value = []

        schedule.run_cycle(["us"], max_articles=10, language=None, batch_size=64)

        mock_translate.assert_not_called()
        mock_embed.assert_not_called()
        mock_categorize.assert_not_called()


if __name__ == "__main__":
    unittest.main()
