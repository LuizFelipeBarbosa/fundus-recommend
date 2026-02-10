from datetime import datetime, timezone
import unittest

from fundus_recommend.services.date_resolution import resolve_article_publishing_date


class _FakeHtml:
    def __init__(self, content: str):
        self.content = content


class _FakeArticle:
    def __init__(self, publisher: str, publishing_date: datetime | None, html: str):
        self.publisher = publisher
        self.publishing_date = publishing_date
        self.html = _FakeHtml(html)


class DateResolutionTests(unittest.TestCase):
    def test_resolve_anadolu_with_ddmmyyyy(self) -> None:
        article = _FakeArticle(
            publisher="Anadolu Ajansı",
            publishing_date=datetime(2026, 9, 2, tzinfo=timezone.utc),
            html="""
                <html>
                  <body>
                    <div class="detay-bg"><div><div><div><span class="tarih">
                      09.02.2026 - Güncelleme : 09.02.2026
                    </span></div></div></div></div>
                  </body>
                </html>
            """,
        )

        resolved = resolve_article_publishing_date(article, now_utc=datetime(2026, 2, 9, 12, tzinfo=timezone.utc))
        self.assertEqual(resolved, datetime(2026, 2, 9, tzinfo=timezone.utc))

    def test_resolve_klasse_with_ddmmyyyy(self) -> None:
        article = _FakeArticle(
            publisher="Klasse Gegen Klasse",
            publishing_date=datetime(2026, 6, 2, tzinfo=timezone.utc),
            html="""
                <html>
                  <body>
                    <div class="metaInfoDateTime"><span>06.02.2026</span></div>
                  </body>
                </html>
            """,
        )

        resolved = resolve_article_publishing_date(article, now_utc=datetime(2026, 2, 6, 12, tzinfo=timezone.utc))
        self.assertEqual(resolved, datetime(2026, 2, 6, tzinfo=timezone.utc))

    def test_non_target_iso_date_is_unchanged(self) -> None:
        source_date = datetime(2026, 2, 9, 17, 45, tzinfo=timezone.utc)
        article = _FakeArticle(
            publisher="Rolling Stone",
            publishing_date=source_date,
            html="<html><body></body></html>",
        )

        resolved = resolve_article_publishing_date(article, now_utc=datetime(2026, 2, 9, 18, tzinfo=timezone.utc))
        self.assertEqual(resolved, source_date)

    def test_generic_fallback_swaps_future_ambiguous_dates(self) -> None:
        article = _FakeArticle(
            publisher="Some Publisher",
            publishing_date=datetime(2026, 6, 2, tzinfo=timezone.utc),
            html="<html><body></body></html>",
        )

        resolved = resolve_article_publishing_date(article, now_utc=datetime(2026, 2, 6, 1, tzinfo=timezone.utc))
        self.assertEqual(resolved, datetime(2026, 2, 6, tzinfo=timezone.utc))

    def test_generic_fallback_does_not_swap_non_future_ambiguous_dates(self) -> None:
        source_date = datetime(2026, 2, 5, tzinfo=timezone.utc)
        article = _FakeArticle(
            publisher="Some Publisher",
            publishing_date=source_date,
            html="<html><body></body></html>",
        )

        resolved = resolve_article_publishing_date(article, now_utc=datetime(2026, 2, 6, 1, tzinfo=timezone.utc))
        self.assertEqual(resolved, source_date)


if __name__ == "__main__":
    unittest.main()
