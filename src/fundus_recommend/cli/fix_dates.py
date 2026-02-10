from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import click
from sqlalchemy import select

from fundus_recommend.db.session import SyncSessionLocal, sync_engine
from fundus_recommend.models.db import Article, Base
from fundus_recommend.services.date_resolution import is_ambiguous_month_day, swap_month_day

TARGET_PUBLISHERS = ("Anadolu Ajansı", "Klasse Gegen Klasse")
FUTURE_TOLERANCE = timedelta(days=1)


@dataclass(frozen=True)
class BackfillCandidate:
    id: int
    publisher: str
    url: str
    current_date: datetime
    swapped_date: datetime
    crawled_at: datetime


def _as_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _candidate_swapped_date(publishing_date: datetime, crawled_at: datetime) -> datetime | None:
    pub = _as_aware_utc(publishing_date)
    crawled = _as_aware_utc(crawled_at)

    if not is_ambiguous_month_day(pub):
        return None
    if pub <= crawled + FUTURE_TOLERANCE:
        return None

    swapped = swap_month_day(pub)
    if swapped is None:
        return None
    if swapped > crawled + FUTURE_TOLERANCE:
        return None
    return swapped


def collect_backfill_candidates() -> list[BackfillCandidate]:
    with SyncSessionLocal() as session:
        stmt = (
            select(Article)
            .where(
                Article.publisher.in_(TARGET_PUBLISHERS),
                Article.publishing_date.is_not(None),
                Article.crawled_at.is_not(None),
            )
            .order_by(Article.id.asc())
        )
        articles = list(session.execute(stmt).scalars().all())

    candidates: list[BackfillCandidate] = []
    for article in articles:
        if article.publishing_date is None or article.crawled_at is None:
            continue

        swapped = _candidate_swapped_date(article.publishing_date, article.crawled_at)
        if swapped is None:
            continue

        candidates.append(
            BackfillCandidate(
                id=article.id,
                publisher=article.publisher,
                url=article.url,
                current_date=_as_aware_utc(article.publishing_date),
                swapped_date=swapped,
                crawled_at=_as_aware_utc(article.crawled_at),
            )
        )

    return candidates


def apply_backfill(candidates: list[BackfillCandidate]) -> int:
    if not candidates:
        return 0

    swaps_by_id = {candidate.id: candidate.swapped_date for candidate in candidates}

    with SyncSessionLocal() as session:
        stmt = select(Article).where(Article.id.in_(list(swaps_by_id.keys())))
        articles = list(session.execute(stmt).scalars().all())

        updated = 0
        for article in articles:
            swapped = swaps_by_id.get(article.id)
            if swapped is None:
                continue
            article.publishing_date = swapped
            updated += 1

        if updated:
            session.commit()

    return updated


@click.command()
@click.option("--apply", "apply_changes", is_flag=True, help="Apply updates. Default mode is dry-run.")
@click.option("--sample-size", default=10, show_default=True, help="How many candidate rows to print as examples.")
def main(apply_changes: bool, sample_size: int) -> None:
    """Fix clearly ambiguous dd/mm vs mm/dd publishing dates for targeted publishers."""
    Base.metadata.create_all(sync_engine)

    candidates = collect_backfill_candidates()
    click.echo(f"Found {len(candidates)} candidate row(s) for date correction.")

    if candidates:
        click.echo("Sample candidates:")
        for candidate in candidates[:sample_size]:
            click.echo(
                f"  id={candidate.id} | {candidate.publisher} | "
                f"{candidate.current_date.isoformat()} -> {candidate.swapped_date.isoformat()} | "
                f"crawled_at={candidate.crawled_at.isoformat()}"
            )

    if not apply_changes:
        click.echo("Dry-run complete. Re-run with --apply to update rows.")
        return

    if not candidates:
        click.echo("No updates applied.")
        return

    updated = apply_backfill(candidates)
    click.echo(f"Updated {updated} row(s).")


if __name__ == "__main__":
    main()
