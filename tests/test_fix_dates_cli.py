from dataclasses import dataclass
from datetime import datetime, timezone
import unittest
from unittest.mock import patch

from click.testing import CliRunner

from fundus_recommend.cli import fix_dates


@dataclass
class _FakeArticle:
    id: int
    publisher: str
    url: str
    publishing_date: datetime | None
    crawled_at: datetime | None


class _FakeScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return _FakeScalarResult(self._rows)


class _FakeSession:
    def __init__(self, articles, commit_counter):
        self.articles = articles
        self.commit_counter = commit_counter
        self.select_calls = 0

    def execute(self, statement):
        if not getattr(statement, "is_select", False):
            raise AssertionError("Expected only select statements in fix_dates tests")

        self.select_calls += 1
        if self.select_calls == 1:
            return _FakeResult(self.articles)
        return _FakeResult(self.articles)

    def commit(self):
        self.commit_counter["count"] += 1


class _FakeSessionContext:
    def __init__(self, session):
        self.session = session

    def __enter__(self):
        return self.session

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeSessionFactory:
    def __init__(self, articles):
        self.articles = articles
        self.commit_counter = {"count": 0}

    def __call__(self):
        return _FakeSessionContext(_FakeSession(self.articles, self.commit_counter))


class FixDatesCliTests(unittest.TestCase):
    def test_dry_run_finds_candidates_without_updating(self) -> None:
        articles = [
            _FakeArticle(
                id=1,
                publisher="Anadolu Ajansı",
                url="https://example.com/a",
                publishing_date=datetime(2026, 6, 2, tzinfo=timezone.utc),
                crawled_at=datetime(2026, 2, 6, 12, tzinfo=timezone.utc),
            ),
            _FakeArticle(
                id=2,
                publisher="Klasse Gegen Klasse",
                url="https://example.com/b",
                publishing_date=datetime(2026, 2, 5, tzinfo=timezone.utc),
                crawled_at=datetime(2026, 2, 6, 12, tzinfo=timezone.utc),
            ),
        ]
        factory = _FakeSessionFactory(articles)
        runner = CliRunner()

        with patch("fundus_recommend.cli.fix_dates.Base.metadata.create_all"), patch(
            "fundus_recommend.cli.fix_dates.SyncSessionLocal", side_effect=factory
        ):
            result = runner.invoke(fix_dates.main, [])

        self.assertEqual(result.exit_code, 0, msg=result.output)
        self.assertIn("Found 1 candidate row(s)", result.output)
        self.assertIn("Dry-run complete", result.output)
        self.assertEqual(factory.commit_counter["count"], 0)
        self.assertEqual(articles[0].publishing_date, datetime(2026, 6, 2, tzinfo=timezone.utc))

    def test_apply_updates_only_eligible_rows(self) -> None:
        articles = [
            _FakeArticle(
                id=1,
                publisher="Anadolu Ajansı",
                url="https://example.com/a",
                publishing_date=datetime(2026, 6, 2, tzinfo=timezone.utc),
                crawled_at=datetime(2026, 2, 6, 12, tzinfo=timezone.utc),
            ),
            _FakeArticle(
                id=2,
                publisher="Klasse Gegen Klasse",
                url="https://example.com/b",
                publishing_date=datetime(2026, 2, 5, tzinfo=timezone.utc),
                crawled_at=datetime(2026, 2, 6, 12, tzinfo=timezone.utc),
            ),
        ]
        factory = _FakeSessionFactory(articles)
        runner = CliRunner()

        with patch("fundus_recommend.cli.fix_dates.Base.metadata.create_all"), patch(
            "fundus_recommend.cli.fix_dates.SyncSessionLocal", side_effect=factory
        ):
            result = runner.invoke(fix_dates.main, ["--apply"])

        self.assertEqual(result.exit_code, 0, msg=result.output)
        self.assertIn("Updated 1 row(s).", result.output)
        self.assertEqual(factory.commit_counter["count"], 1)
        self.assertEqual(articles[0].publishing_date, datetime(2026, 2, 6, tzinfo=timezone.utc))
        self.assertEqual(articles[1].publishing_date, datetime(2026, 2, 5, tzinfo=timezone.utc))

    def test_apply_with_no_candidates_makes_no_updates(self) -> None:
        articles = [
            _FakeArticle(
                id=1,
                publisher="Anadolu Ajansı",
                url="https://example.com/a",
                publishing_date=datetime(2026, 2, 6, tzinfo=timezone.utc),
                crawled_at=datetime(2026, 2, 6, 12, tzinfo=timezone.utc),
            ),
        ]
        factory = _FakeSessionFactory(articles)
        runner = CliRunner()

        with patch("fundus_recommend.cli.fix_dates.Base.metadata.create_all"), patch(
            "fundus_recommend.cli.fix_dates.SyncSessionLocal", side_effect=factory
        ):
            result = runner.invoke(fix_dates.main, ["--apply"])

        self.assertEqual(result.exit_code, 0, msg=result.output)
        self.assertIn("Found 0 candidate row(s)", result.output)
        self.assertIn("No updates applied.", result.output)
        self.assertEqual(factory.commit_counter["count"], 0)
        self.assertEqual(articles[0].publishing_date, datetime(2026, 2, 6, tzinfo=timezone.utc))


if __name__ == "__main__":
    unittest.main()
