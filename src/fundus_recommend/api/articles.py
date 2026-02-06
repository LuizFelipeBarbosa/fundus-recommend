from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from fundus_recommend.db.queries import get_article_by_id, list_articles
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
    session: AsyncSession = Depends(get_async_session),
):
    articles, total = await list_articles(session, page, page_size, publisher, language, topic)
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
