import click

from fundus_recommend.db.session import sync_engine
from fundus_recommend.ingest.pipeline import crawl_publishers_once
from fundus_recommend.models.db import Base


@click.command()
@click.option(
    "-p",
    "--publishers",
    required=True,
    help="Comma-separated publisher IDs (e.g. reuters,cnn,npr) or legacy country codes (e.g. us)",
)
@click.option("-n", "--max-articles", default=100, help="Max articles to crawl per publisher token")
@click.option("-l", "--language", default=None, help="Filter by language (e.g. en)")
def main(publishers: str, max_articles: int, language: str | None) -> None:
    """Crawl articles from configured publisher adapters into PostgreSQL."""

    Base.metadata.create_all(sync_engine)
    publisher_tokens = [token.strip() for token in publishers.split(",") if token.strip()]
    if not publisher_tokens:
        click.echo("No publisher tokens provided")
        return

    result = crawl_publishers_once(
        publisher_tokens=publisher_tokens,
        max_articles=max_articles,
        language=language,
        workers=1,
        run_label="crawl-cli",
    )

    for publisher_result in result.publisher_results:
        diag = publisher_result.diagnostics
        click.echo(
            f"{publisher_result.publisher_id} [{diag.adapter}] outcome={diag.outcome} "
            f"inserted={diag.inserted_count} crawled={diag.crawled_count} "
            f"skipped={diag.skipped_count} statuses={diag.status_histogram}"
        )

    click.echo(f"Done. run_id={result.run_id} total_inserted={result.total_inserted}")


if __name__ == "__main__":
    main()
