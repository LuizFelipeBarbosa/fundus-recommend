import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from fundus_recommend.api import articles
from fundus_recommend.services.article_body_store import BodyStoreError


def _article(
    article_id: int,
    *,
    body: str | None,
    body_storage_key: str | None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=article_id,
        url=f"https://example.com/{article_id}",
        title=f"Title {article_id}",
        title_en=None,
        authors=["Reporter"],
        topics=["news"],
        publisher="Reuters",
        language="en",
        publishing_date=datetime(2026, 2, 10, 12, 0, tzinfo=timezone.utc),
        cover_image_url=None,
        dedup_cluster_id=None,
        category="General",
        body=body,
        body_storage_key=body_storage_key,
    )


class ArticlesApiBodyStorageTests(unittest.IsolatedAsyncioTestCase):
    async def test_get_article_reads_body_from_r2_when_key_present(self) -> None:
        article_row = _article(1, body=None, body_storage_key="articles/1/k.txt")

        with (
            patch("fundus_recommend.api.articles.get_article_by_id", return_value=article_row),
            patch("fundus_recommend.api.articles.get_body", return_value="r2 body"),
        ):
            response = await articles.get_article(1, session=AsyncMock())

        self.assertEqual(response.id, 1)
        self.assertEqual(response.body, "r2 body")

    async def test_get_article_falls_back_to_db_body_when_r2_read_fails(self) -> None:
        article_row = _article(2, body="db body", body_storage_key="articles/2/k.txt")

        with (
            patch("fundus_recommend.api.articles.get_article_by_id", return_value=article_row),
            patch("fundus_recommend.api.articles.get_body", side_effect=BodyStoreError("read failure")),
        ):
            response = await articles.get_article(2, session=AsyncMock())

        self.assertEqual(response.id, 2)
        self.assertEqual(response.body, "db body")

    async def test_get_article_raises_503_when_no_body_available(self) -> None:
        article_row = _article(3, body=None, body_storage_key="articles/3/k.txt")

        with (
            patch("fundus_recommend.api.articles.get_article_by_id", return_value=article_row),
            patch("fundus_recommend.api.articles.get_body", side_effect=BodyStoreError("read failure")),
        ):
            with self.assertRaises(HTTPException) as exc:
                await articles.get_article(3, session=AsyncMock())

        self.assertEqual(exc.exception.status_code, 503)


if __name__ == "__main__":
    unittest.main()
