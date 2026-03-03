from __future__ import annotations

import click
from sqlalchemy import select, update

from fundus_recommend.db.session import SyncSessionLocal, sync_engine
from fundus_recommend.models.db import Article, Base
from fundus_recommend.services.article_body_store import BodyStoreError, build_body_key, put_body


def migrate_bodies(
    *,
    batch_size: int = 500,
    limit: int | None = None,
    resume_from_id: int = 0,
    dry_run: bool = False,
    prune_db_body: bool = False,
    max_errors: int = 20,
) -> dict[str, int]:
    stats = {
        "processed": 0,
        "uploaded": 0,
        "pruned": 0,
        "errors": 0,
        "last_id": resume_from_id,
    }

    with SyncSessionLocal() as session:
        while True:
            remaining = None if limit is None else (limit - stats["processed"])
            if remaining is not None and remaining <= 0:
                break

            current_batch_size = batch_size if remaining is None else min(batch_size, remaining)
            stmt = (
                select(Article.id, Article.url, Article.body)
                .where(
                    Article.id > stats["last_id"],
                    Article.body_storage_key.is_(None),
                    Article.body.is_not(None),
                )
                .order_by(Article.id)
                .limit(current_batch_size)
            )
            rows = session.execute(stmt).all()
            if not rows:
                break

            for article_id, url, body in rows:
                stats["processed"] += 1
                stats["last_id"] = int(article_id)
                if body is None:
                    continue

                key = build_body_key(int(article_id), url)

                if dry_run:
                    stats["uploaded"] += 1
                    if prune_db_body:
                        stats["pruned"] += 1
                    continue

                try:
                    put_body(key, body)
                except BodyStoreError as exc:
                    stats["errors"] += 1
                    click.echo(f"[error] upload failed article_id={article_id} key={key} error={exc}")
                    if stats["errors"] > max_errors:
                        raise click.ClickException(
                            f"Aborting after {stats['errors']} upload errors (max_errors={max_errors})"
                        )
                    continue

                values: dict[str, str | None] = {
                    "body_storage_key": key,
                    "body_storage_provider": "r2",
                }
                if prune_db_body:
                    values["body"] = None
                    stats["pruned"] += 1

                session.execute(update(Article).where(Article.id == article_id).values(**values))
                session.commit()
                stats["uploaded"] += 1

    return stats


@click.command()
@click.option("--batch-size", default=500, show_default=True, help="Number of articles to process per batch.")
@click.option("--limit", default=None, type=int, help="Optional cap on total rows processed.")
@click.option("--resume-from-id", default=0, show_default=True, type=int, help="Start from article ID > this value.")
@click.option("--dry-run", is_flag=True, help="Show what would be uploaded without writing to R2 or DB.")
@click.option("--prune-db-body", is_flag=True, help="Set articles.body=NULL after successful upload.")
@click.option("--max-errors", default=20, show_default=True, type=int, help="Abort after this many upload errors.")
def main(
    batch_size: int,
    limit: int | None,
    resume_from_id: int,
    dry_run: bool,
    prune_db_body: bool,
    max_errors: int,
) -> None:
    """Backfill article bodies into R2 and optionally prune PostgreSQL bodies."""
    Base.metadata.create_all(sync_engine)
    click.echo(
        f"Starting body migration: batch_size={batch_size} limit={limit} "
        f"resume_from_id={resume_from_id} dry_run={dry_run} prune_db_body={prune_db_body}"
    )
    stats = migrate_bodies(
        batch_size=batch_size,
        limit=limit,
        resume_from_id=resume_from_id,
        dry_run=dry_run,
        prune_db_body=prune_db_body,
        max_errors=max_errors,
    )

    mode_label = "would upload" if dry_run else "uploaded"
    click.echo(
        f"Done. processed={stats['processed']} {mode_label}={stats['uploaded']} "
        f"pruned={stats['pruned']} errors={stats['errors']} last_id={stats['last_id']}"
    )


if __name__ == "__main__":
    main()
