from __future__ import annotations

import os

from fundus_recommend.ingest.adapters.base import AdapterRunOutput, BaseAdapter
from fundus_recommend.ingest.fetcher import HttpFetcher
from fundus_recommend.ingest.policy import PolicyState
from fundus_recommend.ingest.types import FetchPolicy, PublisherConfig


class OfficialAPIAdapter(BaseAdapter):
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

        key_name = config.credential_env
        credential = os.getenv(key_name) if key_name else None
        if not credential:
            output.skip_reason = "missing_credentials"
            return output

        output.skip_reason = "official_api_not_implemented"
        output.error_message = f"Official API adapter for '{config.publisher_id}' is not implemented yet"
        return output
