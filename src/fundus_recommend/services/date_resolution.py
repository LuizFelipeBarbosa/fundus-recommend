from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import re
from typing import Any, Callable

import lxml.html

FUTURE_TOLERANCE = timedelta(days=1)
_DDMMYYYY_PATTERN = re.compile(r"(\d{2}\.\d{2}\.\d{4})")


@dataclass(frozen=True)
class _PublisherDateExtractor:
    publisher: str
    extractor: Callable[[Any], datetime | None]


def _parse_ddmmyyyy(value: str) -> datetime | None:
    match = _DDMMYYYY_PATTERN.search(value)
    if match is None:
        return None
    return datetime.strptime(match.group(1), "%d.%m.%Y")


def _article_doc(article: Any) -> lxml.html.HtmlElement | None:
    html_obj = getattr(article, "html", None)
    if html_obj is None:
        return None
    content = getattr(html_obj, "content", None)
    if not content:
        return None
    try:
        return lxml.html.fromstring(content)
    except (TypeError, ValueError):
        return None


def _extract_anadolu_date(article: Any) -> datetime | None:
    doc = _article_doc(article)
    if doc is None:
        return None
    nodes = doc.cssselect("div.detay-bg > div > div > div > span.tarih")
    if not nodes:
        return None
    return _parse_ddmmyyyy(nodes[0].text_content())


def _extract_klasse_date(article: Any) -> datetime | None:
    doc = _article_doc(article)
    if doc is None:
        return None
    nodes = doc.xpath("(//div[@class='metaInfoDateTime']/span)[1]")
    if not nodes:
        return None
    return _parse_ddmmyyyy(nodes[0].text_content())


_EXTRACTORS: tuple[_PublisherDateExtractor, ...] = (
    _PublisherDateExtractor("Anadolu Ajansı", _extract_anadolu_date),
    _PublisherDateExtractor("Klasse Gegen Klasse", _extract_klasse_date),
)


def is_ambiguous_month_day(value: datetime) -> bool:
    return value.month <= 12 and value.day <= 12


def swap_month_day(value: datetime) -> datetime | None:
    if not is_ambiguous_month_day(value):
        return None
    try:
        return value.replace(month=value.day, day=value.month)
    except ValueError:
        return None


def _coerce_now(now_utc: datetime | None) -> datetime:
    if now_utc is None:
        return datetime.now(timezone.utc)
    if now_utc.tzinfo is None:
        return now_utc.replace(tzinfo=timezone.utc)
    return now_utc.astimezone(timezone.utc)


def _normalize(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
    return value


def _resolve_publisher_specific_date(article: Any) -> datetime | None:
    publisher = getattr(article, "publisher", None)
    for extractor in _EXTRACTORS:
        if publisher == extractor.publisher:
            return extractor.extractor(article)
    return None


def resolve_article_publishing_date(article: Any, now_utc: datetime | None = None) -> datetime | None:
    now = _coerce_now(now_utc)

    raw_publisher_date = _resolve_publisher_specific_date(article)
    parsed = _normalize(raw_publisher_date)
    if parsed is None:
        parsed = _normalize(getattr(article, "publishing_date", None))
    if parsed is None:
        return None

    if not is_ambiguous_month_day(parsed):
        return parsed
    if parsed <= now + FUTURE_TOLERANCE:
        return parsed

    swapped = swap_month_day(parsed)
    if swapped is None:
        return parsed
    if swapped <= now + FUTURE_TOLERANCE:
        return swapped
    return parsed
