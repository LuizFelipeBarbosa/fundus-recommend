from datetime import datetime

from pydantic import BaseModel


class ArticleSummary(BaseModel):
    id: int
    url: str
    title: str
    title_en: str | None
    authors: list[str]
    topics: list[str]
    publisher: str
    language: str | None
    publishing_date: datetime | None
    cover_image_url: str | None
    dedup_cluster_id: int | None
    category: str | None

    model_config = {"from_attributes": True}


class ArticleDetail(ArticleSummary):
    body: str

    model_config = {"from_attributes": True}


class ArticleListResponse(BaseModel):
    items: list[ArticleSummary]
    total: int
    page: int
    page_size: int


class SearchResult(BaseModel):
    article: ArticleSummary
    score: float


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]


class RecommendationResponse(BaseModel):
    strategy: str
    results: list[SearchResult]


class TopicPreference(BaseModel):
    topic: str
    weight: float = 1.0


class PreferencesRequest(BaseModel):
    user_id: str
    preferences: list[TopicPreference]


class PreferencesResponse(BaseModel):
    user_id: str
    preferences: list[TopicPreference]


class HealthResponse(BaseModel):
    status: str
    article_count: int
    embedded_count: int
