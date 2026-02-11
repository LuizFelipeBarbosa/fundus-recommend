import numpy as np
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from fundus_recommend.config import settings
from fundus_recommend.models.db import Article


def run_dedup(session: Session, new_article_ids: list[int] | None = None) -> int:
    """Incremental dedup: compare new articles against the full corpus.

    Only articles listed in *new_article_ids* are checked for similarity.
    For each new article we find all neighbours above the cosine-similarity
    threshold and either join an existing cluster or create a new one.
    When a new article bridges two previously separate clusters the smaller
    cluster is merged into the larger one (by min-id convention).

    The similarity matrix is (new × all) instead of (all × all), so memory
    stays proportional to ``len(new_article_ids) * total_articles`` rather
    than ``total_articles²``.

    Returns the number of articles whose cluster assignment changed.
    """
    if not new_article_ids:
        return 0

    # --- load new-article embeddings ---
    new_stmt = (
        select(Article.id, Article.embedding)
        .where(Article.id.in_(new_article_ids), Article.embedding.is_not(None))
        .order_by(Article.id)
    )
    new_rows = session.execute(new_stmt).all()
    if not new_rows:
        return 0

    new_ids = [r[0] for r in new_rows]
    new_embeddings = np.array([r[1] for r in new_rows])

    # --- load full corpus embeddings + existing cluster assignments ---
    all_stmt = (
        select(Article.id, Article.embedding, Article.dedup_cluster_id)
        .where(Article.embedding.is_not(None))
        .order_by(Article.id)
    )
    all_rows = session.execute(all_stmt).all()
    all_ids = [r[0] for r in all_rows]
    all_embeddings = np.array([r[1] for r in all_rows])
    # current cluster state (article_id -> cluster_id)
    cluster_of: dict[int, int | None] = {r[0]: r[2] for r in all_rows}

    # --- similarity: new × all  (cosine; embeddings are L2-normalised) ---
    sim_matrix = new_embeddings @ all_embeddings.T  # shape (len(new), len(all))

    threshold = settings.dedup_threshold
    changed: set[int] = set()

    for i, new_id in enumerate(new_ids):
        neighbor_indices = np.where(sim_matrix[i] >= threshold)[0]
        neighbor_ids = [all_ids[int(j)] for j in neighbor_indices if all_ids[int(j)] != new_id]

        if not neighbor_ids:
            continue

        # Gather everyone in this group: the new article + its neighbours
        group = [new_id] + neighbor_ids

        # Collect existing cluster IDs present in the group
        cluster_ids_in_group: set[int] = set()
        for aid in group:
            cid = cluster_of.get(aid)
            if cid is not None:
                cluster_ids_in_group.add(cid)

        # Target cluster = smallest existing cluster id, or smallest article id
        target_cluster = min(cluster_ids_in_group) if cluster_ids_in_group else min(group)

        # Assign unclustered members of the group
        for aid in group:
            if cluster_of.get(aid) is None:
                cluster_of[aid] = target_cluster
                changed.add(aid)

        # Merge any other clusters into target (smaller id wins)
        for old_cluster in cluster_ids_in_group:
            if old_cluster == target_cluster:
                continue
            # Bulk-update in DB
            session.execute(
                update(Article)
                .where(Article.dedup_cluster_id == old_cluster)
                .values(dedup_cluster_id=target_cluster)
            )
            # Keep local map in sync
            for aid in list(cluster_of):
                if cluster_of[aid] == old_cluster:
                    cluster_of[aid] = target_cluster
                    changed.add(aid)

    # Persist new assignments for articles that weren't covered by the merge UPDATE
    for aid in changed:
        cid = cluster_of[aid]
        session.execute(update(Article).where(Article.id == aid).values(dedup_cluster_id=cid))

    session.commit()
    return len(changed)
