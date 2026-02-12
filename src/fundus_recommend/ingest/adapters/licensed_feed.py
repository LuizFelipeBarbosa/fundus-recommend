from __future__ import annotations

import os

from fundus_recommend.ingest.adapters.base import AdapterRunOutput, BaseAdapter
from fundus_recommend.ingest.fetcher import HttpFetcher
from fundus_recommend.ingest.policy import PolicyState
from fundus_recommend.ingest.types import FetchPolicy, PublisherConfig


class LicensedFeedAdapter(BaseAdapter):
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
        output = AdapterRunOutput(outcome="skipped")

        config_name = config.credential_env
        feed_ref = os.getenv(config_name) if config_name else None
        if not feed_ref:
            output.skip_reason = "missing_contract_or_feed"
            return output

        output.skip_reason = "licensed_feed_not_implemented"
        output.error_message = f"Licensed feed adapter for '{config.publisher_id}' is not implemented yet"
        return output
