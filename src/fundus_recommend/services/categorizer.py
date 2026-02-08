from __future__ import annotations

from functools import lru_cache

import numpy as np

from fundus_recommend.config import settings
from fundus_recommend.services.embeddings import embed_single, embed_texts, make_embedding_text

# Priority order also defines tie-breaking when semantic scores are equal.
CATEGORY_PRIORITY = ["US", "Global", "Business", "Technology", "Arts", "Sports", "Entertainment"]

CATEGORY_PROTOTYPES: dict[str, str] = {
    "US": (
        "US domestic politics, congress, senate, white house, supreme court, "
        "elections, federal policy, state governors"
    ),
    "Global": (
        "international relations, geopolitics, diplomacy, wars, foreign policy, "
        "NATO, UN, cross-border conflicts"
    ),
    "Business": (
        "business, markets, finance, earnings, companies, banking, inflation, "
        "federal reserve, economic indicators"
    ),
    "Technology": (
        "technology, AI, software, hardware, semiconductors, cybersecurity, "
        "startups, space technology"
    ),
    "Arts": (
        "arts, books, museums, theater, music, film criticism, exhibitions, "
        "cultural institutions"
    ),
    "Sports": (
        "sports competitions, leagues, teams, athletes, tournaments, scores, "
        "championships, transfers"
    ),
    "Entertainment": (
        "entertainment industry, celebrities, streaming, TV, movies, pop culture, "
        "gaming, lifestyle media"
    ),
}


def _normalize_vector(vector: np.ndarray) -> np.ndarray:
    normalized = np.asarray(vector, dtype=float).reshape(-1)
    norm = np.linalg.norm(normalized)
    if norm == 0:
        return normalized
    return normalized / norm


@lru_cache(maxsize=1)
def _get_prototype_embeddings() -> np.ndarray:
    """Return normalized category prototype embeddings in CATEGORY_PRIORITY order."""
    texts = [CATEGORY_PROTOTYPES[category] for category in CATEGORY_PRIORITY]
    vectors = np.asarray(embed_texts(texts), dtype=float)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    return vectors / norms


def _resolve_article_embedding(
    embedding: np.ndarray | list[float] | tuple[float, ...] | None,
    title: str,
    body_snippet: str,
    title_en: str | None,
) -> np.ndarray | None:
    if embedding is not None:
        article_vector = _normalize_vector(np.asarray(embedding, dtype=float))
        if article_vector.size > 0 and np.linalg.norm(article_vector) > 0:
            return article_vector

    if not (title or body_snippet or title_en):
        return None

    fallback_text = make_embedding_text(title, body_snippet, title_en=title_en)
    fallback_vector = _normalize_vector(np.asarray(embed_single(fallback_text), dtype=float))
    if fallback_vector.size == 0 or np.linalg.norm(fallback_vector) == 0:
        return None
    return fallback_vector


def _select_category(scores: np.ndarray, min_score: float, min_margin: float) -> str:
    if scores.size == 0:
        return "General"

    top_index = int(np.argmax(scores))
    top_score = float(scores[top_index])
    runner_up = float(np.partition(scores, -2)[-2]) if scores.size > 1 else -1.0
    margin = top_score - runner_up

    if top_score < min_score or margin < min_margin:
        return "General"
    return CATEGORY_PRIORITY[top_index]


def assign_category(
    embedding: np.ndarray | list[float] | tuple[float, ...] | None = None,
    title: str = "",
    body_snippet: str = "",
    title_en: str | None = None,
) -> str:
    """Assign a semantic category from embedding similarity with confidence fallback.

    The classifier compares an article embedding against fixed category prototype
    embeddings. If no usable embedding is provided, it falls back to embedding the
    article text (title + body snippet). Low-confidence results are mapped to
    "General" using score and score-margin thresholds from settings.
    """
    article_vector = _resolve_article_embedding(embedding, title, body_snippet, title_en)
    if article_vector is None:
        return "General"

    prototype_matrix = _get_prototype_embeddings()
    scores = prototype_matrix @ article_vector

    return _select_category(
        scores=scores,
        min_score=settings.category_semantic_min_score,
        min_margin=settings.category_semantic_min_margin,
    )
