import click
from sqlalchemy import select, update

from fundus_recommend.db.session import SyncSessionLocal, sync_engine
from fundus_recommend.models.db import Article, Base
from fundus_recommend.services.embeddings import embed_texts, make_embedding_text


@click.command()
@click.option("--batch-size", default=64, help="Embedding batch size")
@click.option("--with-dedup", is_flag=True, help="Run dedup after embedding")
def main(batch_size: int, with_dedup: bool) -> None:
    """Generate embeddings for un-embedded articles, optionally run dedup."""
    Base.metadata.create_all(sync_engine)

    with SyncSessionLocal() as session:
        stmt = select(Article.id, Article.title, Article.body).where(Article.embedding.is_(None)).order_by(Article.id)
        rows = session.execute(stmt).all()

        if not rows:
            click.echo("No un-embedded articles found.")
        else:
            click.echo(f"Embedding {len(rows)} articles in batches of {batch_size}...")
            for i in range(0, len(rows), batch_size):
                batch = rows[i : i + batch_size]
                texts = [make_embedding_text(r[1], r[2]) for r in batch]
                vectors = embed_texts(texts)

                for row, vec in zip(batch, vectors):
                    session.execute(update(Article).where(Article.id == row[0]).values(embedding=vec.tolist()))

                session.commit()
                click.echo(f"  Embedded {min(i + batch_size, len(rows))}/{len(rows)}")

            click.echo("Embedding complete.")

    if with_dedup:
        click.echo("Running dedup...")
        from fundus_recommend.services.dedup import run_dedup

        with SyncSessionLocal() as session:
            clustered = run_dedup(session)
            click.echo(f"Dedup complete. {clustered} articles assigned to clusters.")


if __name__ == "__main__":
    main()
