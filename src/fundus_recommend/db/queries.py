from dataclasses import dataclass
from datetime import datetime, timezone
import math

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer

from fundus_recommend.config import settings
from fundus_recommend.models.db import Article, ArticleView, User, UserPreference
from fundus_recommend.services.embeddings import embed_single
from fundus_recommend.services.publisher_authority import authority_score, publisher_tier
from fundus_recommend.services.ranking import RankingWeights, composite_scores


@dataclass
class RankedStory:
    story_id: str
    dedup_cluster_id: int | None
    lead_article: Article
    articles: list[Article]


@dataclass
class _EligibleStory:
    story_key: str
    lead_article: Article
    source_count: int
    popularity_score: float


def _as_utc_timestamp(dt: datetime | None) -> float:
    if dt is None:
        return float("-inf")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


def _story_key(article: Article) -> str:
    if article.dedup_cluster_id is not None:
        return f"cluster:{article.dedup_cluster_id}"
    return f"article:{article.id}"


def _dedupe_articles_by_id(articles: list[Article]) -> list[Article]:
    deduped: list[Article] = []
    seen_ids: set[int] = set()
    for article in articles:
        if article.id in seen_ids:
            continue
        seen_ids.add(article.id)
        deduped.append(article)
    return deduped


def _compute_popularity_scores(articles: list[Article], view_counts: dict[int, int]) -> np.ndarray:
    dates = [a.publishing_date for a in articles]
    views = [view_counts.get(a.id, 0) for a in articles]
    cluster_ids = [a.dedup_cluster_id for a in articles]

    # Compute cluster sizes: how many articles share each dedup_cluster_id.
    cluster_size_map: dict[int, int] = {}
    for cid in cluster_ids:
        if cid is not None:
            cluster_size_map[cid] = cluster_size_map.get(cid, 0) + 1
    cluster_sizes = [cluster_size_map.get(cid, 1) if cid is not None else 1 for cid in cluster_ids]

    authorities = [authority_score(a.publisher) for a in articles]

    weights = RankingWeights(
        freshness=settings.ranking_freshness_weight,
        prominence=settings.ranking_prominence_weight,
        authority=settings.ranking_authority_weight,
        engagement=settings.ranking_engagement_weight,
        diversity_lambda=settings.ranking_diversity_lambda,
        half_life_hours=settings.ranking_recency_half_life_hours,
    )

    return composite_scores(dates, views, weights, cluster_sizes, authorities)


def _coverage_score(source_count: int) -> float:
    """Absolute coverage score: 1 source → 0.0, 10+ sources → 1.0."""
    if source_count <= 1:
        return 0.0
    return min(1.0, math.log1p(source_count) / math.log1p(10))


def _recency_sort_key(article: Article) -> tuple[float, int]:
    return (-_as_utc_timestamp(article.publishing_date), -article.id)


def _lead_priority_tuple(
    article: Article,
    popularity_score_by_article_id: dict[int, float],
) -> tuple[float, float, int]:
    return (
        popularity_score_by_article_id.get(article.id, float("-inf")),
        _as_utc_timestamp(article.publishing_date),
        article.id,
    )


async def _fetch_cluster_articles(
    session: AsyncSession,
    cluster_ids: list[int],
) -> dict[int, list[Article]]:
    if not cluster_ids:
        return {}

    result = await session.execute(
        select(Article)
        .options(defer(Article.body), defer(Article.embedding))
        .where(Article.dedup_cluster_id.in_(cluster_ids))
        .order_by(
            Article.dedup_cluster_id.asc(),
            Article.publishing_date.desc().nulls_last(),
            Article.id.desc(),
        )
    )

    story_articles_by_cluster: dict[int, list[Article]] = {}
    for article in result.scalars().all():
        cluster_id = article.dedup_cluster_id
        if cluster_id is None:
            continue
        story_articles_by_cluster.setdefault(cluster_id, []).append(article)

    return story_articles_by_cluster


def _order_story_articles(lead_article: Article, story_articles: list[Article]) -> list[Article]:
    # Preserve lead article identity in the response, then order supporters by tier and recency.
    deduped = _dedupe_articles_by_id([lead_article, *story_articles])
    tier_buckets: dict[int, list[Article]] = {1: [], 2: [], 3: []}

    for article in deduped:
        if article.id == lead_article.id:
            continue
        tier_buckets[publisher_tier(article.publisher)].append(article)

    for tier in (1, 2, 3):
        tier_buckets[tier].sort(key=_recency_sort_key)

    return _dedupe_articles_by_id(
        [
            lead_article,
            *tier_buckets[1],
            *tier_buckets[2],
            *tier_buckets[3],
        ]
    )


def _story_quality_sort_key(
    story_key: str,
    final_score_by_story_key: dict[str, float],
    source_count_by_story_key: dict[str, int],
    lead_by_story_key: dict[str, Article],
) -> tuple[float, int, float, int]:
    lead_article = lead_by_story_key[story_key]
    return (
        -final_score_by_story_key[story_key],
        -source_count_by_story_key.get(story_key, 1),
        -_as_utc_timestamp(lead_article.publishing_date),
        -lead_article.id,
    )


async def _build_tier_anchored_story_ranking(
    session: AsyncSession,
    candidate_articles: list[Article],
    popularity_score_by_article_id: dict[int, float],
    exclude_story_key: str | None = None,
) -> tuple[list[str], dict[str, Article], dict[str, float]]:
    if not candidate_articles:
        return [], {}, {}

    candidate_by_story_key: dict[str, list[Article]] = {}
    cluster_ids: set[int] = set()

    for article in candidate_articles:
        story_key = _story_key(article)
        if exclude_story_key is not None and story_key == exclude_story_key:
            continue
        candidate_by_story_key.setdefault(story_key, []).append(article)
        if article.dedup_cluster_id is not None:
            cluster_ids.add(article.dedup_cluster_id)

    if not candidate_by_story_key:
        return [], {}, {}

    story_articles_by_cluster = await _fetch_cluster_articles(session, sorted(cluster_ids))
    all_eligible_stories: list[_EligibleStory] = []

    for story_key, story_candidate_articles in candidate_by_story_key.items():
        first_article = story_candidate_articles[0]
        cluster_id = first_article.dedup_cluster_id
        full_story_articles = (
            story_articles_by_cluster.get(cluster_id, story_candidate_articles)
            if cluster_id is not None
            else story_candidate_articles
        )
        full_story_articles = _dedupe_articles_by_id(full_story_articles)
        if not full_story_articles:
            continue

        # Skip runaway transitive-chain clusters
        if len(full_story_articles) > 200:
            continue

        # Select lead article: prefer Tier 1 > Tier 2 > any
        tier_1_articles = [a for a in full_story_articles if publisher_tier(a.publisher) == 1]
        tier_2_articles = [a for a in full_story_articles if publisher_tier(a.publisher) == 2]

        if tier_1_articles:
            lead_pool = tier_1_articles
        elif tier_2_articles:
            lead_pool = tier_2_articles
        else:
            lead_pool = full_story_articles

        lead_article = max(
            lead_pool,
            key=lambda article: _lead_priority_tuple(article, popularity_score_by_article_id),
        )

        lead_popularity_score = popularity_score_by_article_id.get(lead_article.id, float("-inf"))
        if lead_popularity_score == float("-inf"):
            lead_popularity_score = max(
                (popularity_score_by_article_id.get(a.id, float("-inf")) for a in story_candidate_articles),
                default=0.0,
            )
        if lead_popularity_score == float("-inf"):
            lead_popularity_score = 0.0

        all_eligible_stories.append(
            _EligibleStory(
                story_key=story_key,
                lead_article=lead_article,
                source_count=len(full_story_articles),
                popularity_score=float(lead_popularity_score),
            )
        )

    if not all_eligible_stories:
        return [], {}, {}

    lead_by_story_key: dict[str, Article] = {}
    source_count_by_story_key: dict[str, int] = {}
    final_score_by_story_key: dict[str, float] = {}

    for story in all_eligible_stories:
        lead_by_story_key[story.story_key] = story.lead_article
        source_count_by_story_key[story.story_key] = story.source_count
        coverage = _coverage_score(story.source_count)
        reputation = authority_score(story.lead_article.publisher)
        final_score_by_story_key[story.story_key] = (
            settings.top_story_score_popularity_weight * story.popularity_score
            + settings.top_story_score_coverage_weight * coverage
            + settings.top_story_score_reputation_weight * reputation
        )

    ordered_story_keys = sorted(
        [s.story_key for s in all_eligible_stories],
        key=lambda sk: _story_quality_sort_key(
            sk, final_score_by_story_key, source_count_by_story_key, lead_by_story_key
        ),
    )
    return ordered_story_keys, lead_by_story_key, final_score_by_story_key


async def _expand_ranked_stories(
    session: AsyncSession,
    lead_by_story_key: dict[str, Article],
    story_keys: list[str],
) -> list[RankedStory]:
    if not story_keys:
        return []

    page_cluster_ids = sorted(
        {
            lead_by_story_key[story_key].dedup_cluster_id
            for story_key in story_keys
            if lead_by_story_key[story_key].dedup_cluster_id is not None
        }
    )

    story_articles_by_cluster = await _fetch_cluster_articles(session, page_cluster_ids)

    stories: list[RankedStory] = []
    for story_key in story_keys:
        lead_article = lead_by_story_key[story_key]
        cluster_id = lead_article.dedup_cluster_id

        if cluster_id is None:
            story_articles = [lead_article]
        else:
            grouped_articles = story_articles_by_cluster.get(cluster_id, [])
            if grouped_articles:
                story_articles = _order_story_articles(lead_article, grouped_articles)
            else:
                story_articles = [lead_article]

        stories.append(
            RankedStory(
                story_id=story_key,
                dedup_cluster_id=cluster_id,
                lead_article=lead_article,
                articles=story_articles,
            )
        )

    return stories


async def _rank_story_candidates(
    session: AsyncSession,
    candidate_articles: list[Article],
    limit: int,
    exclude_story_key: str | None = None,
) -> list[tuple[RankedStory, float]]:
    if limit <= 0:
        return []

    articles = _dedupe_articles_by_id(candidate_articles)
    if not articles:
        return []

    view_counts = await get_view_counts(session)
    scores = _compute_popularity_scores(articles, view_counts)
    popularity_score_by_article_id = {
        article.id: float(scores[idx]) for idx, article in enumerate(articles)
    }
    ordered_story_keys, lead_by_story_key, final_score_by_story_key = await _build_tier_anchored_story_ranking(
        session,
        articles,
        popularity_score_by_article_id,
        exclude_story_key=exclude_story_key,
    )
    selected_story_keys = ordered_story_keys[:limit]
    stories = await _expand_ranked_stories(session, lead_by_story_key, selected_story_keys)

    return [(story, final_score_by_story_key[story.story_id]) for story in stories]


async def get_article_count(session: AsyncSession) -> int:
    result = await session.execute(select(func.count(Article.id)))
    return result.scalar_one()


async def get_embedded_count(session: AsyncSession) -> int:
    result = await session.execute(select(func.count(Article.id)).where(Article.embedding.is_not(None)))
    return result.scalar_one()


async def list_articles(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    publisher: str | None = None,
    language: str | None = None,
    topic: str | None = None,
    category: str | None = None,
) -> tuple[list[Article], int]:
    query = select(Article).options(defer(Article.body), defer(Article.embedding))
    count_query = select(func.count(Article.id))

    if publisher:
        query = query.where(Article.publisher == publisher)
        count_query = count_query.where(Article.publisher == publisher)
    if language:
        query = query.where(Article.language == language)
        count_query = count_query.where(Article.language == language)
    if topic:
        query = query.where(Article.topics.any(topic))
        count_query = count_query.where(Article.topics.any(topic))
    if category:
        query = query.where(Article.category == category)
        count_query = count_query.where(Article.category == category)

    total = (await session.execute(count_query)).scalar_one()

    query = query.order_by(Article.publishing_date.desc().nulls_last()).offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    return list(result.scalars().all()), total


async def get_article_by_id(session: AsyncSession, article_id: int) -> Article | None:
    result = await session.execute(select(Article).where(Article.id == article_id))
    return result.scalar_one_or_none()


async def semantic_search(session: AsyncSession, query_text: str, limit: int = 10) -> list[tuple[Article, float]]:
    query_vec = embed_single(query_text)
    stmt = (
        select(Article, Article.embedding.cosine_distance(query_vec.tolist()).label("distance"))
        .where(Article.embedding.is_not(None))
        .order_by("distance")
        .limit(limit)
    )
    result = await session.execute(stmt)
    rows = result.all()
    return [(row[0], 1.0 - row[1]) for row in rows]


async def recommend_by_topic(session: AsyncSession, topic: str, limit: int = 10) -> list[tuple[Article, float]]:
    return await semantic_search(session, topic, limit)


async def recommend_similar(session: AsyncSession, article_id: int, limit: int = 10) -> list[tuple[Article, float]]:
    article = await get_article_by_id(session, article_id)
    if article is None or article.embedding is None:
        return []
    stmt = (
        select(Article, Article.embedding.cosine_distance(article.embedding).label("distance"))
        .where(Article.embedding.is_not(None), Article.id != article_id)
        .order_by("distance")
        .limit(limit)
    )
    result = await session.execute(stmt)
    rows = result.all()
    return [(row[0], 1.0 - row[1]) for row in rows]


async def recommend_stories_by_topic(
    session: AsyncSession,
    topic: str,
    limit: int = 10,
    candidate_limit: int = 200,
) -> list[tuple[RankedStory, float]]:
    candidates = await semantic_search(session, topic, candidate_limit)
    candidate_articles = [article for article, _score in candidates]
    return await _rank_story_candidates(session, candidate_articles, limit)


async def recommend_stories_similar(
    session: AsyncSession,
    article_id: int,
    limit: int = 10,
    candidate_limit: int = 200,
) -> list[tuple[RankedStory, float]]:
    source_article = await get_article_by_id(session, article_id)
    if source_article is None or source_article.embedding is None:
        return []

    candidates = await recommend_similar(session, article_id, candidate_limit)
    candidate_articles = [article for article, _score in candidates]
    return await _rank_story_candidates(
        session,
        candidate_articles,
        limit,
        exclude_story_key=_story_key(source_article),
    )


async def get_personalized_feed(session: AsyncSession, user_id: str, limit: int = 20) -> list[tuple[Article, float]]:
    result = await session.execute(select(UserPreference).where(UserPreference.user_id == user_id))
    preferences = list(result.scalars().all())
    if not preferences:
        return []

    scored: dict[int, tuple[Article, float]] = {}
    for pref in preferences:
        results = await semantic_search(session, pref.topic, limit=limit)
        for article, score in results:
            weighted = score * pref.weight
            if article.id not in scored or scored[article.id][1] < weighted:
                scored[article.id] = (article, weighted)

    ranked = sorted(scored.values(), key=lambda x: x[1], reverse=True)
    return ranked[:limit]


async def get_personalized_story_feed(
    session: AsyncSession,
    user_id: str,
    limit: int = 20,
    candidate_limit_per_topic: int = 100,
) -> list[tuple[RankedStory, float]]:
    result = await session.execute(select(UserPreference).where(UserPreference.user_id == user_id))
    preferences = list(result.scalars().all())
    if not preferences:
        return []

    candidate_articles_by_id: dict[int, Article] = {}
    for pref in preferences:
        candidates = await semantic_search(session, pref.topic, candidate_limit_per_topic)
        for article, _score in candidates:
            if article.id not in candidate_articles_by_id:
                candidate_articles_by_id[article.id] = article

    return await _rank_story_candidates(
        session,
        list(candidate_articles_by_id.values()),
        limit,
    )


async def set_user_preferences(
    session: AsyncSession, user_id: str, preferences: list[tuple[str, float]]
) -> list[UserPreference]:
    # Ensure user exists
    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        user = User(id=user_id)
        session.add(user)

    # Delete existing preferences
    existing = (await session.execute(select(UserPreference).where(UserPreference.user_id == user_id))).scalars().all()
    for p in existing:
        await session.delete(p)

    # Insert new preferences
    new_prefs = []
    for topic, weight in preferences:
        pref = UserPreference(user_id=user_id, topic=topic, weight=weight)
        session.add(pref)
        new_prefs.append(pref)

    await session.commit()
    return new_prefs


async def get_user_preferences(session: AsyncSession, user_id: str) -> list[UserPreference]:
    result = await session.execute(select(UserPreference).where(UserPreference.user_id == user_id))
    return list(result.scalars().all())


async def record_article_view(session: AsyncSession, article_id: int, session_id: str) -> None:
    view = ArticleView(article_id=article_id, session_id=session_id)
    session.add(view)
    await session.commit()


async def get_view_counts(session: AsyncSession) -> dict[int, int]:
    result = await session.execute(
        select(ArticleView.article_id, func.count(ArticleView.id)).group_by(ArticleView.article_id)
    )
    return dict(result.all())


async def get_ranked_articles(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    publisher: str | None = None,
    language: str | None = None,
    topic: str | None = None,
    category: str | None = None,
    candidate_limit: int = 200,
) -> tuple[list[Article], int]:
    query = select(Article).options(defer(Article.body), defer(Article.embedding)).where(Article.embedding.is_not(None))
    count_query = select(func.count(Article.id)).where(Article.embedding.is_not(None))

    if publisher:
        query = query.where(Article.publisher == publisher)
        count_query = count_query.where(Article.publisher == publisher)
    if language:
        query = query.where(Article.language == language)
        count_query = count_query.where(Article.language == language)
    if topic:
        query = query.where(Article.topics.any(topic))
        count_query = count_query.where(Article.topics.any(topic))
    if category:
        query = query.where(Article.category == category)
        count_query = count_query.where(Article.category == category)

    total = (await session.execute(count_query)).scalar_one()

    # Fetch only the most recent candidates — freshness-weighted ranking makes
    # older articles score near-zero anyway (48h half-life), so loading all rows
    # wastes bandwidth, especially with a remote database.
    query = query.order_by(Article.publishing_date.desc().nulls_last()).limit(candidate_limit)
    result = await session.execute(query)
    articles = list(result.scalars().all())

    if not articles:
        return [], total

    view_counts = await get_view_counts(session)

    dates = [a.publishing_date for a in articles]
    views = [view_counts.get(a.id, 0) for a in articles]
    cluster_ids = [a.dedup_cluster_id for a in articles]

    # Compute cluster sizes: how many articles share each dedup_cluster_id
    cluster_size_map: dict[int, int] = {}
    for cid in cluster_ids:
        if cid is not None:
            cluster_size_map[cid] = cluster_size_map.get(cid, 0) + 1
    cluster_sizes = [cluster_size_map.get(cid, 1) if cid is not None else 1 for cid in cluster_ids]

    authorities = [authority_score(a.publisher) for a in articles]

    weights = RankingWeights(
        freshness=settings.ranking_freshness_weight,
        prominence=settings.ranking_prominence_weight,
        authority=settings.ranking_authority_weight,
        engagement=settings.ranking_engagement_weight,
        diversity_lambda=settings.ranking_diversity_lambda,
        half_life_hours=settings.ranking_recency_half_life_hours,
    )

    scores = composite_scores(dates, views, weights, cluster_sizes, authorities)

    # Score-based ranking (avoids loading embeddings over the network for MMR)
    offset = (page - 1) * page_size
    ranked_indices = np.argsort(-scores).tolist()
    page_indices = ranked_indices[offset : offset + page_size]

    ranked_articles = [articles[i] for i in page_indices]
    return ranked_articles, total


async def _fetch_top_cluster_articles(
    session: AsyncSession,
    min_cluster_size: int = 3,
    max_cluster_size: int = 200,
    cluster_limit: int = 50,
    publisher: str | None = None,
    language: str | None = None,
    category: str | None = None,
) -> list[Article]:
    """Fetch one representative article per large cluster so big stories
    always appear in the candidate set regardless of recency.

    Clusters larger than *max_cluster_size* are excluded — they are
    almost certainly runaway transitive-chain artefacts, not real stories.
    """
    size_query = (
        select(
            Article.dedup_cluster_id,
            func.count(Article.id).label("cluster_size"),
        )
        .where(Article.embedding.is_not(None), Article.dedup_cluster_id.is_not(None))
    )
    if publisher:
        size_query = size_query.where(Article.publisher == publisher)
    if language:
        size_query = size_query.where(Article.language == language)
    if category:
        size_query = size_query.where(Article.category == category)

    size_query = (
        size_query
        .group_by(Article.dedup_cluster_id)
        .having(
            func.count(Article.id) >= min_cluster_size,
            func.count(Article.id) <= max_cluster_size,
        )
        .order_by(func.count(Article.id).desc())
        .limit(cluster_limit)
    )
    cluster_rows = await session.execute(size_query)
    top_cluster_ids = [row[0] for row in cluster_rows.all()]

    if not top_cluster_ids:
        return []

    # Fetch one article per cluster (the most recent) as a representative
    from sqlalchemy import distinct
    repr_query = (
        select(Article)
        .options(defer(Article.body), defer(Article.embedding))
        .where(Article.dedup_cluster_id.in_(top_cluster_ids))
        .distinct(Article.dedup_cluster_id)
        .order_by(Article.dedup_cluster_id, Article.publishing_date.desc().nulls_last())
    )
    result = await session.execute(repr_query)
    return list(result.scalars().all())


async def get_ranked_stories(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 15,
    publisher: str | None = None,
    language: str | None = None,
    topic: str | None = None,
    category: str | None = None,
    candidate_limit: int = 500,
) -> tuple[list[RankedStory], int]:
    base_filter = select(Article).options(defer(Article.body), defer(Article.embedding)).where(Article.embedding.is_not(None))

    if publisher:
        base_filter = base_filter.where(Article.publisher == publisher)
    if language:
        base_filter = base_filter.where(Article.language == language)
    if topic:
        base_filter = base_filter.where(Article.topics.any(topic))
    if category:
        base_filter = base_filter.where(Article.category == category)

    # Pass 1: most recent articles (standalone + small clusters)
    recency_query = base_filter.order_by(Article.publishing_date.desc().nulls_last()).limit(candidate_limit)
    result = await session.execute(recency_query)
    articles = list(result.scalars().all())

    # Pass 2: ensure large clusters are represented even if not recent
    cluster_reps = await _fetch_top_cluster_articles(
        session, min_cluster_size=3, cluster_limit=50,
        publisher=publisher, language=language, category=category,
    )
    articles.extend(cluster_reps)

    if not articles:
        return [], 0

    articles = _dedupe_articles_by_id(articles)
    view_counts = await get_view_counts(session)
    scores = _compute_popularity_scores(articles, view_counts)
    popularity_score_by_article_id = {
        article.id: float(scores[idx]) for idx, article in enumerate(articles)
    }
    ordered_story_keys, lead_by_story_key, _final_score_by_story_key = await _build_tier_anchored_story_ranking(
        session,
        articles,
        popularity_score_by_article_id,
    )

    # When a category filter is active, drop stories whose lead article
    # doesn't match — cluster expansion can pull in cross-category leads.
    if category:
        ordered_story_keys = [
            sk for sk in ordered_story_keys
            if getattr(lead_by_story_key[sk], "category", None) == category
        ]

    total_stories = len(ordered_story_keys)
    offset = (page - 1) * page_size
    page_story_keys = ordered_story_keys[offset : offset + page_size]

    if not page_story_keys:
        return [], total_stories

    stories = await _expand_ranked_stories(session, lead_by_story_key, page_story_keys)
    return stories, total_stories
