from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from fundus_recommend.db.queries import get_article_by_id, get_ranked_articles, list_articles, record_article_view
from fundus_recommend.db.session import get_async_session
from fundus_recommend.models.schemas import ArticleDetail, ArticleListResponse, ArticleSummary

router = APIRouter(tags=["articles"])


@router.get("/articles", response_model=ArticleListResponse)
async def get_articles(
    page: int = 1,
    page_size: int = 20,
    publisher: str | None = None,
    language: str | None = None,
    topic: str | None = None,
    category: str | None = None,
    sort: Literal["recent", "ranked"] = "ranked",
    session: AsyncSession = Depends(get_async_session),
):
    if sort == "ranked":
        articles, total = await get_ranked_articles(session, page, page_size, publisher, language, topic, category)
    else:
        articles, total = await list_articles(session, page, page_size, publisher, language, topic, category)
    return ArticleListResponse(
        items=[ArticleSummary.model_validate(a) for a in articles],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/articles/{article_id}", response_model=ArticleDetail)
async def get_article(article_id: int, session: AsyncSession = Depends(get_async_session)):
    article = await get_article_by_id(session, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    return ArticleDetail.model_validate(article)


class ViewRequest(BaseModel):
    session_id: str


@router.post("/articles/{article_id}/view", status_code=204)
async def track_article_view(
    article_id: int,
    body: ViewRequest,
    session: AsyncSession = Depends(get_async_session),
):
    article = await get_article_by_id(session, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    await record_article_view(session, article_id, body.session_id)
