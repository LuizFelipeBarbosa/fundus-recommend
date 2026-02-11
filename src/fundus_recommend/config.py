from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://fundus:fundus@localhost:5432/fundus_recommend"
    database_url_sync: str = "postgresql+psycopg2://fundus:fundus@localhost:5432/fundus_recommend"
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384
    dedup_threshold: float = 0.70
    ranking_freshness_weight: float = 0.4
    ranking_prominence_weight: float = 0.35
    ranking_authority_weight: float = 0.2
    ranking_engagement_weight: float = 0.05
    ranking_diversity_lambda: float = 0.3
    ranking_recency_half_life_hours: float = 48.0
    top_story_min_sources: int = 3  # unused, kept for .env compatibility
    top_story_score_popularity_weight: float = 0.45
    top_story_score_coverage_weight: float = 0.35
    top_story_score_reputation_weight: float = 0.20
    category_semantic_min_score: float = 0.12
    category_semantic_min_margin: float = 0.02
    cors_origins: str = "http://localhost:3000"
    crawl_timeout_seconds: int = 20
    crawl_max_retries: int = 2
    crawl_backoff_seconds: float = 1.0
    crawl_rate_limit_per_minute: int = 30
    crawl_circuit_breaker_threshold: int = 5
    crawl_circuit_breaker_cooldown_seconds: int = 900

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
