"""Publisher authority tiers for ranking.

Maps publisher names to authority scores [0.0, 1.0] based on editorial
judgement of credibility and reputation.  Three tiers:

- Tier 1 (1.0): Wire services, papers of record, major internationals
- Tier 2 (0.7): Established national / digital outlets
- Tier 3 (0.4): Tabloids, regional, niche, and unknown publishers
"""

from __future__ import annotations

_TIER_1: frozenset[str] = frozenset(
    {
        # Wire services
        "Associated Press News",
        "Reuters",
        "Afp",
        "Dpa",
        "Ansa",
        "Kyodonews",
        # US papers of record / major outlets
        "Nytimes",
        "Washington Post",
        "Wsj",
        "Los Angeles Times",
        "The Washington Times",
        "The New Yorker",
        "Bloomberg",
        "CNN",
        "Npr",
        # UK
        "The Guardian",
        "The BBC",
        "Ft",
        "Economist",
        "Nature",
        # France
        "Le Monde",
        "Le Figaro",
        # Germany
        "Frankfurter Allgemeine Zeitung",
        "Süddeutsche Zeitung",
        "Die Zeit",
        "Tagesschau",
        "Deutsche Welle",
        "ZDF",
        # Other international
        "Aljazeera",
        "Voice Of America",
        "CBC News",
        "The Globe and Mail",
        "Neue Zürcher Zeitung (NZZ)",
        "El País",
        "Corriere della Sera",
    }
)

_TIER_2: frozenset[str] = frozenset(
    {
        # US
        "CNBC",
        "Business Insider",
        "Fox News",
        "The Intercept",
        "TechCrunch",
        "Wired",
        "Rolling Stone",
        "The Nation",
        "Propublica",
        "Theatlantic",
        "Politico",
        "Axios",
        "USA Today",
        "CBS News",
        "NBC News",
        "ABC News",
        "Newsweek",
        # UK
        "The Independent",
        "Thetimes",
        "The Telegraph",
        "Sky",
        "Euronews (EN)",
        # France
        "Les Échos",
        "France24",
        "Liberation",
        "Euronews (FR)",
        # Germany
        "Spiegel Online",
        "Die Welt",
        "Stern",
        "Focus Online",
        "Bild",
        "N-Tv",
        "T-Online",
        "Tagesspiegel",
        "Berliner Zeitung",
        "Die Tageszeitung (taz)",
        "Handelsblatt",
        "Deutschlandfunk",
        "Frankfurter Rundschau",
        "Euronews (DE)",
        # Switzerland
        "Schweizer Radio und Fernsehen",
        # Italy
        "La Repubblica",
        # Netherlands
        "Nos",
        "Nrc",
        # Nordics
        "Politiken",
        "Dr",
        "Norsk rikskringkasting",
        "Yle",
        # Asia-Pacific
        "Scmp",
        "Straitstimes",
        "Channelnewsasia",
        "Nine News",
        "Times Of India",
        "Thehindu",
        "Ndtv",
        "Asahi Shimbun",
        "The Nikkei",
        "Nhk Or",
        "Kompas",
        "Dawn",
        "Rappler",
        # Middle East / Africa
        "Haaretz",
        "Daily Maverick",
        # Eastern Europe
        "Ukrainska Pravda",
        "Kyivindependent",
        "Meduza",
        # Other
        "Rest of World",
    }
)

_DEFAULT_SCORE: float = 0.4


def authority_score(publisher: str) -> float:
    """Return an authority score in [0.0, 1.0] for *publisher*."""
    if publisher in _TIER_1:
        return 1.0
    if publisher in _TIER_2:
        return 0.7
    return _DEFAULT_SCORE
