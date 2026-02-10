import numpy as np
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from fundus_recommend.config import settings
from fundus_recommend.models.db import Article


def run_dedup(session: Session) -> int:
    """Find near-duplicate articles by cosine similarity and assign cluster IDs.

    Returns the number of articles assigned to a cluster.
    """
    stmt = select(Article.id, Article.embedding).where(Article.embedding.is_not(None)).order_by(Article.id)
    rows = session.execute(stmt).all()
    if not rows:
        return 0

    ids = [r[0] for r in rows]
    embeddings = np.array([r[1] for r in rows])

    # Cosine similarity matrix (embeddings are already L2-normalized)
    sim_matrix = embeddings @ embeddings.T

    # Recompute from scratch each pass: clear stale assignments first.
    session.execute(update(Article).where(Article.embedding.is_not(None)).values(dedup_cluster_id=None))

    # Connected components over pairwise similarity graph.
    n = len(ids)
    visited = [False] * n
    cluster_map: dict[int, int] = {}

    for start in range(n):
        if visited[start]:
            continue

        stack = [start]
        component_indices: list[int] = []

        while stack:
            idx = stack.pop()
            if visited[idx]:
                continue
            visited[idx] = True
            component_indices.append(idx)

            neighbors = np.where(sim_matrix[idx] >= settings.dedup_threshold)[0]
            for neighbor in neighbors:
                if neighbor == idx or visited[neighbor]:
                    continue
                stack.append(int(neighbor))

        if len(component_indices) < 2:
            continue

        cluster_id = min(ids[i] for i in component_indices)
        for i in component_indices:
            cluster_map[ids[i]] = cluster_id

    for article_id, cluster_id in cluster_map.items():
        session.execute(update(Article).where(Article.id == article_id).values(dedup_cluster_id=cluster_id))

    session.commit()
    return len(cluster_map)
