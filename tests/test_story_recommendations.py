import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import numpy as np

from fundus_recommend.db.queries import (
    get_personalized_story_feed,
    recommend_stories_by_topic,
    recommend_stories_similar,
)


def _article(
    article_id: int,
    cluster_id: int | None,
    publisher: str,
    hour: int,
    *,
    with_embedding: bool = False,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=article_id,
        dedup_cluster_id=cluster_id,
        publisher=publisher,
        publishing_date=datetime(2026, 2, 10, hour, 0, tzinfo=timezone.utc),
        embedding=[0.1, 0.2] if with_embedding else None,
    )


class _FakeScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeExecuteResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return _FakeScalarResult(self._rows)

    def all(self):
        return self._rows


class StoryRecommendationsQueryTests(unittest.IsolatedAsyncioTestCase):
    async def test_recommend_stories_by_topic_uses_tier_policy_and_story_limit(self) -> None:
        candidates = [
            _article(1, 100, "Reuters", 12),
            _article(2, 100, "Nytimes", 11),
            _article(3, 100, "Politico", 10),
            _article(4, 100, "Local Desk A", 9),
            _article(5, 200, "Politico", 12),
            _article(6, 200, "Local Desk B", 11),
            _article(7, 200, "Local Desk C", 10),
        ]
        cluster_articles = [
            _article(1, 100, "Reuters", 12),
            _article(2, 100, "Nytimes", 11),
            _article(3, 100, "Politico", 10),
            _article(4, 100, "Local Desk A", 9),
            _article(5, 200, "Politico", 12),
            _article(6, 200, "Local Desk B", 11),
            _article(7, 200, "Local Desk C", 10),
        ]

        session = AsyncMock()
        session.execute.side_effect = [
            _FakeExecuteResult(cluster_articles),
            _FakeExecuteResult(cluster_articles),
        ]

        with (
            patch(
                "fundus_recommend.db.queries.semantic_search",
                return_value=[(article, 0.9) for article in candidates],
            ),
            patch("fundus_recommend.db.queries.get_view_counts", return_value={}),
            patch(
                "fundus_recommend.db.queries.composite_scores",
                return_value=np.array([0.88, 0.87, 0.86, 0.30, 0.99, 0.20, 0.10]),
            ),
        ):
            results = await recommend_stories_by_topic(session, "geopolitics", limit=2, candidate_limit=50)

        self.assertEqual([story.story_id for story, _score in results], ["cluster:100", "cluster:200"])
        self.assertEqual(results[0][0].lead_article.id, 1)
        self.assertEqual([article.id for article in results[0][0].articles], [1, 2, 3, 4])
        self.assertEqual(results[1][0].lead_article.id, 5)
        self.assertEqual([article.id for article in results[1][0].articles], [5, 6, 7])

    async def test_recommend_stories_similar_excludes_source_story(self) -> None:
        source_article = _article(10, 500, "Reuters", 12, with_embedding=True)
        similar_candidates = [
            _article(11, 500, "Nytimes", 11),  # excluded same story
            _article(12, 600, "Reuters", 10),
            _article(13, 600, "Politico", 9),
            _article(14, 600, "Local A", 8),
            _article(15, 700, "Politico", 10),
            _article(16, 700, "Local B", 9),
            _article(17, 700, "Local C", 8),
        ]
        cluster_articles = [
            _article(12, 600, "Reuters", 10),
            _article(13, 600, "Politico", 9),
            _article(14, 600, "Local A", 8),
            _article(15, 700, "Politico", 10),
            _article(16, 700, "Local B", 9),
            _article(17, 700, "Local C", 8),
        ]

        session = AsyncMock()
        session.execute.side_effect = [
            _FakeExecuteResult(cluster_articles),
            _FakeExecuteResult(cluster_articles),
        ]

        with (
            patch("fundus_recommend.db.queries.get_article_by_id", return_value=source_article),
            patch(
                "fundus_recommend.db.queries.recommend_similar",
                return_value=[(article, 0.9) for article in similar_candidates],
            ),
            patch("fundus_recommend.db.queries.get_view_counts", return_value={}),
            patch(
                "fundus_recommend.db.queries.composite_scores",
                return_value=np.array([0.95, 0.90, 0.88, 0.20, 0.89, 0.19, 0.18]),
            ),
        ):
            results = await recommend_stories_similar(session, 10, limit=3, candidate_limit=50)

        self.assertEqual([story.story_id for story, _score in results], ["cluster:600", "cluster:700"])

    async def test_get_personalized_story_feed_prefers_tier1_anchored_and_respects_limit(self) -> None:
        preferences = [
            SimpleNamespace(topic="policy", weight=1.0),
            SimpleNamespace(topic="markets", weight=0.8),
        ]

        tier1_cluster = [
            _article(1, 100, "Reuters", 12),
            _article(2, 100, "Politico", 11),
            _article(3, 100, "Local Source A", 10),
        ]
        fallback_cluster = [
            _article(4, 200, "Politico", 12),
            _article(5, 200, "Local Source B", 11),
            _article(6, 200, "Local Source C", 10),
        ]

        session = AsyncMock()
        session.execute.side_effect = [
            _FakeExecuteResult(preferences),
            _FakeExecuteResult([*tier1_cluster, *fallback_cluster]),
            _FakeExecuteResult([*tier1_cluster, *fallback_cluster]),
        ]

        async def _semantic_side_effect(_session, topic: str, _limit: int):
            if topic == "policy":
                return [(article, 0.9) for article in tier1_cluster]
            return [(article, 0.8) for article in fallback_cluster]

        with (
            patch("fundus_recommend.db.queries.semantic_search", side_effect=_semantic_side_effect) as semantic_mock,
            patch("fundus_recommend.db.queries.get_view_counts", return_value={}),
            patch(
                "fundus_recommend.db.queries.composite_scores",
                return_value=np.array([0.91, 0.90, 0.50, 0.99, 0.40, 0.30]),
            ),
        ):
            results = await get_personalized_story_feed(session, "user-1", limit=1, candidate_limit_per_topic=5)

        self.assertEqual(semantic_mock.await_count, 2)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0].story_id, "cluster:100")


if __name__ == "__main__":
    unittest.main()
