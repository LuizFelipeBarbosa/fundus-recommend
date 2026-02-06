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
        "Associated Press News",
        "The Guardian",
        "Le Monde",
        "Los Angeles Times",
        "The Washington Times",
        "The New Yorker",
        "Nature",
        "Voice Of America",
        "Frankfurter Allgemeine Zeitung",
        "Süddeutsche Zeitung",
        "Die Zeit",
        "Tagesschau",
        "Le Figaro",
        "Deutsche Welle",
        "ZDF",
    }
)

_TIER_2: frozenset[str] = frozenset(
    {
        "The Independent",
        "Business Insider",
        "Fox News",
        "CNBC",
        "The Intercept",
        "TechCrunch",
        "Wired",
        "Rolling Stone",
        "Euronews (EN)",
        "Euronews (FR)",
        "Euronews (DE)",
        "Spiegel Online",
        "Die Welt",
        "Stern",
        "Focus Online",
        "Nine News",
        "Rest of World",
        "The Nation",
        "Bild",
        "N-Tv",
        "T-Online",
        "Tagesspiegel",
        "Berliner Zeitung",
        "Die Tageszeitung (taz)",
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
