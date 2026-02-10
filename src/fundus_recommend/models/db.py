from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ARRAY,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from fundus_recommend.config import settings


class Base(DeclarativeBase):
    pass


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    authors: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    topics: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    publisher: Mapped[str] = mapped_column(String(255), nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=True)
    publishing_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    crawled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    cover_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding = mapped_column(Vector(settings.embedding_dim), nullable=True)
    embedded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dedup_cluster_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)

    __table_args__ = (
        Index("ix_articles_topics", "topics", postgresql_using="gin"),
        Index("ix_articles_publishing_date", "publishing_date"),
        Index("ix_articles_publisher", "publisher"),
        Index("ix_articles_language", "language"),
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    preferences: Mapped[list["UserPreference"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    user: Mapped["User"] = relationship(back_populates="preferences")

    __table_args__ = (UniqueConstraint("user_id", "topic", name="uq_user_topic"),)


class ArticleView(Base):
    __tablename__ = "article_views"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    article_id: Mapped[int] = mapped_column(Integer, ForeignKey("articles.id", ondelete="CASCADE"), nullable=False)
    session_id: Mapped[str] = mapped_column(String(36), nullable=False)
    viewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_article_views_article_id", "article_id"),
        Index("ix_article_views_viewed_at", "viewed_at"),
    )


class CrawlRun(Base):
    __tablename__ = "crawl_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_label: Mapped[str] = mapped_column(String(64), nullable=False, default="crawl")
    requested_publishers: Mapped[list[str]] = mapped_column(ARRAY(String(255)), default=list)
    resolved_publishers: Mapped[list[str]] = mapped_column(ARRAY(String(255)), default=list)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    total_publishers: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    succeeded_publishers: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_publishers: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_publishers: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_inserted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    publishers: Mapped[list["CrawlRunPublisher"]] = relationship(
        back_populates="crawl_run",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_crawl_runs_started_at", "started_at"),
        Index("ix_crawl_runs_status", "status"),
    )


class CrawlRunPublisher(Base):
    __tablename__ = "crawl_run_publishers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    crawl_run_id: Mapped[int] = mapped_column(Integer, ForeignKey("crawl_runs.id", ondelete="CASCADE"), nullable=False)
    publisher_id: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    adapter: Mapped[str] = mapped_column(String(50), nullable=False)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)
    inserted_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    crawled_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status_histogram: Mapped[dict[str, int]] = mapped_column(JSONB, nullable=False, default=dict)
    skip_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    crawl_run: Mapped["CrawlRun"] = relationship(back_populates="publishers")

    __table_args__ = (
        Index("ix_crawl_run_publishers_run_id", "crawl_run_id"),
        Index("ix_crawl_run_publishers_publisher_id", "publisher_id"),
        Index("ix_crawl_run_publishers_started_at", "started_at"),
    )
