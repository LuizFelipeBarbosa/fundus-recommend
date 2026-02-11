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
    async def test_get_ranked_stories_prioritizes_tier1_anchored_stories(self) -> None:
        candidates = [
            _article(1, 100, "Reuters", 12),
            _article(2, 100, "Nytimes", 11),
            _article(5, 200, "Politico", 12),
            _article(6, 200, "Local Gazette 1", 11),
            _article(7, 200, "Local Gazette 2", 10),
            _article(8, 300, "Reuters", 9),
        ]
        all_cluster_articles = [
            _article(1, 100, "Reuters", 12),
            _article(2, 100, "Nytimes", 11),
            _article(3, 100, "Politico", 13),
            _article(4, 100, "Local Gazette 3", 10),
            _article(5, 200, "Politico", 12),
            _article(6, 200, "Local Gazette 1", 11),
            _article(7, 200, "Local Gazette 2", 10),
            _article(8, 300, "Reuters", 9),
        ]
        expanded_story_articles = [
            _article(1, 100, "Reuters", 12),
            _article(2, 100, "Nytimes", 11),
            _article(3, 100, "Politico", 13),
            _article(4, 100, "Local Gazette 3", 10),
            _article(5, 200, "Politico", 12),
            _article(6, 200, "Local Gazette 1", 11),
            _article(7, 200, "Local Gazette 2", 10),
            _article(8, 300, "Reuters", 9),
        ]

        session = AsyncMock()
        session.execute.side_effect = [
            _FakeExecuteResult(candidates),
            _FakeExecuteResult(all_cluster_articles),
            _FakeExecuteResult(expanded_story_articles),
        ]

        with (
            patch("fundus_recommend.db.queries.get_view_counts", return_value={}),
            patch(
                "fundus_recommend.db.queries.composite_scores",
                return_value=np.array([0.80, 0.90, 0.99, 0.20, 0.10, 0.95]),
            ),
        ):
            stories, total = await get_ranked_stories(session, page=1, page_size=5)

        # All three clusters now appear (cluster:300 is a single-source story)
        self.assertEqual(total, 3)
        self.assertEqual(
            [story.story_id for story in stories],
            ["cluster:100", "cluster:200", "cluster:300"],
        )
        self.assertEqual(stories[0].lead_article.id, 2)
        self.assertEqual([article.id for article in stories[0].articles], [2, 1, 3, 4])
        self.assertEqual(stories[1].lead_article.id, 5)
        self.assertEqual([article.id for article in stories[1].articles], [5, 6, 7])
        self.assertEqual(stories[2].lead_article.id, 8)
        self.assertEqual([article.id for article in stories[2].articles], [8])

    async def test_get_ranked_stories_includes_all_clusters(self) -> None:
        """All clusters are included regardless of tier composition — tier
        influences ranking, not eligibility."""
        candidates = [
            _article(10, 400, "Reuters", 12),
            _article(11, 500, "Politico", 11),
            _article(12, 600, "Politico", 10),
            _article(13, 600, "Local Outlet A", 9),
            _article(14, 600, "Local Outlet B", 8),
        ]
        cluster_articles = [
            _article(10, 400, "Reuters", 12),
            _article(40, 400, "Local Outlet C", 11),
            _article(11, 500, "Politico", 11),
            _article(50, 500, "Local Outlet D", 10),
            _article(12, 600, "Politico", 10),
            _article(13, 600, "Local Outlet A", 9),
            _article(14, 600, "Local Outlet B", 8),
        ]

        session = AsyncMock()
        session.execute.side_effect = [
            _FakeExecuteResult(candidates),
            _FakeExecuteResult(cluster_articles),
            _FakeExecuteResult(cluster_articles),
        ]

        with (
            patch("fundus_recommend.db.queries.get_view_counts", return_value={}),
            patch(
                "fundus_recommend.db.queries.composite_scores",
                return_value=np.array([0.95, 0.94, 0.93, 0.40, 0.30]),
            ),
        ):
            stories, total = await get_ranked_stories(session, page=1, page_size=5)

        # All three clusters included: 600 (best coverage), 400 (Tier 1 lead), 500
        self.assertEqual(total, 3)
        self.assertEqual(
            [story.story_id for story in stories],
            ["cluster:600", "cluster:400", "cluster:500"],
        )
        self.assertEqual(stories[0].lead_article.id, 12)
        self.assertEqual(stories[1].lead_article.id, 10)
        self.assertEqual(stories[2].lead_article.id, 11)

    async def test_get_ranked_stories_includes_standalone_articles(self) -> None:
        """Standalone articles (no dedup cluster) appear as single-source stories."""
        candidates = [
            _article(20, None, "Reuters", 12),
            _article(21, None, "Politico", 11),
            _article(22, 700, "Nytimes", 10),
            _article(23, 700, "Local Outlet E", 9),
        ]
        cluster_articles = [
            _article(22, 700, "Nytimes", 10),
            _article(23, 700, "Local Outlet E", 9),
        ]

        session = AsyncMock()
        session.execute.side_effect = [
            _FakeExecuteResult(candidates),
            _FakeExecuteResult(cluster_articles),
            _FakeExecuteResult(cluster_articles),
        ]

        with (
            patch("fundus_recommend.db.queries.get_view_counts", return_value={}),
            patch(
                "fundus_recommend.db.queries.composite_scores",
                return_value=np.array([0.90, 0.80, 0.85, 0.70]),
            ),
        ):
            stories, total = await get_ranked_stories(session, page=1, page_size=5)

        self.assertEqual(total, 3)
        story_ids = [story.story_id for story in stories]
        self.assertIn("article:20", story_ids)
        self.assertIn("article:21", story_ids)
        self.assertIn("cluster:700", story_ids)

        # Standalone stories have exactly one article
        standalone = next(s for s in stories if s.story_id == "article:20")
        self.assertEqual(len(standalone.articles), 1)
        self.assertEqual(standalone.lead_article.id, 20)


if __name__ == "__main__":
    unittest.main()
