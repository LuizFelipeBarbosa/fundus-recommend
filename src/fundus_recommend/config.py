from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://fundus:fundus@localhost:5432/fundus_recommend"
    database_url_sync: str = "postgresql+psycopg2://fundus:fundus@localhost:5432/fundus_recommend"
    cors_allow_origins: str = ""
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384
    dedup_threshold: float = 0.50
    ranking_freshness_weight: float = 0.4
    ranking_prominence_weight: float = 0.35
    ranking_authority_weight: float = 0.2
    ranking_engagement_weight: float = 0.05
    ranking_diversity_lambda: float = 0.3
    ranking_recency_half_life_hours: float = 48.0

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
