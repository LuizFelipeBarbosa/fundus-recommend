import numpy as np
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from fundus_recommend.config import settings
from fundus_recommend.models.db import Article, ArticleView, User, UserPreference
from fundus_recommend.services.embeddings import embed_single
from fundus_recommend.services.ranking import RankingWeights, composite_scores, mmr_rerank


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
    query = select(Article)
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
) -> tuple[list[Article], int]:
    query = select(Article).where(Article.embedding.is_not(None))
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
    result = await session.execute(query)
    articles = list(result.scalars().all())

    if not articles:
        return [], total

    view_counts = await get_view_counts(session)

    dates = [a.publishing_date for a in articles]
    views = [view_counts.get(a.id, 0) for a in articles]
    embeddings = np.array([a.embedding for a in articles])
    cluster_ids = [a.dedup_cluster_id for a in articles]

    # Compute cluster sizes: how many articles share each dedup_cluster_id
    cluster_size_map: dict[int, int] = {}
    for cid in cluster_ids:
        if cid is not None:
            cluster_size_map[cid] = cluster_size_map.get(cid, 0) + 1
    cluster_sizes = [cluster_size_map.get(cid, 1) if cid is not None else 1 for cid in cluster_ids]

    weights = RankingWeights(
        recency=settings.ranking_recency_weight,
        engagement=settings.ranking_engagement_weight,
        source_count=settings.ranking_source_count_weight,
        diversity_lambda=settings.ranking_diversity_lambda,
        half_life_hours=settings.ranking_recency_half_life_hours,
    )

    scores = composite_scores(dates, views, weights, cluster_sizes)
    offset = (page - 1) * page_size
    ranked_indices = mmr_rerank(scores, embeddings, page_size, offset, weights.diversity_lambda, cluster_ids)

    ranked_articles = [articles[i] for i in ranked_indices]
    return ranked_articles, total
