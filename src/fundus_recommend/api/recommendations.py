from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from fundus_recommend.db.queries import (
    RankedStory,
    get_personalized_feed,
    get_personalized_story_feed,
    recommend_by_topic,
    recommend_similar,
    recommend_stories_by_topic,
    recommend_stories_similar,
)
from fundus_recommend.db.session import get_async_session
from fundus_recommend.models.schemas import (
    ArticleSummary,
    NewsStory,
    RecommendationResponse,
    SearchResult,
    StoryRecommendationResponse,
    StoryRecommendationResult,
)

router = APIRouter(tags=["recommendations"])


def _to_news_story(story: RankedStory) -> NewsStory:
    return NewsStory(
        story_id=story.story_id,
        dedup_cluster_id=story.dedup_cluster_id,
        source_count=len(story.articles),
        lead_article=ArticleSummary.model_validate(story.lead_article),
        articles=[ArticleSummary.model_validate(article) for article in story.articles],
    )


@router.get("/recommendations", response_model=RecommendationResponse)
async def get_recommendations(
    topic: str | None = Query(None, description="Topic to get recommendations for"),
    similar_to: int | None = Query(None, description="Article ID to find similar articles"),
    limit: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    if similar_to is not None:
        results = await recommend_similar(session, similar_to, limit)
        strategy = f"similar_to:{similar_to}"
    elif topic is not None:
        results = await recommend_by_topic(session, topic, limit)
        strategy = f"topic:{topic}"
    else:
        # Default: recent articles with embeddings
        results = await recommend_by_topic(session, "latest news", limit)
        strategy = "recent"

    return RecommendationResponse(
        strategy=strategy,
        results=[
            SearchResult(article=ArticleSummary.model_validate(article), score=round(score, 4))
            for article, score in results
        ],
    )


@router.get("/story-recommendations", response_model=StoryRecommendationResponse)
async def get_story_recommendations(
    topic: str | None = Query(None, description="Topic to get story recommendations for"),
    similar_to: int | None = Query(None, description="Article ID to find related stories"),
    limit: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    if similar_to is not None:
        results = await recommend_stories_similar(session, similar_to, limit)
        strategy = f"similar_to:{similar_to}"
    elif topic is not None:
        results = await recommend_stories_by_topic(session, topic, limit)
        strategy = f"topic:{topic}"
    else:
        results = await recommend_stories_by_topic(session, "latest news", limit)
        strategy = "recent"

    return StoryRecommendationResponse(
        strategy=strategy,
        results=[
            StoryRecommendationResult(story=_to_news_story(story), score=round(score, 4))
            for story, score in results
        ],
    )


@router.get("/feed/{user_id}", response_model=RecommendationResponse)
async def get_feed(
    user_id: str,
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    results = await get_personalized_feed(session, user_id, limit)
    return RecommendationResponse(
        strategy=f"personalized:{user_id}",
        results=[
            SearchResult(article=ArticleSummary.model_validate(article), score=round(score, 4))
            for article, score in results
        ],
    )


@router.get("/story-feed/{user_id}", response_model=StoryRecommendationResponse)
async def get_story_feed(
    user_id: str,
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    results = await get_personalized_story_feed(session, user_id, limit)
    return StoryRecommendationResponse(
        strategy=f"personalized:{user_id}",
        results=[
            StoryRecommendationResult(story=_to_news_story(story), score=round(score, 4))
            for story, score in results
        ],
    )
