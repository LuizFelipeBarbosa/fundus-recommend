from __future__ import annotations

from dataclasses import replace

from fundus_recommend.ingest.types import AdapterType, PublisherConfig

DEFAULT_PUBLISHER_IDS: tuple[str, ...] = (
    "reuters",
    "nyt",
    "washington-post",
    "cnn",
    "bloomberg",
    "npr",
    "wsj",
    "axios",
    "propublica",
    "politico",
    "the-atlantic",
)

PUBLISHER_REGISTRY: dict[str, PublisherConfig] = {
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


def _legacy_fundus_country(token: str) -> PublisherConfig | None:
    from fundus import PublisherCollection

    code = token.strip().lower()
    collection = getattr(PublisherCollection, code, None)
    if collection is None:
        return None

    return PublisherConfig(
        publisher_id=f"fundus-country:{code}",
        display_name=f"Fundus country collection '{code}'",
        adapter=AdapterType.FUNDUS,
        fundus_collection=code,
        legacy_token=token,
    )


def resolve_publisher_token(token: str) -> tuple[PublisherConfig | None, str | None]:
    key = token.strip().lower()
    if not key:
        return None, None

    config = PUBLISHER_REGISTRY.get(key)
    if config is not None:
        return replace(config), None

    legacy = _legacy_fundus_country(key)
    if legacy is not None:
        warning = (
            f"Legacy country token '{token}' is deprecated; "
            "use explicit publisher IDs instead."
        )
        return legacy, warning

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
