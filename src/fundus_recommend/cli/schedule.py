import time
from datetime import datetime, timedelta, timezone

import click
from sqlalchemy import select, update

from fundus_recommend.db.session import SyncSessionLocal, sync_engine
from fundus_recommend.models.db import Article, Base
from fundus_recommend.services.categorizer import assign_category
from fundus_recommend.services.dedup import run_dedup
from fundus_recommend.services.embeddings import embed_texts, make_embedding_text
from fundus_recommend.services.translation import translate_to_english


def crawl_articles(publisher_code: str, max_articles: int, language: str | None) -> list[int]:
    """Crawl a single publisher collection and return IDs of newly inserted articles."""
    from fundus import Crawler, PublisherCollection

    collection = getattr(PublisherCollection, publisher_code, None)
    if collection is None:
        click.echo(f"  Unknown publisher collection: {publisher_code}, skipping")
        return []

    click.echo(f"  Crawling from '{publisher_code}' (max {max_articles})...")
    crawler = Crawler(collection)
    new_ids: list[int] = []

    for article in crawler.crawl(max_articles=max_articles):
        if language and article.lang and article.lang != language:
            continue

        with SyncSessionLocal() as session:
            exists = session.execute(select(Article.id).where(Article.url == article.html.responded_url)).scalar()
            if exists:
                continue

            cover_url = None
            if article.images:
                cover_url = article.images[0].url

            db_article = Article(
                url=article.html.responded_url,
                title=article.title,
                body=str(article.body),
                authors=list(article.authors) if article.authors else [],
                topics=list(article.topics) if article.topics else [],
                publisher=article.publisher,
                language=article.lang,
                publishing_date=article.publishing_date,
                cover_image_url=cover_url,
            )
            session.add(db_article)
            session.commit()
            new_ids.append(db_article.id)

    click.echo(f"  Inserted {len(new_ids)} articles from '{publisher_code}'")
    return new_ids


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
            select(Article.id, Article.topics, Article.title, Article.body, Article.title_en)
            .where(Article.id.in_(article_ids), Article.category.is_(None))
            .order_by(Article.id)
        )
        rows = session.execute(stmt).all()

        if not rows:
            return 0

        categorized = 0
        for row in rows:
            body_snippet = row[3][:500] if row[3] else ""
            category = assign_category(row[1] or [], row[2], body_snippet, title_en=row[4])
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


def run_dedup_pass() -> int:
    with SyncSessionLocal() as session:
        return run_dedup(session)


def run_cycle(publishers: list[str], max_articles: int, language: str | None, batch_size: int) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    click.echo(f"\n[{now}] Starting crawl cycle...")

    total_inserted = 0
    total_translated = 0
    total_categorized = 0
    total_embedded = 0

    for code in publishers:
        new_ids = crawl_articles(code, max_articles, language)
        total_inserted += len(new_ids)

        if new_ids:
            translated = translate_new_articles(new_ids)
            total_translated += translated

            categorized = categorize_new_articles(new_ids)
            total_categorized += categorized

            embedded = embed_new_articles(new_ids, batch_size)
            total_embedded += embedded

    click.echo(f"  Totals: {total_inserted} crawled, {total_translated} translated, "
               f"{total_categorized} categorized, {total_embedded} embedded")

    clustered = run_dedup_pass()
    click.echo(f"  Dedup: {clustered} articles in clusters")

    refreshed = refresh_stale_embeddings(max_age_days=7, batch_size=batch_size)
    if refreshed:
        click.echo(f"  Refreshed {refreshed} stale embeddings")

    click.echo(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Cycle complete.")


@click.command()
@click.option(
    "-p",
    "--publishers",
    default="ar,at,au,bd,be,br,ca,ch,cl,cn,co,cz,de,dk,eg,es,fi,fr,gl,gr,hk,hu,id,ie,il,ind,intl,isl,it,jp,ke,kr,lb,li,ls,lt,lu,mx,my,na,ng,nl,no,nz,ph,pk,pl,pt,py,ro,ru,sa,se,sg,th,tr,tw,tz,ua,uk,us,ve,vn,za",
    help="Comma-separated publisher country codes",
)
@click.option("-n", "--max-articles", default=100, help="Max articles per publisher per cycle")
@click.option("-l", "--language", default=None, help="Filter by language (e.g. en); omit for all languages")
@click.option("--interval", default=10, help="Minutes between crawl cycles")
@click.option("--batch-size", default=64, help="Embedding batch size")
@click.option("--run-once", is_flag=True, help="Run a single cycle then exit")
def main(publishers: str, max_articles: int, language: str | None, interval: int, batch_size: int, run_once: bool) -> None:
    """Scheduled crawl + embed + dedup loop."""
    Base.metadata.create_all(sync_engine)

    pub_list = [c.strip().lower() for c in publishers.split(",")]
    click.echo(f"Scheduler: publishers={pub_list}, max_articles={max_articles}, interval={interval}min")

    run_cycle(pub_list, max_articles, language, batch_size)

    if run_once:
        return

    while True:
        click.echo(f"\nSleeping {interval} minutes until next cycle...")
        time.sleep(interval * 60)
        run_cycle(pub_list, max_articles, language, batch_size)


if __name__ == "__main__":
    main()
