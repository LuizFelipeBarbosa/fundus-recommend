import time
from datetime import datetime

import click
from sqlalchemy import select, update

from fundus_recommend.db.session import SyncSessionLocal, sync_engine
from fundus_recommend.models.db import Article, Base
from fundus_recommend.services.categorizer import assign_category
from fundus_recommend.services.dedup import run_dedup
from fundus_recommend.services.embeddings import embed_texts, make_embedding_text
from fundus_recommend.services.translation import translate_to_english


def crawl_articles(publishers: list[str], max_articles: int, language: str | None) -> int:
    from fundus import Crawler, PublisherCollection

    total_inserted = 0
    for code in publishers:
        collection = getattr(PublisherCollection, code, None)
        if collection is None:
            click.echo(f"  Unknown publisher collection: {code}, skipping")
            continue

        click.echo(f"  Crawling from '{code}' (max {max_articles})...")
        crawler = Crawler(collection)
        count = 0

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
                count += 1

        click.echo(f"  Inserted {count} articles from '{code}'")
        total_inserted += count

    return total_inserted


def translate_articles() -> int:
    """Translate titles of non-English articles that haven't been translated yet."""
    with SyncSessionLocal() as session:
        stmt = (
            select(Article.id, Article.title, Article.language)
            .where(Article.language != "en", Article.title_en.is_(None))
            .order_by(Article.id)
        )
        rows = session.execute(stmt).all()

        if not rows:
            return 0

        click.echo(f"  Translating {len(rows)} article titles...")
        translated = 0
        for row in rows:
            result = translate_to_english(row[1], source_lang=row[2] or "auto")
            if result:
                session.execute(update(Article).where(Article.id == row[0]).values(title_en=result))
                translated += 1
        session.commit()
        return translated


def categorize_articles() -> int:
    """Assign categories to articles that don't have one yet."""
    with SyncSessionLocal() as session:
        stmt = (
            select(Article.id, Article.topics, Article.title, Article.body)
            .where(Article.category.is_(None))
            .order_by(Article.id)
        )
        rows = session.execute(stmt).all()

        if not rows:
            return 0

        click.echo(f"  Categorizing {len(rows)} articles...")
        categorized = 0
        for row in rows:
            body_snippet = row[3][:500] if row[3] else ""
            category = assign_category(row[1] or [], row[2], body_snippet)
            if category:
                session.execute(update(Article).where(Article.id == row[0]).values(category=category))
                categorized += 1
        session.commit()
        return categorized


def embed_articles(batch_size: int) -> int:
    with SyncSessionLocal() as session:
        stmt = (
            select(Article.id, Article.title, Article.body, Article.title_en)
            .where(Article.embedding.is_(None))
            .order_by(Article.id)
        )
        rows = session.execute(stmt).all()

        if not rows:
            return 0

        click.echo(f"  Embedding {len(rows)} articles...")
        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            texts = [make_embedding_text(r[1], r[2], title_en=r[3]) for r in batch]
            vectors = embed_texts(texts)

            for row, vec in zip(batch, vectors):
                session.execute(update(Article).where(Article.id == row[0]).values(embedding=vec.tolist()))

            session.commit()

        return len(rows)


def run_dedup_pass() -> int:
    with SyncSessionLocal() as session:
        return run_dedup(session)


def run_cycle(publishers: list[str], max_articles: int, language: str | None, batch_size: int) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    click.echo(f"\n[{now}] Starting crawl cycle...")

    inserted = crawl_articles(publishers, max_articles, language)
    click.echo(f"  Crawled {inserted} new articles")

    translated = translate_articles()
    click.echo(f"  Translated {translated} article titles")

    categorized = categorize_articles()
    click.echo(f"  Categorized {categorized} articles")

    embedded = embed_articles(batch_size)
    click.echo(f"  Embedded {embedded} articles")

    clustered = run_dedup_pass()
    click.echo(f"  Dedup: {clustered} articles in clusters")

    click.echo(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Cycle complete.")


@click.command()
@click.option("-p", "--publishers", default="us,uk", help="Comma-separated publisher country codes")
@click.option("-n", "--max-articles", default=100, help="Max articles per publisher per cycle")
@click.option("-l", "--language", default="en", help="Filter by language")
@click.option("--interval", default=30, help="Minutes between crawl cycles")
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
