import time
from datetime import datetime, timedelta, timezone

import click
from sqlalchemy import func, select, update

from fundus_recommend.config import settings
from fundus_recommend.db.session import SyncSessionLocal, sync_engine
from fundus_recommend.ingest.pipeline import crawl_publishers_once
from fundus_recommend.ingest.registry import DEFAULT_PUBLISHER_IDS
from fundus_recommend.models.db import Article, Base
from fundus_recommend.services.categorizer import assign_category
from fundus_recommend.services.dedup import run_dedup
from fundus_recommend.services.embeddings import embed_texts, make_embedding_text
from fundus_recommend.services.translation import translate_to_english


def translate_new_articles(article_ids: list[int]) -> int:
    """Translate titles of non-English articles from the given IDs."""
    if not article_ids:
        return 0

    with SyncSessionLocal() as session:
        stmt = (
            select(Article.id, Article.title, Article.language)
            .where(Article.id.in_(article_ids), Article.language != "en", Article.title_en.is_(None))
            .order_by(Article.id)
        )
        rows = session.execute(stmt).all()

        if not rows:
            return 0

        translated = 0
        for row in rows:
            result = translate_to_english(row[1], source_lang=row[2] or "auto")
            if result:
                session.execute(update(Article).where(Article.id == row[0]).values(title_en=result))
                translated += 1
        session.commit()
        return translated


def categorize_new_articles(article_ids: list[int]) -> int:
    """Assign categories to articles from the given IDs."""
    if not article_ids:
        return 0

    with SyncSessionLocal() as session:
        stmt = (
            select(Article.id, Article.title, Article.body, Article.title_en, Article.embedding)
            .where(Article.id.in_(article_ids), Article.category.is_(None))
            .order_by(Article.id)
        )
        rows = session.execute(stmt).all()

        if not rows:
            return 0

        categorized = 0
        for row in rows:
            body_snippet = row[2][:500] if row[2] else ""
            category = assign_category(
                embedding=row[4],
                title=row[1],
                body_snippet=body_snippet,
                title_en=row[3],
            )
            session.execute(update(Article).where(Article.id == row[0]).values(category=category))
            categorized += 1
        session.commit()
        return categorized


def embed_new_articles(article_ids: list[int], batch_size: int) -> int:
    """Embed articles from the given IDs and set embedded_at."""
    if not article_ids:
        return 0

    with SyncSessionLocal() as session:
        stmt = (
            select(Article.id, Article.title, Article.body, Article.title_en)
            .where(Article.id.in_(article_ids), Article.embedding.is_(None))
            .order_by(Article.id)
        )
        rows = session.execute(stmt).all()

        if not rows:
            return 0

        now = datetime.now(timezone.utc)
        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            texts = [make_embedding_text(r[1], r[2], title_en=r[3]) for r in batch]
            vectors = embed_texts(texts)

            for row, vec in zip(batch, vectors):
                session.execute(
                    update(Article).where(Article.id == row[0]).values(embedding=vec.tolist(), embedded_at=now)
                )

            session.commit()

        return len(rows)


def refresh_stale_embeddings(max_age_days: int = 7, batch_size: int = 64) -> int:
    """Re-embed articles whose embeddings are older than max_age_days or where title_en was set after embedding."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)

    with SyncSessionLocal() as session:
        stmt = (
            select(Article.id, Article.title, Article.body, Article.title_en)
            .where(
                Article.embedding.is_not(None),
                Article.embedded_at.is_not(None),
                Article.embedded_at < cutoff,
            )
            .order_by(Article.id)
        )
        rows = session.execute(stmt).all()

        if not rows:
            return 0

        click.echo(f"  Refreshing {len(rows)} stale embeddings (older than {max_age_days} days)...")
        now = datetime.now(timezone.utc)
        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            texts = [make_embedding_text(r[1], r[2], title_en=r[3]) for r in batch]
            vectors = embed_texts(texts)

            for row, vec in zip(batch, vectors):
                session.execute(
                    update(Article).where(Article.id == row[0]).values(embedding=vec.tolist(), embedded_at=now)
                )

            session.commit()

        return len(rows)


def run_dedup_pass(new_article_ids: list[int] | None = None) -> int:
    with SyncSessionLocal() as session:
        return run_dedup(session, new_article_ids)


def get_dedup_stats() -> tuple[int, int, int]:
    with SyncSessionLocal() as session:
        clustered_articles = (
            session.execute(select(func.count(Article.id)).where(Article.dedup_cluster_id.is_not(None))).scalar() or 0
        )
        cluster_count = (
            session.execute(
                select(func.count(func.distinct(Article.dedup_cluster_id))).where(Article.dedup_cluster_id.is_not(None))
            ).scalar()
            or 0
        )
        cluster_sizes = (
            select(func.count(Article.id).label("cluster_size"))
            .where(Article.dedup_cluster_id.is_not(None))
            .group_by(Article.dedup_cluster_id)
            .subquery()
        )
        max_cluster_size = session.execute(select(func.coalesce(func.max(cluster_sizes.c.cluster_size), 0))).scalar() or 0

    return int(clustered_articles), int(cluster_count), int(max_cluster_size)


def run_cycle(publishers: list[str], max_articles: int, language: str | None, batch_size: int, workers: int) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    click.echo(f"\n[{now}] Starting crawl cycle ({workers} workers)...")

    crawl_result = crawl_publishers_once(
        publisher_tokens=publishers,
        max_articles=max_articles,
        language=language,
        workers=workers,
        run_label="schedule-cycle",
    )

    total_inserted = 0
    total_translated = 0
    total_embedded = 0
    total_categorized = 0
    all_new_ids: list[int] = []

    for publisher_result in crawl_result.publisher_results:
        diag = publisher_result.diagnostics
        inserted = diag.inserted_count
        translated = 0
        embedded = 0
        categorized = 0

        if publisher_result.inserted_article_ids:
            all_new_ids.extend(publisher_result.inserted_article_ids)
            translated = translate_new_articles(publisher_result.inserted_article_ids)
            embedded = embed_new_articles(publisher_result.inserted_article_ids, batch_size)
            categorized = categorize_new_articles(publisher_result.inserted_article_ids)

        total_inserted += inserted
        total_translated += translated
        total_embedded += embedded
        total_categorized += categorized

        click.echo(
            f"  [{publisher_result.publisher_id}] adapter={diag.adapter} outcome={diag.outcome} "
            f"crawled={diag.crawled_count} inserted={inserted} translated={translated} "
            f"embedded={embedded} categorized={categorized}"
        )

    click.echo(
        f"  Totals: {total_inserted} crawled, {total_translated} translated, "
        f"{total_embedded} embedded, {total_categorized} categorized"
    )

    clustered = run_dedup_pass(all_new_ids)
    clustered_articles, cluster_count, max_cluster_size = get_dedup_stats()
    click.echo(
        "  Dedup: "
        f"threshold={settings.dedup_threshold:.2f}, "
        f"reassigned={clustered}, "
        f"clustered_articles={clustered_articles}, "
        f"clusters={cluster_count}, "
        f"max_cluster_size={max_cluster_size}"
    )

    refreshed = refresh_stale_embeddings(max_age_days=7, batch_size=batch_size)
    if refreshed:
        click.echo(f"  Refreshed {refreshed} stale embeddings")

    click.echo(f"  Crawl diagnostics run_id={crawl_result.run_id}")
    click.echo(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Cycle complete.")


@click.command()
@click.option(
    "-p",
    "--publishers",
    default=",".join(DEFAULT_PUBLISHER_IDS),
    help="Comma-separated publisher IDs (legacy country codes still accepted)",
)
@click.option("-n", "--max-articles", default=100, help="Max articles per publisher per cycle")
@click.option("-l", "--language", default=None, help="Filter by language (e.g. en); omit for all languages")
@click.option("--interval", default=10, help="Minutes between crawl cycles")
@click.option("--batch-size", default=64, help="Embedding batch size")
@click.option("--workers", default=4, help="Number of parallel workers for crawling publishers")
@click.option("--run-once", is_flag=True, help="Run a single cycle then exit")
def main(publishers: str, max_articles: int, language: str | None, interval: int, batch_size: int, workers: int, run_once: bool) -> None:
    """Scheduled crawl + embed + dedup loop."""
    Base.metadata.create_all(sync_engine)

    pub_list = [token.strip() for token in publishers.split(",") if token.strip()]
    click.echo(
        f"Scheduler: publishers={pub_list}, max_articles={max_articles}, "
        f"interval={interval}min, workers={workers}"
    )

    run_cycle(pub_list, max_articles, language, batch_size, workers)

    if run_once:
        return

    while True:
        click.echo(f"\nSleeping {interval} minutes until next cycle...")
        time.sleep(interval * 60)
        run_cycle(pub_list, max_articles, language, batch_size, workers)


if __name__ == "__main__":
    main()
