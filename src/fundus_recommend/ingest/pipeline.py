from __future__ import annotations

import json
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
from datetime import datetime, timezone

import click
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from fundus_recommend.config import settings
from fundus_recommend.db.session import SyncSessionLocal
from fundus_recommend.ingest.adapters import FundusAdapter, LicensedFeedAdapter, OfficialAPIAdapter, RSSAdapter
from fundus_recommend.ingest.fetcher import HttpFetcher
from fundus_recommend.ingest.policy import build_policy_state
from fundus_recommend.ingest.registry import resolve_publisher_tokens
from fundus_recommend.ingest.types import (
    AdapterType,
    CrawlArticleCandidate,
    CrawlRunResult,
    FetchPolicy,
    PublisherConfig,
    PublisherCrawlResult,
    PublisherRunDiagnostics,
)
from fundus_recommend.models.db import Article, CrawlRun, CrawlRunPublisher


def _adapter_for(adapter: AdapterType):
    if adapter == AdapterType.RSS:
        return RSSAdapter()
    if adapter == AdapterType.FUNDUS:
        return FundusAdapter()
    if adapter == AdapterType.OFFICIAL_API:
        return OfficialAPIAdapter()
    if adapter == AdapterType.LICENSED_FEED:
        return LicensedFeedAdapter()
    raise ValueError(f"Unsupported adapter type: {adapter}")


def _policy_from_settings() -> FetchPolicy:
    return FetchPolicy(
        timeout_seconds=settings.crawl_timeout_seconds,
        max_retries=settings.crawl_max_retries,
        backoff_seconds=settings.crawl_backoff_seconds,
        rate_limit_per_minute=settings.crawl_rate_limit_per_minute,
        circuit_breaker_threshold=settings.crawl_circuit_breaker_threshold,
        circuit_breaker_cooldown_seconds=settings.crawl_circuit_breaker_cooldown_seconds,
    )


def _serialize_config(config: PublisherConfig) -> dict:
    payload = asdict(config)
    payload["adapter"] = config.adapter.value
    return payload


def _deserialize_config(payload: dict) -> PublisherConfig:
    payload = dict(payload)
    payload["adapter"] = AdapterType(payload["adapter"])
    if isinstance(payload.get("feed_urls"), list):
        payload["feed_urls"] = tuple(payload["feed_urls"])
    return PublisherConfig(**payload)


def _insert_candidates(candidates: list[CrawlArticleCandidate]) -> list[int]:
    inserted_ids: list[int] = []

    with SyncSessionLocal() as session:
        for candidate in candidates:
            exists = session.execute(select(Article.id).where(Article.url == candidate.url)).scalar()
            if exists:
                continue

            db_article = Article(
                url=candidate.url,
                title=candidate.title,
                body=candidate.body,
                authors=candidate.authors,
                topics=candidate.topics,
                publisher=candidate.publisher,
                language=candidate.language,
                publishing_date=candidate.publishing_date,
                cover_image_url=candidate.cover_image_url,
            )
            session.add(db_article)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                continue
            inserted_ids.append(db_article.id)

    return inserted_ids


def _worker_crawl_and_insert(
    config_payload: dict,
    max_articles: int,
    language: str | None,
    policy_payload: dict,
) -> dict:
    started_at = datetime.now(timezone.utc)
    config = _deserialize_config(config_payload)
    policy = FetchPolicy(**policy_payload)

    status_histogram: dict[str, int] = {}
    inserted_article_ids: list[int] = []

    try:
        fetcher = HttpFetcher(policy)
        state = build_policy_state(policy)
        adapter = _adapter_for(config.adapter)
        adapter_output = adapter.crawl(
            config=config,
            max_articles=max_articles,
            language=language,
            policy=policy,
            fetcher=fetcher,
            state=state,
            status_histogram=status_histogram,
        )

        if adapter_output.outcome == "success" and adapter_output.candidates:
            inserted_article_ids = _insert_candidates(adapter_output.candidates)

        diagnostics = PublisherRunDiagnostics(
            publisher_id=config.publisher_id,
            display_name=config.display_name,
            adapter=config.adapter.value,
            outcome=adapter_output.outcome,
            inserted_count=len(inserted_article_ids),
            crawled_count=adapter_output.crawled_count,
            skipped_count=adapter_output.skipped_count,
            status_histogram=status_histogram,
            skip_reason=adapter_output.skip_reason,
            error_message=adapter_output.error_message,
            started_at=started_at,
            finished_at=datetime.now(timezone.utc),
        )
        return {
            "publisher_id": config.publisher_id,
            "inserted_article_ids": inserted_article_ids,
            "diagnostics": diagnostics.to_dict(),
        }

    except Exception as exc:  # pragma: no cover - defensive hardening
        diagnostics = PublisherRunDiagnostics(
            publisher_id=config.publisher_id,
            display_name=config.display_name,
            adapter=config.adapter.value,
            outcome="failed",
            inserted_count=0,
            crawled_count=0,
            skipped_count=0,
            status_histogram=status_histogram,
            error_message=f"{type(exc).__name__}: {exc}",
            started_at=started_at,
            finished_at=datetime.now(timezone.utc),
        )
        return {
            "publisher_id": config.publisher_id,
            "inserted_article_ids": [],
            "diagnostics": diagnostics.to_dict(),
        }


def _result_from_payload(payload: dict) -> PublisherCrawlResult:
    diagnostics_payload = dict(payload["diagnostics"])

    started_at = diagnostics_payload.get("started_at")
    finished_at = diagnostics_payload.get("finished_at")

    diagnostics = PublisherRunDiagnostics(
        publisher_id=diagnostics_payload["publisher_id"],
        display_name=diagnostics_payload["display_name"],
        adapter=diagnostics_payload["adapter"],
        outcome=diagnostics_payload["outcome"],
        inserted_count=diagnostics_payload["inserted_count"],
        crawled_count=diagnostics_payload["crawled_count"],
        skipped_count=diagnostics_payload["skipped_count"],
        status_histogram=diagnostics_payload.get("status_histogram", {}),
        skip_reason=diagnostics_payload.get("skip_reason"),
        error_message=diagnostics_payload.get("error_message"),
        started_at=datetime.fromisoformat(started_at) if started_at else None,
        finished_at=datetime.fromisoformat(finished_at) if finished_at else None,
    )

    return PublisherCrawlResult(
        publisher_id=payload["publisher_id"],
        inserted_article_ids=list(payload.get("inserted_article_ids", [])),
        diagnostics=diagnostics,
    )


def _create_run(run_label: str, requested: list[str], resolved: list[str]) -> int:
    with SyncSessionLocal() as session:
        run = CrawlRun(
            run_label=run_label,
            requested_publishers=requested,
            resolved_publishers=resolved,
            status="running",
            total_publishers=0,
            total_inserted=0,
        )
        session.add(run)
        session.commit()
        return int(run.id)


def _persist_run_results(run_id: int, results: list[PublisherCrawlResult]) -> None:
    now = datetime.now(timezone.utc)

    with SyncSessionLocal() as session:
        run = session.get(CrawlRun, run_id)
        if run is None:
            return

        for result in results:
            diag = result.diagnostics
            row = CrawlRunPublisher(
                crawl_run_id=run_id,
                publisher_id=diag.publisher_id,
                display_name=diag.display_name,
                adapter=diag.adapter,
                outcome=diag.outcome,
                inserted_count=diag.inserted_count,
                crawled_count=diag.crawled_count,
                skipped_count=diag.skipped_count,
                status_histogram=diag.status_histogram,
                skip_reason=diag.skip_reason,
                error_message=diag.error_message,
                started_at=diag.started_at,
                finished_at=diag.finished_at,
            )
            session.add(row)

        total_publishers = len(results)
        succeeded = sum(1 for r in results if r.diagnostics.outcome == "success")
        skipped = sum(1 for r in results if r.diagnostics.outcome == "skipped")
        failed = total_publishers - succeeded - skipped

        run.total_publishers = total_publishers
        run.succeeded_publishers = succeeded
        run.skipped_publishers = skipped
        run.failed_publishers = failed
        run.total_inserted = sum(r.diagnostics.inserted_count for r in results)
        run.finished_at = now
        if failed == total_publishers and total_publishers > 0:
            run.status = "failed"
        elif failed > 0:
            run.status = "partial_success"
        else:
            run.status = "success"

        session.commit()


def crawl_publishers_once(
    publisher_tokens: list[str],
    max_articles: int,
    language: str | None,
    *,
    workers: int = 1,
    run_label: str = "crawl",
    emit_logs: bool = True,
) -> CrawlRunResult:
    policy = _policy_from_settings()
    policy_payload = asdict(policy)

    configs, warnings, unknown_tokens = resolve_publisher_tokens(publisher_tokens)

    run_id = _create_run(
        run_label=run_label,
        requested=publisher_tokens,
        resolved=[config.publisher_id for config in configs],
    )

    results: list[PublisherCrawlResult] = []

    for token in unknown_tokens:
        results.append(
            PublisherCrawlResult(
                publisher_id=token,
                inserted_article_ids=[],
                diagnostics=PublisherRunDiagnostics(
                    publisher_id=token,
                    display_name=token,
                    adapter="unknown",
                    outcome="failed",
                    inserted_count=0,
                    crawled_count=0,
                    skipped_count=0,
                    status_histogram={},
                    error_message=f"Unknown publisher token: {token}",
                    started_at=datetime.now(timezone.utc),
                    finished_at=datetime.now(timezone.utc),
                ),
            )
        )

    if workers > 1 and len(configs) > 1:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            future_to_config = {
                executor.submit(
                    _worker_crawl_and_insert,
                    _serialize_config(config),
                    max_articles,
                    language,
                    policy_payload,
                ): config
                for config in configs
            }

            for future in as_completed(future_to_config):
                payload = future.result()
                results.append(_result_from_payload(payload))
    else:
        for config in configs:
            payload = _worker_crawl_and_insert(
                _serialize_config(config),
                max_articles,
                language,
                policy_payload,
            )
            results.append(_result_from_payload(payload))

    _persist_run_results(run_id, results)

    if emit_logs:
        for warning in warnings:
            click.echo(f"[warn] {warning}")

        for result in results:
            click.echo(
                json.dumps(
                    {
                        "event": "crawl.publisher",
                        "run_id": run_id,
                        "publisher_id": result.publisher_id,
                        "adapter": result.diagnostics.adapter,
                        "outcome": result.diagnostics.outcome,
                        "inserted_count": result.diagnostics.inserted_count,
                        "skip_reason": result.diagnostics.skip_reason,
                        "status_histogram": result.diagnostics.status_histogram,
                        "error_message": result.diagnostics.error_message,
                    },
                    ensure_ascii=False,
                )
            )

        click.echo(
            json.dumps(
                {
                    "event": "crawl.run",
                    "run_id": run_id,
                    "requested_publishers": publisher_tokens,
                    "resolved_publishers": [config.publisher_id for config in configs],
                    "total_publishers": len(results),
                    "total_inserted": sum(r.diagnostics.inserted_count for r in results),
                    "succeeded_publishers": sum(1 for r in results if r.diagnostics.outcome == "success"),
                    "skipped_publishers": sum(1 for r in results if r.diagnostics.outcome == "skipped"),
                    "failed_publishers": sum(1 for r in results if r.diagnostics.outcome == "failed"),
                },
                ensure_ascii=False,
            )
        )

    return CrawlRunResult(run_id=run_id, publisher_results=results, warnings=warnings)
