from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from fundus_recommend.db.queries import semantic_search
from fundus_recommend.db.session import get_async_session
from fundus_recommend.models.schemas import ArticleSummary, SearchResponse, SearchResult

router = APIRouter(tags=["search"])


@router.get("/search", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    results = await semantic_search(session, q, limit)
    return SearchResponse(
        query=q,
        results=[
            SearchResult(article=ArticleSummary.model_validate(article), score=round(score, 4))
            for article, score in results
        ],
    )
