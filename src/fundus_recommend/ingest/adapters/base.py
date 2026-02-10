from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from fundus_recommend.ingest.fetcher import HttpFetcher
from fundus_recommend.ingest.policy import PolicyState
from fundus_recommend.ingest.types import CrawlArticleCandidate, FetchPolicy, PublisherConfig


@dataclass(slots=True)
class AdapterRunOutput:
    candidates: list[CrawlArticleCandidate] = field(default_factory=list)
    outcome: str = "success"
    skip_reason: str | None = None
    error_message: str | None = None
    crawled_count: int = 0
    skipped_count: int = 0


class BaseAdapter(ABC):
    @abstractmethod
    def crawl(
        self,
        config: PublisherConfig,
        max_articles: int,
        language: str | None,
        policy: FetchPolicy,
        fetcher: HttpFetcher,
        state: PolicyState,
        status_histogram: dict[str, int],
    ) -> AdapterRunOutput:
        raise NotImplementedError
