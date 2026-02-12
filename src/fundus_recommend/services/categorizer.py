from __future__ import annotations

from functools import lru_cache

import numpy as np

from fundus_recommend.config import settings
from fundus_recommend.services.embeddings import embed_single, embed_texts, make_embedding_text

# Priority order also defines tie-breaking when semantic scores are equal.
CATEGORY_PRIORITY = ["US", "Global", "Business", "Technology", "Arts", "Sports", "Entertainment"]

# Each category uses multiple exemplar sentences that resemble real headlines.
# The embeddings are averaged to form a robust prototype centroid.
CATEGORY_EXEMPLARS: dict[str, list[str]] = {
    "US": [
        "US Congress passes bipartisan spending bill after Senate filibuster showdown",
        "President Biden addresses America on domestic policy from the White House",
        "US Supreme Court overturns ruling affecting abortion rights across American states",
        "Democrats and Republicans clash over immigration at the US-Mexico border",
        "Trump signs executive order on tariffs as American economy shows mixed signals",
    ],
    "Global": [
        "NATO allies agree to increase defense spending amid rising geopolitical tensions",
        "UN Security Council calls emergency session over escalating conflict in Middle East",
        "Diplomatic talks between world leaders aim to resolve cross-border dispute",
        "Ukraine peace negotiations accelerate as foreign ministers meet in Geneva",
        "European Union imposes sanctions on Russia over territorial aggression",
    ],
    "Business": [
        "Wall Street rallies as Fed signals pause on interest rate hikes",
        "Major tech company reports record quarterly earnings beating analyst estimates",
        "Oil prices surge after OPEC announces production cuts for next quarter",
        "Central bank raises interest rates to combat persistent inflation",
        "Global stock markets tumble on fears of an economic recession",
    ],
    "Technology": [
        "Big tech companies plan to spend billions on new AI data centers",
        "New semiconductor chip promises breakthrough in computing performance",
        "Cybersecurity firm warns of critical vulnerability in widely used software",
        "Startup raises funding to develop next-generation electric vehicle battery",
        "AI chatbot reaches milestone in natural language understanding benchmark",
    ],
    "Arts": [
        "New exhibition at the national museum explores modern art movements",
        "Acclaimed author wins prestigious literary prize for debut novel",
        "Orchestra performs sold-out concert featuring classical compositions",
        "Film critic reviews award-winning drama at international film festival",
        "Theater company stages bold new adaptation of a Shakespeare play",
    ],
    "Sports": [
        "Premier League title race heats up as top teams clash this weekend",
        "Olympic athlete breaks world record in swimming finals",
        "NBA playoffs begin with defending champions facing tough first-round matchup",
        "Tennis star advances to Grand Slam semifinal after five-set thriller",
        "National football team qualifies for World Cup after dramatic victory",
    ],
    "Entertainment": [
        "Streaming platform announces new original series from acclaimed director",
        "Pop star breaks streaming records with surprise album release",
        "Celebrity couple confirms relationship on social media to fan excitement",
        "Blockbuster movie sequel dominates box office on opening weekend",
        "Video game studio reveals trailer for highly anticipated sequel",
    ],
}


def _normalize_vector(vector: np.ndarray) -> np.ndarray:
    normalized = np.asarray(vector, dtype=float).reshape(-1)
    norm = np.linalg.norm(normalized)
    if norm == 0:
        return normalized
    return normalized / norm


@lru_cache(maxsize=1)
def _get_prototype_embeddings() -> np.ndarray:
    """Return normalized category prototype embeddings in CATEGORY_PRIORITY order.

    Each prototype is the mean of multiple exemplar embeddings for that category,
    producing a centroid that captures the breadth of the category.
    """
    all_texts: list[str] = []
    slices: list[tuple[int, int]] = []
    for category in CATEGORY_PRIORITY:
        exemplars = CATEGORY_EXEMPLARS[category]
        start = len(all_texts)
        all_texts.extend(exemplars)
        slices.append((start, len(all_texts)))

    all_vectors = np.asarray(embed_texts(all_texts), dtype=float)

    centroids = []
    for start, end in slices:
        centroid = all_vectors[start:end].mean(axis=0)
        centroids.append(centroid)

    matrix = np.stack(centroids)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    return matrix / norms


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
