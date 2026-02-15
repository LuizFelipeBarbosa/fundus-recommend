# Fundus Recommend

Fundus Recommend is a news recommendation engine powered by [Fundus](https://github.com/flairNLP/fundus), FastAPI, PostgreSQL/pgvector, and Next.js.

It crawls multi-source news, translates non-English titles, builds semantic embeddings, clusters duplicate coverage, assigns categories, and serves ranked story feeds through a web API and frontend.

For full implementation details, see [`ARCHITECTURE.md`](ARCHITECTURE.md).

## System Overview

- Scheduler pipeline (`fr-schedule`): crawl -> translate -> embed -> categorize -> dedup -> refresh stale embeddings
- Data store: PostgreSQL 16 + `pgvector`
- API: FastAPI on port `8000`
- Frontend: Next.js on port `3000`

## Tech Stack

- Backend: Python 3.10+, FastAPI, SQLAlchemy, Alembic, sentence-transformers
- Database: PostgreSQL 16 + pgvector
- Frontend: Next.js 14, React 18, Tailwind CSS
- Ingestion: Fundus + adapter-based publisher registry (`rss`, `official_api`, `licensed_feed`, `fundus`)

## Repository Layout

```text
fundus-recommend/
├── ARCHITECTURE.md
├── docker-compose.yml              # dev DB only
├── docker-compose.prod.yml         # postgres + api + scheduler + frontend
├── src/fundus_recommend/
│   ├── main.py                     # FastAPI app
│   ├── config.py                   # settings from env
│   ├── api/                        # route handlers
│   ├── cli/                        # fr-* commands
│   ├── services/                   # ranking, embeddings, dedup, translation, categorizer
│   ├── ingest/                     # adapters + crawl pipeline
│   └── models/                     # ORM + response schemas
├── alembic/
├── frontend/
└── docs/operations.md
```

## Prerequisites

- Docker + Docker Compose (for containerized setup)
- Python 3.10+ (3.12 recommended)
- Node.js 20+ and npm (for local frontend dev)

## Quick Start

### Option A: Full stack with Docker Compose

```bash
cp .env.example .env
docker compose -f docker-compose.prod.yml up --build
```

Services:
- Frontend: [http://localhost:3000](http://localhost:3000)
- API docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health: [http://localhost:8000/health](http://localhost:8000/health)

### Option B: Local development (API + scheduler + frontend)

1. Start PostgreSQL:

```bash
docker compose up -d postgres
```

2. Set up backend:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
alembic upgrade head
uvicorn fundus_recommend.main:app --reload --host 0.0.0.0 --port 8000
```

3. In another terminal, run scheduler (example subset of publishers):

```bash
source .venv/bin/activate
fr-schedule --publishers cnn,npr,propublica --interval 10
```

4. Run frontend:

```bash
cd frontend
npm install
npm run dev
```

The frontend defaults to `http://localhost:8000` for API calls (`NEXT_PUBLIC_API_URL`).

## Ingestion Model (Adapter-Based)

The scheduler and crawl CLI now resolve explicit publisher IDs via registry adapters.

Supported adapters:
- `rss`
- `official_api`
- `licensed_feed`
- `fundus`

Examples:

```bash
# one-shot crawl
fr-crawl --publishers cnn,npr,propublica --max-articles 25

# run one scheduler cycle
fr-schedule --publishers cnn,npr,propublica,the-atlantic --run-once

# legacy compatibility (deprecated warning expected)
fr-crawl --publishers us --max-articles 25
```

Some publishers require credentials (for example `nyt`, `reuters`, `wsj`, `bloomberg`, `politico`, `axios`) via environment variables.

## Pipeline Stages

Per cycle:
1. Crawl publishers and insert new articles
2. Translate non-English titles to English
3. Generate embeddings for new articles
4. Assign semantic category labels
5. Deduplicate near-duplicate coverage into clusters
6. Refresh stale embeddings

## API Endpoints

Core endpoints:

- `GET /articles`
- `GET /stories`
- `GET /articles/latest-timestamp`
- `GET /articles/{article_id}`
- `POST /articles/{article_id}/view`
- `GET /search`
- `GET /recommendations`
- `GET /story-recommendations`
- `GET /feed/{user_id}`
- `GET /story-feed/{user_id}`
- `POST /preferences`
- `GET /health`

Interactive schema: [http://localhost:8000/docs](http://localhost:8000/docs)

## CLI Commands

Defined in `pyproject.toml`:

- `fr-schedule`: scheduled crawl + enrichment loop
- `fr-crawl`: one-shot crawl
- `fr-embed`: embed unembedded articles (`--with-dedup` available)
- `fr-classify`: re-run semantic categorization
- `fr-fix-dates`: fix ambiguous publish dates (targeted publishers)

## Key Environment Variables

From `.env.example` / `src/fundus_recommend/config.py`:

- `DATABASE_URL`
- `DATABASE_URL_SYNC`
- `EMBEDDING_MODEL`
- `EMBEDDING_DIM`
- `DEDUP_THRESHOLD`
- `CORS_ORIGINS`
- `CRAWL_TIMEOUT_SECONDS`
- `CRAWL_MAX_RETRIES`
- `CRAWL_BACKOFF_SECONDS`
- `CRAWL_RATE_LIMIT_PER_MINUTE`
- `CRAWL_CIRCUIT_BREAKER_THRESHOLD`
- `CRAWL_CIRCUIT_BREAKER_COOLDOWN_SECONDS`
- `NEXT_PUBLIC_API_URL` (frontend build/runtime)

## Testing

```bash
pytest
```

## Operations Notes

After deploying dedup changes, run a one-time full dedup pass:

```bash
fr-embed --with-dedup
```

See [`docs/operations.md`](docs/operations.md) for runbook details.

## Deployment Notes

- `docker-compose.prod.yml`: production-like local stack
- `railway.toml`: default Railway config for Dockerfile builds

### Railway (Neon + API + Frontend + Scheduler)

Deploy as three Railway services in one project (all from this repo):

1. `api`
2. `frontend`
3. `scheduler`

Recommended service-level variables:

| Service | Variable | Value |
|---|---|---|
| `api` | `RAILWAY_DOCKERFILE_PATH` | `Dockerfile` |
| `api` | `PORT` | `8000` |
| `api` | `DATABASE_URL` | Neon async URL (`postgresql+asyncpg://...`) |
| `api` | `DATABASE_URL_SYNC` | Neon sync URL (`postgresql+psycopg2://...`) |
| `api` | `CORS_ORIGINS` | `https://<frontend-domain>` |
| `frontend` | `RAILWAY_DOCKERFILE_PATH` | `Dockerfile.frontend` |
| `frontend` | `NEXT_PUBLIC_API_URL` | `https://<api-domain>` |
| `scheduler` | `RAILWAY_DOCKERFILE_PATH` | `Dockerfile.scheduler` |
| `scheduler` | `DATABASE_URL` | Neon async URL |
| `scheduler` | `DATABASE_URL_SYNC` | Neon sync URL |
| `scheduler` | `SCHEDULER_PUBLISHERS` | `all-countries` (expands to every Fundus country collection) |
| `scheduler` | `SCHEDULER_MAX_ARTICLES` | `25` |
| `scheduler` | `SCHEDULER_WORKERS` | `8` |
| `scheduler` | `SCHEDULER_BATCH_SIZE` | `64` |
| `scheduler` | `SCHEDULER_INTERVAL_MINUTES` | `5` |
| `scheduler` | `SCHEDULER_RUN_MODE` | `loop` (use Python built-in scheduler) |

Use the Python built-in scheduler loop (`fr-schedule --interval ...`) for continuous crawling.
If you need one-shot cron behavior, set `SCHEDULER_RUN_MODE=once`.

Set `SCHEDULER_WORKERS` to control parallel crawl workers.

Recommended watch paths:
- `api`: `/src`, `/alembic`, `/scripts`, `/pyproject.toml`, `/Dockerfile`
- `frontend`: `/frontend`, `/Dockerfile.frontend`
- `scheduler`: `/src`, `/alembic`, `/scripts`, `/pyproject.toml`, `/Dockerfile.scheduler`

Files used for this setup:
- `Dockerfile` (API)
- `Dockerfile.frontend` (Frontend, repo-root build context)
- `Dockerfile.scheduler` (Scheduler worker)
- `scripts/start-api.sh`
- `scripts/start-scheduler-once.sh`
