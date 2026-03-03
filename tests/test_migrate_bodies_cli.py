import unittest
from unittest.mock import patch

from fundus_recommend.cli import migrate_bodies
from fundus_recommend.services.article_body_store import BodyStoreError


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeSession:
    def __init__(self, select_batches):
        self._select_batches = list(select_batches)
        self.update_params: list[dict] = []
        self.commit_calls = 0

    def execute(self, statement):
        if getattr(statement, "is_select", False):
            rows = self._select_batches.pop(0) if self._select_batches else []
            return _FakeResult(rows)
        if getattr(statement, "is_update", False):
            self.update_params.append(statement.compile().params)
            return _FakeResult([])
        raise AssertionError("Unexpected statement type")

    def commit(self):
        self.commit_calls += 1


class _FakeSessionContext:
    def __init__(self, session):
        self._session = session

    def __enter__(self):
        return self._session

    def __exit__(self, exc_type, exc, tb):
        return False


class MigrateBodiesCliTests(unittest.TestCase):
    def test_dry_run_makes_no_writes(self) -> None:
        session = _FakeSession([[(1, "https://example.com/1", "Body 1")], []])

        with (
            patch("fundus_recommend.cli.migrate_bodies.SyncSessionLocal", return_value=_FakeSessionContext(session)),
            patch("fundus_recommend.cli.migrate_bodies.build_body_key", return_value="articles/1/key.txt"),
            patch("fundus_recommend.cli.migrate_bodies.put_body") as put_mock,
        ):
            stats = migrate_bodies.migrate_bodies(dry_run=True, prune_db_body=True)

        self.assertEqual(stats["processed"], 1)
        self.assertEqual(stats["uploaded"], 1)
        self.assertEqual(stats["pruned"], 1)
        self.assertEqual(session.update_params, [])
        self.assertEqual(session.commit_calls, 0)
        put_mock.assert_not_called()

    def test_prune_db_body_updates_only_successful_uploads(self) -> None:
        session = _FakeSession(
            [[(1, "https://example.com/1", "Body 1"), (2, "https://example.com/2", "Body 2")], []]
        )

        with (
            patch("fundus_recommend.cli.migrate_bodies.SyncSessionLocal", return_value=_FakeSessionContext(session)),
            patch(
                "fundus_recommend.cli.migrate_bodies.build_body_key",
                side_effect=lambda article_id, _url: f"articles/{article_id}/key.txt",
            ),
            patch(
                "fundus_recommend.cli.migrate_bodies.put_body",
                side_effect=[None, BodyStoreError("upload failed")],
            ),
        ):
            stats = migrate_bodies.migrate_bodies(prune_db_body=True, max_errors=5)

        self.assertEqual(stats["processed"], 2)
        self.assertEqual(stats["uploaded"], 1)
        self.assertEqual(stats["pruned"], 1)
        self.assertEqual(stats["errors"], 1)
        self.assertEqual(session.commit_calls, 1)
        self.assertEqual(len(session.update_params), 1)
        self.assertEqual(session.update_params[0]["body_storage_key"], "articles/1/key.txt")
        self.assertEqual(session.update_params[0]["body_storage_provider"], "r2")
        self.assertIsNone(session.update_params[0]["body"])

    def test_rerun_is_idempotent(self) -> None:
        session_first = _FakeSession([[(1, "https://example.com/1", "Body 1")], []])
        session_second = _FakeSession([[]])
        session_contexts = [_FakeSessionContext(session_first), _FakeSessionContext(session_second)]

        with (
            patch("fundus_recommend.cli.migrate_bodies.SyncSessionLocal", side_effect=session_contexts),
            patch("fundus_recommend.cli.migrate_bodies.build_body_key", return_value="articles/1/key.txt"),
            patch("fundus_recommend.cli.migrate_bodies.put_body") as put_mock,
        ):
            first_run = migrate_bodies.migrate_bodies()
            second_run = migrate_bodies.migrate_bodies()

        self.assertEqual(first_run["uploaded"], 1)
        self.assertEqual(second_run["uploaded"], 0)
        self.assertEqual(second_run["processed"], 0)
        put_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
