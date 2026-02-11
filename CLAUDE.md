# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Development Commands

```bash
# Install (editable, for development)
pip install -e .

# Run API server locally
uvicorn fundus_recommend.main:app --reload --port 8000

# Run all tests
pytest tests/

# Run a single test file
pytest tests/test_dedup.py

# Run a single test method
pytest tests/test_dedup.py::DedupeTests::test_no_new_articles -v

# Database (dev postgres via docker-compose)
docker-compose up postgres
alembic upgrade head

# Production stack
docker-compose -f docker-compose.prod.yml up
```

## Architecture Overview

**fundus-recommend** is a news recommendation engine. It crawls articles from 60+ countries, embeds them as vectors, deduplicates into story clusters, ranks them, and serves them via a FastAPI API consumed by a Next.js frontend.

### Pipeline (fr-schedule)

The main production loop runs `fr-schedule --interval 10` and executes these stages in order:

1. **Crawl** — Fetch articles via pluggable adapters (Fundus, RSS, Official API, Licensed Feed)
2. **Translate** — Non-English titles → English via Google Translate
3. **Embed** — Encode with sentence-transformers (`all-MiniLM-L6-v2`, 384-dim vectors stored in pgvector)
4. **Categorize** — Assign one of 7 categories using exemplar-based cosine similarity
5. **Dedup** — Connected-components clustering (cosine similarity ≥ 0.70) to group articles about the same story
6. **Refresh** — Update stale embeddings and engagement metrics

### Key Modules

| Path | Purpose |
|------|---------|
| `src/fundus_recommend/main.py` | FastAPI app entry point |
| `src/fundus_recommend/config.py` | Pydantic Settings (all tunable params, loaded from `.env`) |
| `src/fundus_recommend/cli/schedule.py` | Main scheduler loop orchestrating the full pipeline |
| `src/fundus_recommend/ingest/` | Crawl pipeline: registry of publishers, adapters, rate limiting, circuit breaker |
| `src/fundus_recommend/ingest/registry.py` | Publisher configs — Fundus country codes + named publishers |
| `src/fundus_recommend/services/ranking.py` | Composite scoring: freshness (0.4) + prominence (0.35) + authority (0.2) + engagement (0.05), with MMR diversity reranking |
| `src/fundus_recommend/services/dedup.py` | Incremental connected-components dedup (new × all matrix, not all × all) |
| `src/fundus_recommend/services/categorizer.py` | 7-category classifier using exemplar prototype embeddings |
| `src/fundus_recommend/db/queries.py` | All database queries (async for API, sync for CLI); story construction with tier-anchored leads |
| `src/fundus_recommend/models/db.py` | SQLAlchemy 2.0 ORM models (Article, User, etc.) with pgvector |
| `frontend/` | Next.js 14 app (independent, connects to API at port 8000) |

### Dual Database Engines

The codebase maintains two SQLAlchemy engines:
- **Async** (`asyncpg`) — used by FastAPI routes
- **Sync** (`psycopg2`) — used by CLI commands and the crawl pipeline

Both are configured via `DATABASE_URL` / `DATABASE_URL_SYNC` environment variables.

### Ingest Adapter System

Adapters in `ingest/adapters/` implement a common interface. The registry in `ingest/registry.py` maps publisher IDs to `PublisherConfig` dataclasses specifying which adapter, feed URLs, API keys, etc. New publishers are added by creating a config entry, not by writing new adapter code.

### Ranking & Stories

Articles are ranked with a weighted composite score and then reranked using Maximal Marginal Relevance (MMR) for diversity. Dedup clusters form "stories" — the API picks a tier-1 publisher (Reuters, AP, etc.) as the lead article when available.

## Conventions

- **CLI commands** use Click and are registered as `fr-*` entry points in `pyproject.toml`
- **Tests** use `unittest.TestCase` with `unittest.mock`; run via pytest
- **Internal types** use `@dataclass(slots=True)` (e.g., `PublisherConfig`, `CrawlArticleCandidate`)
- **API schemas** use Pydantic v2 `BaseModel`
- **Vector math** uses numpy directly (cosine similarity via normalized dot products)
- **Migrations** managed by Alembic in `alembic/`
