from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np


@dataclass
class RankingWeights:
    freshness: float = 0.4
    prominence: float = 0.35
    authority: float = 0.2
    engagement: float = 0.05
    diversity_lambda: float = 0.3
    half_life_hours: float = 48.0


def freshness_score(publishing_date: datetime | None, now: datetime, half_life_hours: float) -> float:
    if publishing_date is None:
        return 0.0
    if publishing_date.tzinfo is None:
        publishing_date = publishing_date.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    age_hours = max((now - publishing_date).total_seconds() / 3600.0, 0.0)
    decay_rate = math.log(2) / half_life_hours
    return math.exp(-decay_rate * age_hours)


def engagement_score(view_count: int, max_views: int) -> float:
    if max_views <= 0:
        return 0.0
    return math.log(1 + view_count) / math.log(1 + max_views)


def prominence_score(cluster_size: int, max_cluster_size: int) -> float:
    if max_cluster_size <= 1:
        return 0.0
    return math.log(1 + cluster_size) / math.log(1 + max_cluster_size)


def composite_scores(
    dates: list[datetime | None],
    views: list[int],
    weights: RankingWeights,
    cluster_sizes: list[int] | None = None,
    authorities: list[float] | None = None,
) -> np.ndarray:
    now = datetime.now(timezone.utc)
    n = len(dates)
    scores = np.zeros(n)
    max_views = max(views) if views else 0
    max_cluster = max(cluster_sizes) if cluster_sizes else 1

    for i in range(n):
        f = freshness_score(dates[i], now, weights.half_life_hours)
        e = engagement_score(views[i], max_views)
        p = prominence_score(cluster_sizes[i], max_cluster) if cluster_sizes else 0.0
        a = authorities[i] if authorities else 0.0
        scores[i] = weights.freshness * f + weights.prominence * p + weights.authority * a + weights.engagement * e

    return scores


def mmr_rerank(
    scores: np.ndarray,
    embeddings: np.ndarray,
    page_size: int,
    offset: int = 0,
    lam: float = 0.3,
    cluster_ids: list[int | None] | None = None,
) -> list[int]:
    n = len(scores)
    if n == 0:
        return []

    k = min(offset + page_size, n)

    # Normalize embeddings for dot-product similarity
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)
    normed = embeddings / norms

    # Precompute NxN similarity matrix
    sim_matrix = normed @ normed.T

    # Zero out similarity between articles in the same dedup cluster
    # so same-story coverage from different publishers isn't penalized
    if cluster_ids is not None:
        for i in range(n):
            if cluster_ids[i] is None:
                continue
            for j in range(i + 1, n):
                if cluster_ids[j] == cluster_ids[i]:
                    sim_matrix[i, j] = 0.0
                    sim_matrix[j, i] = 0.0

    # Normalize scores to [0, 1]
    score_min = scores.min()
    score_max = scores.max()
    if score_max > score_min:
        norm_scores = (scores - score_min) / (score_max - score_min)
    else:
        norm_scores = np.ones(n)

    selected: list[int] = []
    candidates = set(range(n))
    max_sim_to_selected = np.full(n, -np.inf)

    for _ in range(k):
        best_idx = -1
        best_val = -np.inf

        for idx in candidates:
            sim_penalty = max(max_sim_to_selected[idx], 0.0) if selected else 0.0
            val = lam * norm_scores[idx] - (1 - lam) * sim_penalty
            if val > best_val:
                best_val = val
                best_idx = idx

        if best_idx == -1:
            break

        selected.append(best_idx)
        candidates.discard(best_idx)

        # Update max similarity to selected set
        np.maximum(max_sim_to_selected, sim_matrix[best_idx], out=max_sim_to_selected)

    return selected[offset:]
