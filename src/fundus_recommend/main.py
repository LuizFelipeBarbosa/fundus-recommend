from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from fundus_recommend.api import articles, preferences, recommendations, search
from fundus_recommend.config import settings
from fundus_recommend.db.queries import get_article_count, get_embedded_count
from fundus_recommend.db.session import get_async_session
from fundus_recommend.models.schemas import HealthResponse

app = FastAPI(title="Fundus Recommend", version="0.1.0", description="News recommendation engine powered by Fundus")


def _get_cors_origins() -> list[str]:
    return [origin.strip() for origin in settings.cors_allow_origins.split(",") if origin.strip()]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_cors_origins(),
    allow_origin_regex=r"^http://localhost:\d+$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(articles.router)
app.include_router(search.router)
app.include_router(recommendations.router)
app.include_router(preferences.router)


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health(session: AsyncSession = Depends(get_async_session)):
    return HealthResponse(
        status="ok",
        article_count=await get_article_count(session),
        embedded_count=await get_embedded_count(session),
    )
