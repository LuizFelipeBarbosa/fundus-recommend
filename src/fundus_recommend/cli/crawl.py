import click
from sqlalchemy import select

from fundus_recommend.db.session import SyncSessionLocal, sync_engine
from fundus_recommend.models.db import Article, Base
from fundus_recommend.services.date_resolution import resolve_article_publishing_date


@click.command()
@click.option("-p", "--publishers", required=True, help="Comma-separated publisher country codes (e.g. us,uk)")
@click.option("-n", "--max-articles", default=100, help="Max articles to crawl per publisher collection")
@click.option("-l", "--language", default=None, help="Filter by language (e.g. en)")
def main(publishers: str, max_articles: int, language: str | None) -> None:
    """Crawl articles from Fundus publishers into PostgreSQL."""
    from fundus import Crawler, PublisherCollection

    Base.metadata.create_all(sync_engine)

    country_codes = [c.strip().lower() for c in publishers.split(",")]
    total_inserted = 0

    for code in country_codes:
        collection = getattr(PublisherCollection, code, None)
        if collection is None:
            click.echo(f"Unknown publisher collection: {code}, skipping")
            continue

        click.echo(f"Crawling from '{code}' (max {max_articles} articles)...")
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
                    publishing_date=resolve_article_publishing_date(article),
                    cover_image_url=cover_url,
                )
                session.add(db_article)
                session.commit()
                count += 1

        click.echo(f"  Inserted {count} articles from '{code}'")
        total_inserted += count

    click.echo(f"Done. Total inserted: {total_inserted}")


if __name__ == "__main__":
    main()
