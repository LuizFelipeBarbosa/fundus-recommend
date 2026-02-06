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

    cluster_map: dict[int, int] = {}
    clustered_count = 0

    for i in range(len(ids)):
        if ids[i] in cluster_map:
            continue
        for j in range(i + 1, len(ids)):
            if ids[j] in cluster_map:
                continue
            if sim_matrix[i, j] >= settings.dedup_threshold:
                cluster_id = cluster_map.get(ids[i], ids[i])
                cluster_map[ids[i]] = cluster_id
                cluster_map[ids[j]] = cluster_id

    for article_id, cluster_id in cluster_map.items():
        session.execute(update(Article).where(Article.id == article_id).values(dedup_cluster_id=cluster_id))
        clustered_count += 1

    session.commit()
    return clustered_count
