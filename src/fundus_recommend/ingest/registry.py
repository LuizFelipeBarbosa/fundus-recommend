from __future__ import annotations

from dataclasses import replace

from fundus_recommend.ingest.types import AdapterType, PublisherConfig

# ---------------------------------------------------------------------------
# Fundus country / region collections
# ---------------------------------------------------------------------------
# Each entry maps a two- or three-letter code (matching the fundus
# ``PublisherCollection`` attribute) to a ``PublisherConfig`` that uses the
# FUNDUS adapter.  ``default_language`` mirrors the value declared in the
# corresponding ``PublisherGroup``.
# ---------------------------------------------------------------------------

_FUNDUS_COUNTRIES: dict[str, tuple[str, str]] = {
    # code: (display_name, default_language)
    "ar": ("Argentina", "es"),
    "at": ("Austria", "de"),
    "au": ("Australia", "en"),
    "bd": ("Bangladesh", "bn"),
    "be": ("Belgium", "nl"),
    "br": ("Brazil", "pt"),
    "ca": ("Canada", "en"),
    "ch": ("Switzerland", "de"),
    "cl": ("Chile", "es"),
    "cn": ("China", "zh"),
    "co": ("Colombia", "es"),
    "cz": ("Czech Republic", "cs"),
    "de": ("Germany", "de"),
    "dk": ("Denmark", "da"),
    "eg": ("Egypt", "ar"),
    "es": ("Spain", "es"),
    "fi": ("Finland", "fi"),
    "fr": ("France", "fr"),
    "gl": ("Greenland", "kl"),
    "gr": ("Greece", "el"),
    "hk": ("Hong Kong", "en"),
    "hu": ("Hungary", "hu"),
    "id": ("Indonesia", "id"),
    "ie": ("Ireland", "en"),
    "il": ("Israel", "he"),
    "ind": ("India", "hi"),
    "intl": ("International", "en"),
    "isl": ("Iceland", "is"),
    "it": ("Italy", "it"),
    "jp": ("Japan", "ja"),
    "ke": ("Kenya", "en"),
    "kr": ("South Korea", "ko"),
    "lb": ("Lebanon", "ar"),
    "li": ("Liechtenstein", "de"),
    "ls": ("Lesotho", "en"),
    "lt": ("Lithuania", "lt"),
    "lu": ("Luxembourg", "de"),
    "mx": ("Mexico", "es"),
    "my": ("Malaysia", "ms"),
    "na": ("Namibia", "en"),
    "ng": ("Nigeria", "en"),
    "nl": ("Netherlands", "nl"),
    "no": ("Norway", "no"),
    "nz": ("New Zealand", "en"),
    "ph": ("Philippines", "en"),
    "pk": ("Pakistan", "en"),
    "pl": ("Poland", "pl"),
    "pt": ("Portugal", "pt"),
    "py": ("Paraguay", "es"),
    "ro": ("Romania", "ro"),
    "ru": ("Russia", "ru"),
    "sa": ("Saudi Arabia", "ar"),
    "se": ("Sweden", "sv"),
    "sg": ("Singapore", "en"),
    "th": ("Thailand", "en"),
    "tr": ("Turkey", "tr"),
    "tw": ("Taiwan", "tw"),
    "tz": ("Tanzania", "sw"),
    "ua": ("Ukraine", "uk"),
    "uk": ("United Kingdom", "en"),
    "us": ("United States", "en"),
    "ve": ("Venezuela", "es"),
    "vn": ("Vietnam", "vi"),
    "za": ("South Africa", "en"),
}

PUBLISHER_REGISTRY: dict[str, PublisherConfig] = {
    code: PublisherConfig(
        publisher_id=code,
        display_name=display_name,
        adapter=AdapterType.FUNDUS,
        fundus_collection=code,
        default_language=lang,
    )
    for code, (display_name, lang) in _FUNDUS_COUNTRIES.items()
}

# ---------------------------------------------------------------------------
# Named / non-fundus publishers (kept for explicit use)
# ---------------------------------------------------------------------------

PUBLISHER_REGISTRY.update(
    {
        "reuters": PublisherConfig(
            publisher_id="reuters",
            display_name="Reuters",
            adapter=AdapterType.LICENSED_FEED,
            requires_credentials=True,
            credential_env="REUTERS_LICENSED_FEED_URL",
        ),
        "nyt": PublisherConfig(
            publisher_id="nyt",
            display_name="New York Times",
            adapter=AdapterType.OFFICIAL_API,
            requires_credentials=True,
            credential_env="NYT_API_KEY",
        ),
        "washington-post": PublisherConfig(
            publisher_id="washington-post",
            display_name="Washington Post",
            adapter=AdapterType.RSS,
            feed_urls=(
                "https://feeds.washingtonpost.com/rss/world",
                "https://feeds.washingtonpost.com/rss/national",
            ),
            default_language="en",
        ),
        "cnn": PublisherConfig(
            publisher_id="cnn",
            display_name="CNN",
            adapter=AdapterType.RSS,
            feed_urls=("http://rss.cnn.com/rss/edition.rss",),
            default_language="en",
        ),
        "bloomberg": PublisherConfig(
            publisher_id="bloomberg",
            display_name="Bloomberg",
            adapter=AdapterType.LICENSED_FEED,
            requires_credentials=True,
            credential_env="BLOOMBERG_LICENSED_FEED_URL",
        ),
        "npr": PublisherConfig(
            publisher_id="npr",
            display_name="NPR",
            adapter=AdapterType.RSS,
            feed_urls=("https://feeds.npr.org/1001/rss.xml",),
            default_language="en",
        ),
        "wsj": PublisherConfig(
            publisher_id="wsj",
            display_name="Wall Street Journal",
            adapter=AdapterType.LICENSED_FEED,
            requires_credentials=True,
            credential_env="WSJ_LICENSED_FEED_URL",
        ),
        "axios": PublisherConfig(
            publisher_id="axios",
            display_name="Axios",
            adapter=AdapterType.LICENSED_FEED,
            requires_credentials=True,
            credential_env="AXIOS_LICENSED_FEED_URL",
        ),
        "propublica": PublisherConfig(
            publisher_id="propublica",
            display_name="ProPublica",
            adapter=AdapterType.RSS,
            feed_urls=("https://www.propublica.org/feeds/propublica/main",),
            default_language="en",
        ),
        "politico": PublisherConfig(
            publisher_id="politico",
            display_name="Politico",
            adapter=AdapterType.LICENSED_FEED,
            requires_credentials=True,
            credential_env="POLITICO_LICENSED_FEED_URL",
        ),
        "the-atlantic": PublisherConfig(
            publisher_id="the-atlantic",
            display_name="The Atlantic",
            adapter=AdapterType.RSS,
            feed_urls=("https://www.theatlantic.com/feed/all/",),
            default_language="en",
        ),
    }
)

# Default set: all fundus country collections
DEFAULT_PUBLISHER_IDS: tuple[str, ...] = tuple(_FUNDUS_COUNTRIES.keys())


def resolve_publisher_token(token: str) -> tuple[PublisherConfig | None, str | None]:
    key = token.strip().lower()
    if not key:
        return None, None

    config = PUBLISHER_REGISTRY.get(key)
    if config is not None:
        return replace(config), None

    return None, None


def resolve_publisher_tokens(tokens: list[str]) -> tuple[list[PublisherConfig], list[str], list[str]]:
    configs: list[PublisherConfig] = []
    warnings: list[str] = []
    unknown: list[str] = []

    for token in tokens:
        config, warning = resolve_publisher_token(token)
        if config is None:
            unknown.append(token)
            continue
        configs.append(config)
        if warning:
            warnings.append(warning)

    return configs, warnings, unknown
