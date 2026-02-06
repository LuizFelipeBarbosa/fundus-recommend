from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://fundus:fundus@localhost:5432/fundus_recommend"
    database_url_sync: str = "postgresql+psycopg2://fundus:fundus@localhost:5432/fundus_recommend"
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384
    dedup_threshold: float = 0.50

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
