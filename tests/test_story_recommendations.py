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
    async def test_recommend_stories_by_topic_applies_source_floor_and_expands_all_sources(self) -> None:
        candidates = [
            _article(1, 100, "Reuters", 12),  # source_count=3 (tier A)
            _article(2, 200, "AP", 11),  # source_count=2 (tier B) but highest popularity
            _article(3, None, "CNN", 10),  # source_count=1 (tier C)
        ]
        source_counts = [
            (100, 3),
            (200, 2),
        ]
        expanded_clusters = [
            _article(6, 100, "BBC", 13),
            _article(1, 100, "Reuters", 12),
            _article(7, 100, "Guardian", 11),
            _article(2, 200, "AP", 11),
            _article(8, 200, "Bloomberg", 10),
        ]

        session = AsyncMock()
        session.execute.side_effect = [
            _FakeExecuteResult(source_counts),
            _FakeExecuteResult(expanded_clusters),
        ]

        with (
            patch(
                "fundus_recommend.db.queries.semantic_search",
                return_value=[(article, 0.9) for article in candidates],
            ),
            patch("fundus_recommend.db.queries.get_view_counts", return_value={}),
            patch(
                "fundus_recommend.db.queries.composite_scores",
                return_value=np.array([0.50, 0.95, 0.90]),
            ),
            patch("fundus_recommend.db.queries.authority_score", return_value=1.0),
        ):
            results = await recommend_stories_by_topic(session, "ai policy", limit=2, candidate_limit=50)

        self.assertEqual(len(results), 2)
        self.assertEqual([story.story_id for story, _score in results], ["cluster:100", "cluster:200"])
        self.assertEqual([article.id for article in results[0][0].articles], [1, 6, 7])
        self.assertEqual([article.id for article in results[1][0].articles], [2, 8])

    async def test_recommend_stories_similar_excludes_source_story(self) -> None:
        source_article = _article(10, 500, "Reuters", 12, with_embedding=True)
        similar_candidates = [
            _article(11, 500, "AP", 11),  # same story as source; should be excluded
            _article(12, 600, "BBC", 10),
            _article(13, None, "CNN", 9),
        ]
        source_counts = [(600, 3)]
        expanded_cluster_600 = [
            _article(14, 600, "Sky News", 12),
            _article(12, 600, "BBC", 10),
            _article(15, 600, "Reuters", 9),
        ]

        session = AsyncMock()
        session.execute.side_effect = [
            _FakeExecuteResult(source_counts),
            _FakeExecuteResult(expanded_cluster_600),
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
                return_value=np.array([0.95, 0.90, 0.85]),
            ),
            patch("fundus_recommend.db.queries.authority_score", return_value=1.0),
        ):
            results = await recommend_stories_similar(session, 10, limit=2, candidate_limit=50)

        self.assertEqual([story.story_id for story, _score in results], ["cluster:600", "article:13"])
        self.assertEqual([article.id for article in results[0][0].articles], [12, 14, 15])

    async def test_get_personalized_story_feed_uses_preference_candidates_and_story_limit(self) -> None:
        preferences = [
            SimpleNamespace(topic="tech", weight=1.0),
            SimpleNamespace(topic="business", weight=0.8),
        ]

        tech_story = _article(1, 100, "Reuters", 12)
        standalone_story = _article(2, None, "Bloomberg", 9)
        business_story = _article(3, 200, "BBC", 11)
        source_counts = [
            (100, 3),
            (200, 2),
        ]
        expanded_selected_clusters = [
            _article(6, 100, "The Verge", 13),
            _article(1, 100, "Reuters", 12),
            _article(7, 100, "AP", 11),
            _article(3, 200, "BBC", 11),
            _article(8, 200, "FT", 10),
        ]

        session = AsyncMock()
        session.execute.side_effect = [
            _FakeExecuteResult(preferences),
            _FakeExecuteResult(source_counts),
            _FakeExecuteResult(expanded_selected_clusters),
        ]

        async def _semantic_side_effect(_session, topic: str, _limit: int):
            if topic == "tech":
                return [(tech_story, 0.9), (standalone_story, 0.8)]
            return [(tech_story, 0.85), (business_story, 0.84)]

        with (
            patch("fundus_recommend.db.queries.semantic_search", side_effect=_semantic_side_effect) as semantic_mock,
            patch("fundus_recommend.db.queries.get_view_counts", return_value={}),
            patch(
                "fundus_recommend.db.queries.composite_scores",
                return_value=np.array([0.90, 0.40, 0.80]),
            ),
            patch("fundus_recommend.db.queries.authority_score", return_value=1.0),
        ):
            results = await get_personalized_story_feed(session, "user-1", limit=2, candidate_limit_per_topic=5)

        self.assertEqual(semantic_mock.await_count, 2)
        self.assertEqual([story.story_id for story, _score in results], ["cluster:100", "cluster:200"])
        self.assertEqual(len(results), 2)  # story limit, not article limit
        self.assertEqual([article.id for article in results[0][0].articles], [1, 6, 7])

    async def test_recommend_stories_by_topic_prefers_higher_reputation_when_other_signals_match(self) -> None:
        candidates = [
            _article(1, 100, "Reuters", 12),
            _article(2, 200, "Unknown Blog", 12),
        ]
        source_counts = [
            (100, 3),
            (200, 3),
        ]
        expanded_clusters = [
            _article(1, 100, "Reuters", 12),
            _article(2, 200, "Unknown Blog", 12),
        ]

        session = AsyncMock()
        session.execute.side_effect = [
            _FakeExecuteResult(source_counts),
            _FakeExecuteResult(expanded_clusters),
        ]

        def _authority_side_effect(publisher: str) -> float:
            if publisher == "Reuters":
                return 1.0
            return 0.4

        with (
            patch(
                "fundus_recommend.db.queries.semantic_search",
                return_value=[(article, 0.9) for article in candidates],
            ),
            patch("fundus_recommend.db.queries.get_view_counts", return_value={}),
            patch(
                "fundus_recommend.db.queries.composite_scores",
                return_value=np.array([0.80, 0.80]),
            ),
            patch("fundus_recommend.db.queries.authority_score", side_effect=_authority_side_effect),
        ):
            results = await recommend_stories_by_topic(session, "elections", limit=2, candidate_limit=10)

        self.assertEqual([story.story_id for story, _score in results], ["cluster:100", "cluster:200"])

    async def test_recommend_stories_by_topic_prefers_higher_coverage_when_popularity_and_reputation_match(self) -> None:
        candidates = [
            _article(1, 100, "Reuters", 12),
            _article(2, 200, "Reuters", 12),
        ]
        source_counts = [
            (100, 5),
            (200, 3),
        ]
        expanded_clusters = [
            _article(1, 100, "Reuters", 12),
            _article(2, 200, "Reuters", 12),
        ]

        session = AsyncMock()
        session.execute.side_effect = [
            _FakeExecuteResult(source_counts),
            _FakeExecuteResult(expanded_clusters),
        ]

        with (
            patch(
                "fundus_recommend.db.queries.semantic_search",
                return_value=[(article, 0.9) for article in candidates],
            ),
            patch("fundus_recommend.db.queries.get_view_counts", return_value={}),
            patch(
                "fundus_recommend.db.queries.composite_scores",
                return_value=np.array([0.70, 0.70]),
            ),
            patch("fundus_recommend.db.queries.authority_score", return_value=1.0),
        ):
            results = await recommend_stories_by_topic(session, "markets", limit=2, candidate_limit=10)

        self.assertEqual([story.story_id for story, _score in results], ["cluster:100", "cluster:200"])


if __name__ == "__main__":
    unittest.main()
