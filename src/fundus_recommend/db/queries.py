from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from fundus_recommend.models.db import Article, User, UserPreference
from fundus_recommend.services.embeddings import embed_single


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
