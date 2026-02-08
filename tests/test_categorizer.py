import unittest
from unittest.mock import patch

import numpy as np

from fundus_recommend.services import categorizer


class SemanticCategorizerTests(unittest.TestCase):
    def setUp(self) -> None:
        categorizer._get_prototype_embeddings.cache_clear()

    def tearDown(self) -> None:
        categorizer._get_prototype_embeddings.cache_clear()

    @patch("fundus_recommend.services.categorizer._get_prototype_embeddings")
    def test_assigns_us_for_strong_us_embedding(self, mock_prototypes) -> None:
        size = len(categorizer.CATEGORY_PRIORITY)
        mock_prototypes.return_value = np.eye(size)
        embedding = np.zeros(size)
        embedding[0] = 1.0

        with patch.object(categorizer.settings, "category_semantic_min_score", 0.3), patch.object(
            categorizer.settings, "category_semantic_min_margin", 0.04
        ):
            category = categorizer.assign_category(embedding=embedding)

        self.assertEqual(category, "US")

    @patch("fundus_recommend.services.categorizer._get_prototype_embeddings")
    def test_assigns_technology_for_strong_tech_embedding(self, mock_prototypes) -> None:
        size = len(categorizer.CATEGORY_PRIORITY)
        mock_prototypes.return_value = np.eye(size)
        embedding = np.zeros(size)
        embedding[categorizer.CATEGORY_PRIORITY.index("Technology")] = 1.0

        with patch.object(categorizer.settings, "category_semantic_min_score", 0.3), patch.object(
            categorizer.settings, "category_semantic_min_margin", 0.04
        ):
            category = categorizer.assign_category(embedding=embedding)

        self.assertEqual(category, "Technology")

    @patch("fundus_recommend.services.categorizer._get_prototype_embeddings")
    def test_returns_general_when_top_score_below_threshold(self, mock_prototypes) -> None:
        size = len(categorizer.CATEGORY_PRIORITY)
        mock_prototypes.return_value = np.zeros((size, size))
        embedding = np.zeros(size)
        embedding[0] = 1.0

        with patch.object(categorizer.settings, "category_semantic_min_score", 0.35), patch.object(
            categorizer.settings, "category_semantic_min_margin", 0.04
        ):
            category = categorizer.assign_category(embedding=embedding)

        self.assertEqual(category, "General")

    @patch("fundus_recommend.services.categorizer._get_prototype_embeddings")
    def test_returns_general_when_margin_is_too_small(self, mock_prototypes) -> None:
        size = len(categorizer.CATEGORY_PRIORITY)
        mock_prototypes.return_value = np.eye(size)
        embedding = np.zeros(size)
        embedding[0] = 1.0
        embedding[1] = 0.99

        with patch.object(categorizer.settings, "category_semantic_min_score", 0.1), patch.object(
            categorizer.settings, "category_semantic_min_margin", 0.04
        ):
            category = categorizer.assign_category(embedding=embedding)

        self.assertEqual(category, "General")

    @patch("fundus_recommend.services.categorizer._get_prototype_embeddings")
    def test_is_deterministic_for_fixed_mock_embeddings(self, mock_prototypes) -> None:
        size = len(categorizer.CATEGORY_PRIORITY)
        mock_prototypes.return_value = np.eye(size)
        embedding = np.zeros(size)
        embedding[categorizer.CATEGORY_PRIORITY.index("Business")] = 1.0

        with patch.object(categorizer.settings, "category_semantic_min_score", 0.3), patch.object(
            categorizer.settings, "category_semantic_min_margin", 0.04
        ):
            first = categorizer.assign_category(embedding=embedding)
            second = categorizer.assign_category(embedding=embedding)

        self.assertEqual(first, second)
        self.assertEqual(first, "Business")

    @patch("fundus_recommend.services.categorizer._get_prototype_embeddings")
    @patch("fundus_recommend.services.categorizer.embed_single")
    def test_uses_text_fallback_when_embedding_missing(self, mock_embed_single, mock_prototypes) -> None:
        size = len(categorizer.CATEGORY_PRIORITY)
        mock_prototypes.return_value = np.eye(size)
        vector = np.zeros(size)
        vector[categorizer.CATEGORY_PRIORITY.index("Technology")] = 1.0
        mock_embed_single.return_value = vector

        with patch.object(categorizer.settings, "category_semantic_min_score", 0.3), patch.object(
            categorizer.settings, "category_semantic_min_margin", 0.04
        ):
            category = categorizer.assign_category(
                embedding=None,
                title="AI chip launch",
                body_snippet="A new semiconductor platform was announced.",
                title_en=None,
            )

        mock_embed_single.assert_called_once()
        self.assertEqual(category, "Technology")


if __name__ == "__main__":
    unittest.main()
