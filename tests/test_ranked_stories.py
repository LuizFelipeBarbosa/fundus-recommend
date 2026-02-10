import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import numpy as np

from fundus_recommend.db.queries import get_ranked_stories


def _article(article_id: int, cluster_id: int | None, publisher: str, hour: int) -> SimpleNamespace:
    return SimpleNamespace(
        id=article_id,
        dedup_cluster_id=cluster_id,
        publisher=publisher,
        publishing_date=datetime(2026, 2, 10, hour, 0, tzinfo=timezone.utc),
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


class RankedStoriesTests(unittest.IsolatedAsyncioTestCase):
    async def test_get_ranked_stories_collapses_clusters_and_expands_all_sources(self) -> None:
        candidates = [
            _article(1, 100, "Reuters", 12),
            _article(2, 100, "AP", 11),
            _article(3, 200, "BBC", 10),
            _article(4, None, "CNN", 9),
            _article(5, 200, "Al Jazeera", 8),
        ]
        source_counts = [
            (100, 3),
            (200, 3),
        ]
        # Includes extra source 6 for cluster 100 that is not in the ranked candidate list.
        cluster_members = [
            _article(6, 100, "The Verge", 13),
            _article(1, 100, "Reuters", 12),
            _article(2, 100, "AP", 11),
            _article(3, 200, "BBC", 10),
            _article(5, 200, "Al Jazeera", 8),
            _article(8, 200, "The Guardian", 7),
        ]

        session = AsyncMock()
        session.execute.side_effect = [
            _FakeExecuteResult(candidates),
            _FakeExecuteResult(source_counts),
            _FakeExecuteResult(cluster_members),
        ]

        with (
            patch("fundus_recommend.db.queries.get_view_counts", return_value={}),
            patch(
                "fundus_recommend.db.queries.composite_scores",
                return_value=np.array([0.91, 0.89, 0.88, 0.40, 0.30]),
            ),
            patch("fundus_recommend.db.queries.authority_score", return_value=1.0),
        ):
            stories, total = await get_ranked_stories(session, page=1, page_size=2)

        self.assertEqual(total, 3)
        self.assertEqual([story.story_id for story in stories], ["cluster:100", "cluster:200"])
        self.assertEqual(stories[0].lead_article.id, 1)
        self.assertEqual([article.id for article in stories[0].articles], [1, 6, 2])
        self.assertEqual(stories[1].lead_article.id, 3)
        self.assertEqual([article.id for article in stories[1].articles], [3, 5, 8])

    async def test_get_ranked_stories_source_floor_priority_then_stepwise_fallback(self) -> None:
        candidates = [
            _article(1, 100, "Reuters", 12),  # source_count=3 (tier A)
            _article(2, 200, "Reuters", 11),  # source_count=2 (tier B), but highest popularity
            _article(3, None, "Reuters", 10),  # source_count=1 (tier C)
        ]
        source_counts = [
            (100, 3),
            (200, 2),
        ]
        cluster_members = [
            _article(1, 100, "Reuters", 12),
            _article(9, 100, "AP", 11),
            _article(10, 100, "BBC", 10),
            _article(2, 200, "Reuters", 11),
            _article(11, 200, "AP", 10),
        ]

        session = AsyncMock()
        session.execute.side_effect = [
            _FakeExecuteResult(candidates),
            _FakeExecuteResult(source_counts),
            _FakeExecuteResult(cluster_members),
        ]

        with (
            patch("fundus_recommend.db.queries.get_view_counts", return_value={}),
            patch(
                "fundus_recommend.db.queries.composite_scores",
                return_value=np.array([0.50, 0.95, 0.90]),
            ),
            patch("fundus_recommend.db.queries.authority_score", return_value=1.0),
        ):
            stories, total = await get_ranked_stories(session, page=1, page_size=3)

        self.assertEqual(total, 3)
        self.assertEqual([story.story_id for story in stories], ["cluster:100", "cluster:200", "article:3"])
        self.assertEqual([article.id for article in stories[0].articles], [1, 9, 10])
        self.assertEqual([article.id for article in stories[1].articles], [2, 11])
        self.assertEqual([article.id for article in stories[2].articles], [3])

    async def test_get_ranked_stories_page_two_returns_singleton_story(self) -> None:
        candidates = [
            _article(1, 100, "Reuters", 12),
            _article(2, 100, "AP", 11),
            _article(3, 200, "BBC", 10),
            _article(4, None, "CNN", 9),
            _article(5, 200, "Al Jazeera", 8),
        ]
        source_counts = [
            (100, 3),
            (200, 2),
        ]

        session = AsyncMock()
        session.execute.side_effect = [
            _FakeExecuteResult(candidates),
            _FakeExecuteResult(source_counts),
        ]

        with (
            patch("fundus_recommend.db.queries.get_view_counts", return_value={}),
            patch(
                "fundus_recommend.db.queries.composite_scores",
                return_value=np.array([0.91, 0.89, 0.88, 0.40, 0.30]),
            ),
            patch("fundus_recommend.db.queries.authority_score", return_value=1.0),
        ):
            stories, total = await get_ranked_stories(session, page=2, page_size=2)

        self.assertEqual(total, 3)
        self.assertEqual(len(stories), 1)
        self.assertEqual(stories[0].story_id, "article:4")
        self.assertEqual([article.id for article in stories[0].articles], [4])


if __name__ == "__main__":
    unittest.main()
