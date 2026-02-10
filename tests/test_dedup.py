import unittest
from unittest.mock import patch

import numpy as np

from fundus_recommend.config import settings
from fundus_recommend.services.dedup import run_dedup


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeSession:
    def __init__(self, rows):
        self._rows = rows
        self.clear_called = 0
        self.clear_value = "unset"
        self.updates: dict[int, int | None] = {}
        self.operations: list[tuple[str, int | None, int | None]] = []
        self.committed = False

    def execute(self, statement):
        if getattr(statement, "is_select", False):
            return _FakeResult(self._rows)

        if getattr(statement, "is_update", False):
            value = next(iter(statement._values.values())).value
            criterion = statement._where_criteria[0]
            left_key = getattr(criterion.left, "key", None)

            if left_key == "embedding":
                self.clear_called += 1
                self.clear_value = value
                self.operations.append(("clear", None, value))
            elif left_key == "id":
                article_id = criterion.right.value
                self.updates[article_id] = value
                self.operations.append(("update", article_id, value))

        return _FakeResult([])

    def commit(self):
        self.committed = True


class DedupeTests(unittest.TestCase):
    def test_transitive_chain_clusters_into_single_component(self) -> None:
        # Similarity chain:
        # 1~2 = 0.80, 2~3 = 0.80, 1~3 = 0.28  -> all should cluster together.
        rows = [
            (1, np.array([1.0, 0.0])),
            (2, np.array([0.8, 0.6])),
            (3, np.array([0.28, 0.96])),
        ]
        session = _FakeSession(rows)

        with patch.object(settings, "dedup_threshold", 0.75):
            clustered = run_dedup(session)

        self.assertEqual(clustered, 3)
        self.assertEqual(session.clear_called, 1)
        self.assertIsNone(session.clear_value)
        self.assertEqual(session.operations[0][0], "clear")
        self.assertEqual(session.updates, {1: 1, 2: 1, 3: 1})
        self.assertTrue(session.committed)

    def test_stale_clusters_are_cleared_and_singletons_remain_unclustered(self) -> None:
        rows = [
            (10, np.array([1.0, 0.0])),
            (11, np.array([0.0, 1.0])),
        ]
        session = _FakeSession(rows)

        with patch.object(settings, "dedup_threshold", 0.90):
            clustered = run_dedup(session)

        self.assertEqual(clustered, 0)
        self.assertEqual(session.clear_called, 1)
        self.assertIsNone(session.clear_value)
        self.assertEqual(session.updates, {})
        self.assertTrue(session.committed)

    def test_threshold_sensitivity_changes_pair_clustering(self) -> None:
        # Dot product = 0.75
        rows = [
            (20, np.array([1.0, 0.0])),
            (21, np.array([0.75, 0.6614378277661477])),
        ]

        low_session = _FakeSession(rows)
        with patch.object(settings, "dedup_threshold", 0.70):
            low_clustered = run_dedup(low_session)

        self.assertEqual(low_clustered, 2)
        self.assertEqual(low_session.updates, {20: 20, 21: 20})

        high_session = _FakeSession(rows)
        with patch.object(settings, "dedup_threshold", 0.80):
            high_clustered = run_dedup(high_session)

        self.assertEqual(high_clustered, 0)
        self.assertEqual(high_session.updates, {})


if __name__ == "__main__":
    unittest.main()
