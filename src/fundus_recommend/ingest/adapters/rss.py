from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser
from lxml import html as lxml_html

from fundus_recommend.ingest.adapters.base import AdapterRunOutput, BaseAdapter
from fundus_recommend.ingest.fetcher import HttpFetcher
from fundus_recommend.ingest.policy import PolicyState
from fundus_recommend.ingest.types import CrawlArticleCandidate, FetchPolicy, PublisherConfig


def _parse_entry_date(entry: dict) -> datetime | None:
    for key in ("published", "updated"):
        value = entry.get(key)
        if not value:
            continue
        try:
            parsed = parsedate_to_datetime(value)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except Exception:
            continue
    return None


def _extract_article_fields(raw_html: str) -> tuple[str | None, str | None, str | None, str | None]:
    try:
        doc = lxml_html.fromstring(raw_html)
    except Exception:
        return None, None, None, None

    title = None
    title_candidates = doc.xpath("//meta[@property='og:title']/@content")
    if title_candidates:
        title = title_candidates[0].strip()
    if not title:
        title_text = doc.xpath("//title/text()")
        if title_text:
            title = title_text[0].strip()

    image = None
    image_candidates = doc.xpath("//meta[@property='og:image']/@content")
    if image_candidates:
        image = image_candidates[0].strip()

    lang = None
    lang_candidates = doc.xpath("//html/@lang")
    if lang_candidates:
        lang = lang_candidates[0].strip()

    paragraphs = [p.text_content().strip() for p in doc.xpath("//p")]
    body_parts = [p for p in paragraphs if p and len(p) > 20]
    body = "\n\n".join(body_parts[:80]) if body_parts else None

    return title, body, image, lang


class RSSAdapter(BaseAdapter):
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
        output = AdapterRunOutput()
        candidates: list[CrawlArticleCandidate] = []
        seen_links: set[str] = set()

        for feed_url in config.feed_urls:
            if len(candidates) >= max_articles:
                break

            feed_response = fetcher.fetch(feed_url, headers=None, state=state, histogram=status_histogram)
            if not feed_response.ok or feed_response.text is None:
                output.skipped_count += 1
                continue

            feed = feedparser.parse(feed_response.text)
            entries = feed.get("entries", [])
            for entry in entries:
                if len(candidates) >= max_articles:
                    break

                link = (entry.get("link") or "").strip()
                if not link or link in seen_links:
                    continue
                seen_links.add(link)

                output.crawled_count += 1
                article_response = fetcher.fetch(link, headers=None, state=state, histogram=status_histogram)
                if not article_response.ok or article_response.text is None:
                    output.skipped_count += 1
                    continue

                title, body, cover_image_url, html_lang = _extract_article_fields(article_response.text)
                if not title or not body:
                    status_histogram["parse_error"] = status_histogram.get("parse_error", 0) + 1
                    output.skipped_count += 1
                    continue

                final_language = language or config.default_language or html_lang
                if language and final_language and final_language != language:
                    output.skipped_count += 1
                    continue

                authors: list[str] = []
                author = entry.get("author")
                if author:
                    authors = [str(author)]

                topics = [tag["term"] for tag in entry.get("tags", []) if isinstance(tag, dict) and tag.get("term")]

                candidates.append(
                    CrawlArticleCandidate(
                        url=article_response.final_url,
                        title=title,
                        body=body,
                        publisher=config.display_name,
                        language=final_language,
                        publishing_date=_parse_entry_date(entry),
                        cover_image_url=cover_image_url,
                        authors=authors,
                        topics=topics,
                    )
                )

        output.candidates = candidates
        output.outcome = "success"
        return output
