from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum


class AdapterType(str, Enum):
    RSS = "rss"
    OFFICIAL_API = "official_api"
    LICENSED_FEED = "licensed_feed"
    FUNDUS = "fundus"


@dataclass(slots=True)
class FetchPolicy:
    timeout_seconds: int
    max_retries: int
    backoff_seconds: float
    rate_limit_per_minute: int
    circuit_breaker_threshold: int
    circuit_breaker_cooldown_seconds: int


@dataclass(slots=True)
class PublisherConfig:
    publisher_id: str
    display_name: str
    adapter: AdapterType
    feed_urls: tuple[str, ...] = ()
    fundus_collection: str | None = None
    fundus_symbol: str | None = None
    default_language: str | None = None
    requires_credentials: bool = False
    credential_env: str | None = None
    legacy_token: str | None = None

    @property
    def is_legacy(self) -> bool:
        return self.legacy_token is not None


@dataclass(slots=True)
class CrawlArticleCandidate:
    url: str
    title: str
    body: str
    publisher: str
    language: str | None = None
    publishing_date: datetime | None = None
    cover_image_url: str | None = None
    authors: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PublisherRunDiagnostics:
    publisher_id: str
    display_name: str
    adapter: str
    outcome: str
    inserted_count: int
    crawled_count: int
    skipped_count: int
    status_histogram: dict[str, int] = field(default_factory=dict)
    skip_reason: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None

    def to_dict(self) -> dict:
        payload = asdict(self)
        if self.started_at is not None:
            payload["started_at"] = self.started_at.isoformat()
        if self.finished_at is not None:
            payload["finished_at"] = self.finished_at.isoformat()
        return payload


@dataclass(slots=True)
class PublisherCrawlResult:
    publisher_id: str
    inserted_article_ids: list[int]
    diagnostics: PublisherRunDiagnostics


@dataclass(slots=True)
class CrawlRunResult:
    run_id: int
    publisher_results: list[PublisherCrawlResult]
    warnings: list[str] = field(default_factory=list)

    @property
    def total_inserted(self) -> int:
        return sum(result.diagnostics.inserted_count for result in self.publisher_results)
