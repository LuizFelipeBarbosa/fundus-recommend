from collections import Counter

import click
from sqlalchemy import select, update

from fundus_recommend.config import settings
from fundus_recommend.models.db import Article, Base
from fundus_recommend.services.categorizer import CATEGORY_PRIORITY, assign_category
from fundus_recommend.db.session import SyncSessionLocal, sync_engine


def classify_all_articles(batch_size: int = 256) -> tuple[int, Counter[str]]:
    """Reclassify all articles using semantic categorization in batches."""
    total = 0
    counts: Counter[str] = Counter()
    last_id = 0
    snippet_chars = max(1, settings.article_body_snippet_chars)

    with SyncSessionLocal() as session:
        while True:
            stmt = (
                select(Article.id, Article.title, Article.body_snippet, Article.body, Article.title_en, Article.embedding)
                .where(Article.id > last_id)
                .order_by(Article.id)
                .limit(batch_size)
            )
            rows = session.execute(stmt).all()
            if not rows:
                break

            for row in rows:
                snippet_source = row[2] or (row[3] or "")[:snippet_chars]
                body_snippet = snippet_source[:500]
                category = assign_category(
                    embedding=row[5],
                    title=row[1],
                    body_snippet=body_snippet,
                    title_en=row[4],
                )
                session.execute(update(Article).where(Article.id == row[0]).values(category=category))
                counts[category] += 1
                total += 1

            session.commit()
            last_id = rows[-1][0]

    return total, counts


@click.command()
@click.option("--batch-size", default=256, show_default=True, help="Number of articles to process per batch.")
def main(batch_size: int) -> None:
    """Semantically classify all stored articles and update category labels."""
    Base.metadata.create_all(sync_engine)

    click.echo(f"Reclassifying articles with semantic classifier (batch_size={batch_size})...")
    total, counts = classify_all_articles(batch_size=batch_size)
    click.echo(f"Done. Reclassified {total} articles.")
    click.echo("Category counts:")

    known = [*CATEGORY_PRIORITY, "General"]
    for category in known:
        click.echo(f"  {category}: {counts.get(category, 0)}")

    extra_categories = sorted(set(counts) - set(known))
    for category in extra_categories:
        click.echo(f"  {category}: {counts[category]}")

    click.echo(f"General assignments: {counts.get('General', 0)}")


if __name__ == "__main__":
    main()
