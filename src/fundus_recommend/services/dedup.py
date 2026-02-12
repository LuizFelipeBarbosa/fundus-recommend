import time

import numpy as np
from sqlalchemy import select, update
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from fundus_recommend.config import settings
from fundus_recommend.models.db import Article


def run_dedup(
    session: Session,
    new_article_ids: list[int] | None = None,
    max_cluster_size: int = 200,
) -> int:
    """Incremental dedup: compare new articles against the full corpus.

    Only articles listed in *new_article_ids* are checked for similarity.
    For each new article we find all neighbours above the cosine-similarity
    threshold and either join an existing cluster or create a new one.
    When a new article bridges two previously separate clusters the smaller
    cluster is merged into the larger one (by min-id convention).

    Clusters are capped at *max_cluster_size* to prevent runaway
    transitive-chain growth.  Neighbours in oversized clusters are ignored,
    and merges that would exceed the cap are skipped.

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

    # --- cluster size tracking ---
    cluster_size: dict[int, int] = {}
    for r in all_rows:
        cid = r[2]
        if cid is not None:
            cluster_size[cid] = cluster_size.get(cid, 0) + 1

    # --- similarity: new × all  (cosine; embeddings are L2-normalised) ---
    sim_matrix = new_embeddings @ all_embeddings.T  # shape (len(new), len(all))

    threshold = settings.dedup_threshold
    changed: set[int] = set()

    for i, new_id in enumerate(new_ids):
        neighbor_indices = np.where(sim_matrix[i] >= threshold)[0]
        neighbor_ids = [all_ids[int(j)] for j in neighbor_indices if all_ids[int(j)] != new_id]

        if not neighbor_ids:
            continue

        # Ignore neighbours in clusters already at the size cap — these are
        # likely transitive-chain artefacts, not genuine duplicates.
        frozen = {cid for cid, sz in cluster_size.items() if sz >= max_cluster_size}
        neighbor_ids = [
            aid for aid in neighbor_ids
            if cluster_of.get(aid) not in frozen
        ]
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

        # Check if merging would exceed the cap
        combined = sum(cluster_size.get(cid, 0) for cid in cluster_ids_in_group)
        combined += sum(1 for aid in group if cluster_of.get(aid) is None)
        if combined > max_cluster_size:
            continue

        # Target cluster = smallest existing cluster id, or smallest article id
        target_cluster = min(cluster_ids_in_group) if cluster_ids_in_group else min(group)

        # Assign unclustered members of the group
        for aid in group:
            if cluster_of.get(aid) is None:
                cluster_of[aid] = target_cluster
                cluster_size[target_cluster] = cluster_size.get(target_cluster, 0) + 1
                changed.add(aid)

        # Merge any other clusters into target (smaller id wins)
        for old_cluster in cluster_ids_in_group:
            if old_cluster == target_cluster:
                continue
            old_size = cluster_size.pop(old_cluster, 0)
            cluster_size[target_cluster] = cluster_size.get(target_cluster, 0) + old_size
            # Bulk-update in DB (retry on deadlock)
            for attempt in range(3):
                try:
                    session.execute(
                        update(Article)
                        .where(Article.dedup_cluster_id == old_cluster)
                        .values(dedup_cluster_id=target_cluster)
                    )
                    break
                except OperationalError:
                    session.rollback()
                    if attempt == 2:
                        raise
                    time.sleep(0.1 * (attempt + 1))
            # Keep local map in sync
            for aid in list(cluster_of):
                if cluster_of[aid] == old_cluster:
                    cluster_of[aid] = target_cluster
                    changed.add(aid)

    # Persist new assignments for articles that weren't covered by the merge UPDATE.
    # Retry on deadlock — concurrent processes (e.g. re-categorization) may lock
    # overlapping rows.
    for aid in changed:
        cid = cluster_of[aid]
        for attempt in range(3):
            try:
                session.execute(update(Article).where(Article.id == aid).values(dedup_cluster_id=cid))
                break
            except OperationalError:
                session.rollback()
                if attempt == 2:
                    raise
                time.sleep(0.1 * (attempt + 1))

    session.commit()
    return len(changed)
