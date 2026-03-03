import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from fundus_recommend.ingest import pipeline
from fundus_recommend.ingest.types import CrawlArticleCandidate
from fundus_recommend.services.article_body_store import BodyStoreError


class _FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar(self):
        return self._value


class _FakeSession:
    def __init__(self, select_scalars: list[int | None] | None = None):
        self.select_scalars = list(select_scalars or [])
        self.added: list[object] = []
        self.commits = 0
        self.rollbacks = 0
        self._next_id = 100

    def execute(self, _statement):
        value = self.select_scalars.pop(0) if self.select_scalars else None
        return _FakeResult(value)

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                obj.id = self._next_id
                self._next_id += 1

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


class _FakeSessionContext:
    def __init__(self, session):
        self._session = session

    def __enter__(self):
        return self._session

    def __exit__(self, exc_type, exc, tb):
        return False


class IngestBodyStorageTests(unittest.TestCase):
    def _candidate(self) -> CrawlArticleCandidate:
        return CrawlArticleCandidate(
            url="https://example.com/a1",
            title="A1",
            body="Body content",
            publisher="Reuters",
            language="en",
            publishing_date=datetime(2026, 2, 20, tzinfo=timezone.utc),
            cover_image_url=None,
            authors=["Reporter"],
            topics=["news"],
        )

    def test_insert_candidates_dual_writes_r2_metadata(self) -> None:
        fake_session = _FakeSession(select_scalars=[None])

        with (
            patch("fundus_recommend.ingest.pipeline.SyncSessionLocal", return_value=_FakeSessionContext(fake_session)),
            patch.object(pipeline.settings, "article_body_storage_mode", "dual"),
            patch.object(pipeline.settings, "article_body_snippet_chars", 5),
            patch("fundus_recommend.ingest.pipeline.build_body_key", return_value="articles/100/key.txt"),
            patch("fundus_recommend.ingest.pipeline.put_body") as put_mock,
        ):
            inserted_ids = pipeline._insert_candidates([self._candidate()])

        self.assertEqual(inserted_ids, [100])
        self.assertEqual(fake_session.commits, 1)
        self.assertEqual(len(fake_session.added), 1)
        row = fake_session.added[0]
        self.assertEqual(row.body, "Body content")
        self.assertEqual(row.body_snippet, "Body ")
        self.assertEqual(row.body_storage_provider, "r2")
        self.assertEqual(row.body_storage_key, "articles/100/key.txt")
        put_mock.assert_called_once_with("articles/100/key.txt", "Body content")

    def test_insert_candidates_dual_falls_back_to_db_on_upload_error(self) -> None:
        fake_session = _FakeSession(select_scalars=[None])

        with (
            patch("fundus_recommend.ingest.pipeline.SyncSessionLocal", return_value=_FakeSessionContext(fake_session)),
            patch.object(pipeline.settings, "article_body_storage_mode", "dual"),
            patch("fundus_recommend.ingest.pipeline.build_body_key", return_value="articles/100/key.txt"),
            patch("fundus_recommend.ingest.pipeline.put_body", side_effect=BodyStoreError("boom")),
        ):
            inserted_ids = pipeline._insert_candidates([self._candidate()])

        self.assertEqual(inserted_ids, [100])
        row = fake_session.added[0]
        self.assertEqual(row.body, "Body content")
        self.assertEqual(row.body_storage_provider, "db")
        self.assertIsNone(row.body_storage_key)

    def test_insert_candidates_r2_primary_prunes_db_body_on_success(self) -> None:
        fake_session = _FakeSession(select_scalars=[None])

        with (
            patch("fundus_recommend.ingest.pipeline.SyncSessionLocal", return_value=_FakeSessionContext(fake_session)),
            patch.object(pipeline.settings, "article_body_storage_mode", "r2_primary"),
            patch("fundus_recommend.ingest.pipeline.build_body_key", return_value="articles/100/key.txt"),
            patch("fundus_recommend.ingest.pipeline.put_body"),
        ):
            inserted_ids = pipeline._insert_candidates([self._candidate()])

        self.assertEqual(inserted_ids, [100])
        row = fake_session.added[0]
        self.assertIsNone(row.body)
        self.assertEqual(row.body_storage_provider, "r2")
        self.assertEqual(row.body_storage_key, "articles/100/key.txt")


if __name__ == "__main__":
    unittest.main()
