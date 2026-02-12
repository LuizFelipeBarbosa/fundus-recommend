import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fundus_recommend.api import recommendations
from fundus_recommend.db.queries import RankedStory
from fundus_recommend.models.schemas import SearchResult, StoryRecommendationResult


def _article(article_id: int, cluster_id: int | None = None, publisher: str = "Reuters") -> SimpleNamespace:
    return SimpleNamespace(
        id=article_id,
        url=f"https://example.com/{article_id}",
        title=f"Title {article_id}",
        title_en=None,
        authors=["Reporter"],
        topics=["news"],
        publisher=publisher,
        language="en",
        publishing_date=datetime(2026, 2, 10, 12, 0, tzinfo=timezone.utc),
        cover_image_url=None,
        dedup_cluster_id=cluster_id,
        category="General",
    )


class RecommendationsApiTests(unittest.IsolatedAsyncioTestCase):
    async def test_story_recommendations_topic_returns_story_shape(self) -> None:
        lead = _article(1, 100)
        related = _article(2, 100, publisher="AP")
        ranked_story = RankedStory(
            story_id="cluster:100",
            dedup_cluster_id=100,
            lead_article=lead,
            articles=[lead, related],
        )

        with patch(
            "fundus_recommend.api.recommendations.recommend_stories_by_topic",
            return_value=[(ranked_story, 0.98765)],
        ):
            response = await recommendations.get_story_recommendations(
                topic="ai policy",
                similar_to=None,
                limit=10,
                session=AsyncMock(),
            )

        self.assertEqual(response.strategy, "topic:ai policy")
        self.assertEqual(len(response.results), 1)
        self.assertIsInstance(response.results[0], StoryRecommendationResult)
        self.assertEqual(response.results[0].story.story_id, "cluster:100")
        self.assertEqual(response.results[0].story.source_count, 2)
        self.assertEqual(response.results[0].score, 0.9877)

    async def test_story_recommendations_recent_fallback_uses_latest_news(self) -> None:
        mock_recommend = AsyncMock(return_value=[])
        with patch("fundus_recommend.api.recommendations.recommend_stories_by_topic", mock_recommend):
            response = await recommendations.get_story_recommendations(
                topic=None,
                similar_to=None,
                limit=5,
                session=AsyncMock(),
            )

        self.assertEqual(response.strategy, "recent")
        self.assertEqual(response.results, [])
        self.assertEqual(mock_recommend.await_count, 1)
        self.assertEqual(mock_recommend.await_args.args[1], "latest news")

    async def test_story_feed_returns_story_shape(self) -> None:
        lead = _article(5, 900)
        related = _article(6, 900, publisher="BBC")
        ranked_story = RankedStory(
            story_id="cluster:900",
            dedup_cluster_id=900,
            lead_article=lead,
            articles=[lead, related],
        )

        with patch(
            "fundus_recommend.api.recommendations.get_personalized_story_feed",
            return_value=[(ranked_story, 0.64231)],
        ):
            response = await recommendations.get_story_feed(
                user_id="user-1",
                limit=20,
                session=AsyncMock(),
            )

        self.assertEqual(response.strategy, "personalized:user-1")
        self.assertEqual(len(response.results), 1)
        self.assertEqual(response.results[0].story.story_id, "cluster:900")
        self.assertEqual(response.results[0].score, 0.6423)

    async def test_legacy_recommendations_endpoint_still_returns_articles(self) -> None:
        article = _article(11, None)
        with patch(
            "fundus_recommend.api.recommendations.recommend_by_topic",
            return_value=[(article, 0.12345)],
        ):
            response = await recommendations.get_recommendations(
                topic="climate",
                similar_to=None,
                limit=10,
                session=AsyncMock(),
            )

        self.assertEqual(response.strategy, "topic:climate")
        self.assertEqual(len(response.results), 1)
        self.assertIsInstance(response.results[0], SearchResult)
        self.assertEqual(response.results[0].article.id, 11)
        self.assertEqual(response.results[0].score, 0.1235)

    async def test_legacy_feed_endpoint_still_returns_articles(self) -> None:
        article = _article(21, 777)
        with patch(
            "fundus_recommend.api.recommendations.get_personalized_feed",
            return_value=[(article, 0.55666)],
        ):
            response = await recommendations.get_feed(
                user_id="legacy-user",
                limit=20,
                session=AsyncMock(),
            )

        self.assertEqual(response.strategy, "personalized:legacy-user")
        self.assertEqual(len(response.results), 1)
        self.assertIsInstance(response.results[0], SearchResult)
        self.assertEqual(response.results[0].article.id, 21)
        self.assertEqual(response.results[0].score, 0.5567)


if __name__ == "__main__":
    unittest.main()
