from __future__ import annotations

from fundus_recommend.ingest.adapters.base import AdapterRunOutput, BaseAdapter
from fundus_recommend.ingest.fetcher import HttpFetcher
from fundus_recommend.ingest.policy import PolicyState
from fundus_recommend.ingest.types import CrawlArticleCandidate, FetchPolicy, PublisherConfig


class FundusAdapter(BaseAdapter):
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
        from fundus import Crawler, PublisherCollection

        output = AdapterRunOutput()

        target = None
        if config.fundus_collection:
            collection = getattr(PublisherCollection, config.fundus_collection, None)
            if collection is None:
                output.outcome = "failed"
                output.error_message = f"Unknown Fundus collection: {config.fundus_collection}"
                return output
            target = collection
            if config.fundus_symbol:
                target = getattr(collection, config.fundus_symbol, None)
                if target is None:
                    output.outcome = "failed"
                    output.error_message = (
                        f"Unknown Fundus publisher symbol '{config.fundus_symbol}' "
                        f"in collection '{config.fundus_collection}'"
                    )
                    return output

        if target is None:
            output.outcome = "failed"
            output.error_message = "Fundus target configuration is missing"
            return output

        crawler = Crawler(target)
        candidates: list[CrawlArticleCandidate] = []

        for article in crawler.crawl(
            max_articles=max_articles,
            only_complete=False,
            error_handling="catch",
            timeout=policy.timeout_seconds,
        ):
            exception = getattr(article, "exception", None)
            if exception is not None:
                status_histogram["fundus_exception"] = status_histogram.get("fundus_exception", 0) + 1
                output.skipped_count += 1
                continue

            article_lang = getattr(article, "lang", None)
            if language and article_lang and article_lang != language:
                output.skipped_count += 1
                continue

            url = getattr(article.html, "responded_url", None) or getattr(article.html, "requested_url", None)
            title = getattr(article, "title", None)
            body = str(getattr(article, "body", "") or "")
            if not url or not title or not body:
                status_histogram["parse_error"] = status_histogram.get("parse_error", 0) + 1
                output.skipped_count += 1
                continue

            cover = None
            images = getattr(article, "images", None)
            if images:
                cover = images[0].url

            candidates.append(
                CrawlArticleCandidate(
                    url=url,
                    title=title,
                    body=body,
                    authors=list(getattr(article, "authors", []) or []),
                    topics=list(getattr(article, "topics", []) or []),
                    publisher=getattr(article, "publisher", config.display_name),
                    language=article_lang,
                    publishing_date=getattr(article, "publishing_date", None),
                    cover_image_url=cover,
                )
            )
            output.crawled_count += 1
            status_histogram["fundus_yielded"] = status_histogram.get("fundus_yielded", 0) + 1

            if len(candidates) >= max_articles:
                break

        output.candidates = candidates
        output.outcome = "success"
        return output
