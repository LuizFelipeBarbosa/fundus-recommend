from collections import Counter
import unittest
from unittest.mock import patch

from click.testing import CliRunner

from fundus_recommend.cli import classify


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeSession:
    def __init__(self, select_batches):
        self._select_batches = list(select_batches)
        self._select_calls = 0
        self.update_statements = 0
        self.commit_calls = 0

    def execute(self, statement):
        if getattr(statement, "is_select", False):
            if self._select_calls < len(self._select_batches):
                rows = self._select_batches[self._select_calls]
            else:
                rows = []
            self._select_calls += 1
            return _FakeResult(rows)

        if getattr(statement, "is_update", False):
            self.update_statements += 1
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


class ClassifyCliTests(unittest.TestCase):
    def test_classify_all_articles_processes_in_batches(self) -> None:
        rows_batch_1 = [
            (1, "Title 1", "Body 1", None, [1.0, 0.0, 0.0]),
            (2, "Title 2", "Body 2", None, [0.0, 1.0, 0.0]),
        ]
        rows_batch_2 = [
            (3, "Title 3", "Body 3", "Translated", None),
        ]
        fake_session = _FakeSession([rows_batch_1, rows_batch_2, []])

        def fake_session_local():
            return _FakeSessionContext(fake_session)

        def fake_assign_category(embedding=None, title="", body_snippet="", title_en=None):
            return "General" if embedding is None else "Technology"

        with patch("fundus_recommend.cli.classify.SyncSessionLocal", side_effect=fake_session_local), patch(
            "fundus_recommend.cli.classify.assign_category", side_effect=fake_assign_category
        ):
            total, counts = classify.classify_all_articles(batch_size=2)

        self.assertEqual(total, 3)
        self.assertEqual(counts["Technology"], 2)
        self.assertEqual(counts["General"], 1)
        self.assertEqual(fake_session.update_statements, 3)
        self.assertEqual(fake_session.commit_calls, 2)

    def test_cli_prints_summary(self) -> None:
        runner = CliRunner()

        with patch("fundus_recommend.cli.classify.Base.metadata.create_all"), patch(
            "fundus_recommend.cli.classify.classify_all_articles",
            return_value=(5, Counter({"Technology": 3, "General": 2})),
        ):
            result = runner.invoke(classify.main, ["--batch-size", "10"])

        self.assertEqual(result.exit_code, 0, msg=result.output)
        self.assertIn("Done. Reclassified 5 articles.", result.output)
        self.assertIn("Technology: 3", result.output)
        self.assertIn("General assignments: 2", result.output)


if __name__ == "__main__":
    unittest.main()
