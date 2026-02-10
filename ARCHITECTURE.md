# Fundus Recommend — Architecture & Data Flow

A news recommendation engine powered by [Fundus](https://github.com/flairNLP/fundus). Crawls articles from 60+ countries, embeds them in a shared semantic space, and serves a ranked, deduplicated, categorized feed through a FastAPI backend and Next.js frontend.

---

## 1. System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          SCHEDULER (fr-schedule)                        │
│                          every 10 min cycle                             │
│                                                                         │
│   ┌──────────┐   ┌───────────┐   ┌──────────┐   ┌────────────┐        │
│   │  Crawl   │──▶│ Translate │──▶│  Embed   │──▶│ Categorize │        │
│   │ (Fundus) │   │ (Google)  │   │ (SBERT)  │   │(Prototypes)│        │
│   └──────────┘   └───────────┘   └──────────┘   └────────────┘        │
│        │                                               │                │
│        ▼                                               ▼                │
│   ┌──────────────────────────────────────────────────────────┐         │
│   │              PostgreSQL + pgvector                        │         │
│   │  articles | article_views | users | user_preferences     │         │
│   └──────────────────────────────────────────────────────────┘         │
│        ▲                         │                                      │
│   ┌────┘                         │                                      │
│   │ Dedup + Refresh              │                                      │
│   └──────────────────────────────┘                                      │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ SQL / pgvector cosine distance
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     FastAPI (port 8000)                                  │
│                                                                         │
│   /articles ──── ranked feed with filters                               │
│   /search ────── semantic similarity search                             │
│   /recommendations ── similar_to | topic | personalized                 │
│   /feed/{user_id} ─── preference-weighted semantic feed                 │
│   /preferences ── set user topic weights                                │
│   /health ────── article & embedding counts                             │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ JSON over HTTP
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      Next.js Frontend (port 3000)                       │
│                        branded as "Nexus"                               │
│                                                                         │
│   /  ──────────── ranked feed, filters, categories, 60s auto-refresh   │
│   /search ─────── semantic search results with scores                  │
│   /recommendations  topic-based discovery                              │
│   /articles/[id] ── full article + 6 related + view tracking           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Infrastructure & Deployment

### Docker Compose (Production)

`docker-compose.prod.yml` runs four services:

| Service       | Image / Build          | Port | Role                                      |
|---------------|------------------------|------|-------------------------------------------|
| **postgres**  | `pgvector/pgvector:pg16` | 5432 | Database with vector extension             |
| **api**       | `./Dockerfile`         | 8000 | FastAPI server (`scripts/start-api.sh`)    |
| **scheduler** | `./Dockerfile`         | —    | `fr-schedule --interval 10` loop           |
| **frontend**  | `./frontend/Dockerfile`| 3000 | Next.js 14 production build               |

### Docker Compose (Development)

`docker-compose.yml` runs only PostgreSQL. The API and scheduler are started manually.

### Environment Variables

| Variable             | Default                                          | Used By         |
|----------------------|--------------------------------------------------|-----------------|
| `DATABASE_URL`       | `postgresql+asyncpg://fundus:fundus@localhost:5432/fundus_recommend` | API (async)    |
| `DATABASE_URL_SYNC`  | `postgresql+psycopg2://fundus:fundus@localhost:5432/fundus_recommend` | Scheduler (sync) |
| `EMBEDDING_MODEL`    | `all-MiniLM-L6-v2`                              | Embeddings      |
| `EMBEDDING_DIM`      | `384`                                            | Vector column   |
| `DEDUP_THRESHOLD`    | `0.50`                                           | Dedup clustering|
| `CORS_ORIGINS`       | `http://localhost:3000`                          | API CORS        |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000`                          | Frontend (build-time) |

All settings are defined in `src/fundus_recommend/config.py` using Pydantic Settings and loaded from `.env`.

---

## 3. Database Schema

PostgreSQL 16 with the **pgvector** extension for vector similarity search.

### `articles` table

| Column              | Type                    | Notes                                   |
|---------------------|-------------------------|-----------------------------------------|
| `id`                | `INTEGER` PK            | Auto-increment                          |
| `url`               | `TEXT` UNIQUE NOT NULL   | Dedup key during crawl                  |
| `title`             | `TEXT` NOT NULL          | Original language title                 |
| `body`              | `TEXT` NOT NULL          | Full article text                       |
| `authors`           | `TEXT[]`                 | Array of author names                   |
| `topics`            | `TEXT[]`                 | Publisher-provided topic tags           |
| `publisher`         | `VARCHAR(255)` NOT NULL  | Publisher display name                  |
| `language`          | `VARCHAR(10)`            | ISO language code (e.g. `en`, `de`)     |
| `publishing_date`   | `TIMESTAMPTZ`            | Resolved from article or HTML           |
| `crawled_at`        | `TIMESTAMPTZ`            | `server_default=now()`                  |
| `cover_image_url`   | `TEXT`                   | First image URL from article            |
| `embedding`         | `VECTOR(384)`            | Sentence embedding (L2-normalized)      |
| `embedded_at`       | `TIMESTAMPTZ`            | When embedding was last computed        |
| `dedup_cluster_id`  | `INTEGER`                | Cluster ID (lowest article ID in group) |
| `title_en`          | `TEXT`                   | English translation of title            |
| `category`          | `VARCHAR(50)`            | Semantic category assignment            |

**Indexes:**
- `ix_articles_topics` — GIN index on `topics` array
- `ix_articles_publishing_date` — B-tree on `publishing_date`
- `ix_articles_publisher` — B-tree on `publisher`
- `ix_articles_language` — B-tree on `language`
- `ix_articles_category` — B-tree on `category`
- pgvector automatically indexes `embedding` for cosine distance queries

### `article_views` table

| Column       | Type              | Notes                              |
|-------------|-------------------|------------------------------------|
| `id`        | `INTEGER` PK      | Auto-increment                     |
| `article_id`| `INTEGER` FK      | References `articles.id` ON DELETE CASCADE |
| `session_id`| `VARCHAR(36)`     | Client-generated UUID              |
| `viewed_at` | `TIMESTAMPTZ`     | `server_default=now()`             |

**Indexes:** `ix_article_views_article_id`, `ix_article_views_viewed_at`

### `users` table

| Column       | Type              | Notes                   |
|-------------|-------------------|-------------------------|
| `id`        | `VARCHAR(36)` PK  | UUID                    |
| `created_at`| `TIMESTAMPTZ`     | `server_default=now()`  |

### `user_preferences` table

| Column    | Type              | Notes                                    |
|----------|-------------------|------------------------------------------|
| `id`     | `INTEGER` PK      | Auto-increment                           |
| `user_id`| `VARCHAR(36)` FK  | References `users.id` ON DELETE CASCADE  |
| `topic`  | `VARCHAR(255)`    | Free-text topic                          |
| `weight` | `FLOAT`           | Preference strength (default 1.0)        |

**Constraint:** `UNIQUE(user_id, topic)`

---

## 4. Backend Pipeline (Scheduler)

The scheduler (`fr-schedule`) runs a continuous loop. Each cycle processes all configured publisher collections sequentially, then performs global dedup and stale embedding refresh.

### Pipeline Steps

```
For each publisher (60+ country codes):
    ┌────────────┐     ┌─────────────┐     ┌────────────┐     ┌──────────────┐
    │  1. CRAWL  │────▶│ 2. TRANSLATE│────▶│  3. EMBED  │────▶│ 4. CATEGORIZE│
    └────────────┘     └─────────────┘     └────────────┘     └──────────────┘

After all publishers:
    ┌────────────────┐     ┌──────────────────┐
    │ 5. DEDUPLICATE │────▶│ 6. REFRESH STALE │
    └────────────────┘     └──────────────────┘

Sleep {interval} minutes, repeat.
```

#### Step 1 — Crawl

- Uses the **Fundus** library to crawl articles from publisher RSS feeds, sitemaps, and newsmaps
- Deduplicates by URL (skips if `article.url` already in DB)
- Extracts: title, body, authors, topics, publisher name, language, publishing date, cover image
- Publishing dates are resolved via `date_resolution.py` which handles publisher-specific date extraction and dd/mm vs mm/dd ambiguity
- Inserts each article into the `articles` table

**Source:** `cli/schedule.py:crawl_articles()`

#### Step 2 — Translate

- Selects newly inserted articles where `language != 'en'` and `title_en IS NULL`
- Translates each title to English via **Google Translate** (`deep-translator` library)
- Retry logic: 3 attempts with exponential backoff (2^attempt seconds)
- Rate limiting: 0.1s delay between requests
- Stores result in `title_en` column

**Source:** `cli/schedule.py:translate_new_articles()` → `services/translation.py`

#### Step 3 — Embed

- Selects articles where `embedding IS NULL`
- Constructs embedding input: `"{title_en or title}\n{body[:400]}"`
- Encodes in batches (default 64) using **SentenceTransformer** `all-MiniLM-L6-v2`
- Embeddings are **L2-normalized** (unit vectors) — 384 dimensions
- Updates `embedding` and `embedded_at` columns

**Source:** `cli/schedule.py:embed_new_articles()` → `services/embeddings.py`

#### Step 4 — Categorize

- Selects articles where `category IS NULL`
- Each of 7 categories has 5 exemplar headlines whose embeddings form a **prototype centroid**
- Computes cosine similarity between article embedding and each category prototype
- Assigns category if: `top_score >= 0.12` AND `(top_score - runner_up) >= 0.02`
- Otherwise assigns `"General"`

**Categories:** US, Global, Business, Technology, Arts, Sports, Entertainment (+ General fallback)

**Source:** `cli/schedule.py:categorize_new_articles()` → `services/categorizer.py`

#### Step 5 — Deduplicate

- Loads all articles with embeddings
- Computes NxN cosine similarity matrix (dot product of L2-normalized vectors)
- Greedy single-pass clustering: if `similarity >= 0.50`, assign both articles to the same cluster
- Cluster ID = lowest article ID in the cluster
- Updates `dedup_cluster_id` for all clustered articles

**Source:** `cli/schedule.py:run_dedup_pass()` → `services/dedup.py`

#### Step 6 — Refresh Stale Embeddings

- Re-embeds articles whose `embedded_at` is older than 7 days
- Ensures articles that received `title_en` after initial embedding get re-embedded with the English title
- Uses the same batched embedding process as Step 3

**Source:** `cli/schedule.py:refresh_stale_embeddings()`

---

## 5. API Endpoints

FastAPI application defined in `main.py`. All endpoints are async, using SQLAlchemy `AsyncSession`.

### Articles

| Method | Path                          | Parameters                                                                     | Response                | Description                          |
|--------|-------------------------------|--------------------------------------------------------------------------------|-------------------------|--------------------------------------|
| GET    | `/articles`                   | `page`, `page_size`, `publisher`, `language`, `topic`, `category`, `sort`       | `ArticleListResponse`  | Ranked or recent article listing      |
| GET    | `/articles/latest-timestamp`  | —                                                                              | `{latest_crawled_at}`   | Most recent crawl timestamp           |
| GET    | `/articles/{article_id}`      | `article_id` (path)                                                            | `ArticleDetail`         | Full article with body               |
| POST   | `/articles/{article_id}/view` | `article_id` (path), `{session_id}` (body)                                    | `204 No Content`        | Record a view event                  |

The `sort` parameter accepts `"ranked"` (default) or `"recent"`. Ranked applies the composite scoring algorithm.

### Search

| Method | Path      | Parameters                    | Response         | Description                    |
|--------|-----------|-------------------------------|------------------|--------------------------------|
| GET    | `/search` | `q` (required), `limit` (1–100, default 10) | `SearchResponse` | Semantic similarity search     |

### Recommendations

| Method | Path                | Parameters                                          | Response                   | Description                     |
|--------|---------------------|-----------------------------------------------------|----------------------------|---------------------------------|
| GET    | `/recommendations`  | `topic`, `similar_to` (article ID), `limit` (1–100) | `RecommendationResponse`   | Topic or similarity recs        |
| GET    | `/feed/{user_id}`   | `user_id` (path), `limit` (1–100, default 20)       | `RecommendationResponse`   | Personalized feed               |

Recommendation strategy is determined by parameter priority: `similar_to` > `topic` > default ("latest news").

### Preferences

| Method | Path           | Body                                                  | Response               | Description                   |
|--------|----------------|-------------------------------------------------------|------------------------|-------------------------------|
| POST   | `/preferences` | `{user_id, preferences: [{topic, weight}]}`           | `PreferencesResponse`  | Set user topic preferences    |

### Health

| Method | Path      | Response                                    | Description           |
|--------|-----------|---------------------------------------------|-----------------------|
| GET    | `/health` | `{status, article_count, embedded_count}`   | System health check   |

---

## 6. Ranking Algorithm

The home feed (`GET /articles?sort=ranked`) ranks articles using a composite score combining four signals.

### Composite Score Formula

```
score = 0.40 * freshness
      + 0.35 * prominence
      + 0.20 * authority
      + 0.05 * engagement
```

### Component Calculations

| Signal        | Weight | Formula                                              | Intuition                                           |
|---------------|--------|------------------------------------------------------|-----------------------------------------------------|
| **Freshness** | 40%    | `exp(-ln(2) / 48 * age_hours)`                       | Exponential decay, half-life = 48 hours             |
| **Prominence**| 35%    | `log(1 + cluster_size) / log(1 + max_cluster_size)`  | How many sources cover the same story               |
| **Authority** | 20%    | Publisher tier score (see below)                      | Editorial reputation of the source                  |
| **Engagement**| 5%     | `log(1 + views) / log(1 + max_views)`                | Reader interest signal                              |

### Publisher Authority Tiers

| Tier | Score | Examples                                                                                    |
|------|-------|---------------------------------------------------------------------------------------------|
| 1    | 1.0   | Associated Press, The Guardian, Le Monde, LA Times, Nature, Deutsche Welle, Tagesschau, FAZ |
| 2    | 0.7   | Business Insider, Fox News, TechCrunch, Wired, Spiegel, Bild, Die Welt, Stern, taz         |
| Default | 0.4 | All other / unknown publishers                                                              |

### Ranking Pipeline

1. Filter articles that have embeddings, apply optional filters (publisher, language, topic, category)
2. Load the 200 most recent candidates (`ORDER BY publishing_date DESC LIMIT 200`)
3. Fetch view counts from `article_views`
4. Compute cluster sizes from `dedup_cluster_id`
5. Look up publisher authority scores
6. Calculate composite score for each candidate
7. Sort by composite score descending
8. Paginate (default 20 per page)

### MMR Reranking (Available)

An MMR (Maximal Marginal Relevance) reranking function is implemented but not currently applied in the main feed:

```
mmr_score = λ * normalized_score - (1 - λ) * max_similarity_to_already_selected
```

- `λ = 0.3` — balances 30% relevance, 70% diversity
- Articles in the same dedup cluster have similarity set to 0.0 (different publishers covering the same story are not penalized)

**Source:** `services/ranking.py`

### Example Calculation

An article from The Guardian, 24 hours old, with 50 views (max 200), in a cluster of 3 (max 10):

```
freshness  = exp(-0.0144 * 24)              = 0.707
prominence = log(4) / log(11)               = 0.579
authority  = 1.0 (Tier 1)
engagement = log(51) / log(201)             = 0.742

score = 0.40 * 0.707 + 0.35 * 0.579 + 0.20 * 1.0 + 0.05 * 0.742
      = 0.283 + 0.203 + 0.200 + 0.037
      = 0.723
```

---

## 7. Semantic Search & Recommendations

All semantic features use the **pgvector** cosine distance operator (`<=>`) over 384-dimensional embeddings.

### Search Flow

```
User query
  │
  ▼
embed_single(query)          ← SentenceTransformer all-MiniLM-L6-v2
  │
  ▼
SELECT article, embedding <=> query_vec AS distance
FROM articles
WHERE embedding IS NOT NULL
ORDER BY distance
LIMIT {limit}
  │
  ▼
score = 1.0 - distance      ← Convert cosine distance to similarity
  │
  ▼
Return ranked results with scores
```

### Recommendation Strategies

| Strategy         | Trigger                      | How it works                                                       |
|------------------|------------------------------|--------------------------------------------------------------------|
| **similar_to**   | `?similar_to={article_id}`   | Fetch article's embedding, find nearest neighbors by cosine distance |
| **topic**        | `?topic={text}`              | Embed the topic string, run semantic search                        |
| **personalized** | `/feed/{user_id}`            | For each user preference `(topic, weight)`: run semantic search, multiply scores by weight, keep best score per article, sort descending |

### Personalized Feed Algorithm

```python
scored = {}
for pref in user_preferences:                    # e.g. ("AI", 0.8), ("Climate", 1.0)
    results = semantic_search(pref.topic, limit)
    for article, score in results:
        weighted = score * pref.weight
        if article.id not in scored or scored[article.id] < weighted:
            scored[article.id] = weighted         # Keep max weighted score
return sorted(scored, by=weighted_score, descending)[:limit]
```

---

## 8. Frontend Pages & Components

Next.js 14 (App Router) application styled with Tailwind CSS. All pages are client components. Branded as **"Nexus"**.

### Pages

| Route                 | Component               | Key Behavior                                                          |
|-----------------------|-------------------------|-----------------------------------------------------------------------|
| `/`                   | `HomePage`              | Ranked feed with publisher/language/category filters. Auto-refreshes every 60 seconds. Featured article + grid layout with clustering. |
| `/search`             | `SearchContent`         | Reads `?q=` param, calls `/search` endpoint, displays results with similarity scores. |
| `/recommendations`    | `RecommendationsPage`   | Topic input form → `/recommendations?topic=` → scored results.         |
| `/articles/[id]`      | `ArticleDetailPage`     | Full article body, translation toggle, cover image, topic tags. Loads 6 related articles via `?similar_to=`. Tracks view with session UUID from localStorage. |

### Components

| Component          | Purpose                                                                                      |
|--------------------|----------------------------------------------------------------------------------------------|
| `Navbar`           | Global header: date, "Nexus" logo, navigation links (Front Page, Search, For You). Active state indicator. |
| `ArticleGrid`      | Segments articles into standalones and clusters (by `dedup_cluster_id`). First standalone becomes featured. 3-column responsive grid with stagger animations. |
| `ArticleCard`      | Two variants: **featured** (21/9 aspect, gradient overlay, large title) and **regular** (16/10 aspect, stacked layout). Shows score badge when available. |
| `ArticleCluster`   | Groups articles with same `dedup_cluster_id`. Main article (with image preferred) on left, compact entries on right. "Show more" toggle for 5+ sources. |
| `CategoryTabs`     | Scrollable tabs: All, US, Global, Business, Technology, Arts, Sports, Entertainment, General. |
| `SearchBar`        | Input with search icon. Form submits to `/search?q=`. Compact variant for navbar.            |
| `Pagination`       | Previous/Next buttons with "Page X of Y" display.                                            |

### Frontend → API Communication

```typescript
// lib/api.ts
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// All requests use cache: "no-store" (always fresh)
async function fetchApi<T>(path: string, params?: Record<string, string>): Promise<T>
```

### Session & View Tracking

- A UUID is generated on first visit and stored in `localStorage` as `fundus_session_id`
- On article detail page load, a fire-and-forget `POST /articles/{id}/view` is sent with the session ID
- Errors are silently ignored

---

## 9. Key Thresholds & Configuration

All values are configurable via environment variables (see `config.py`).

| Component          | Parameter                          | Default          | Description                                          |
|--------------------|------------------------------------|------------------|------------------------------------------------------|
| **Embedding**      | `EMBEDDING_MODEL`                  | `all-MiniLM-L6-v2` | SentenceTransformer model name                    |
|                    | `EMBEDDING_DIM`                    | `384`            | Vector dimensions                                    |
| **Ranking**        | `RANKING_FRESHNESS_WEIGHT`         | `0.40`           | Weight of recency in composite score                 |
|                    | `RANKING_PROMINENCE_WEIGHT`        | `0.35`           | Weight of cluster coverage                           |
|                    | `RANKING_AUTHORITY_WEIGHT`         | `0.20`           | Weight of publisher tier                             |
|                    | `RANKING_ENGAGEMENT_WEIGHT`        | `0.05`           | Weight of view count                                 |
|                    | `RANKING_RECENCY_HALF_LIFE_HOURS`  | `48.0`           | Freshness decay half-life                            |
|                    | `RANKING_DIVERSITY_LAMBDA`         | `0.30`           | MMR relevance-diversity trade-off                    |
| **Dedup**          | `DEDUP_THRESHOLD`                  | `0.50`           | Cosine similarity threshold for clustering           |
| **Categorization** | `CATEGORY_SEMANTIC_MIN_SCORE`      | `0.12`           | Minimum similarity to assign a category              |
|                    | `CATEGORY_SEMANTIC_MIN_MARGIN`     | `0.02`           | Minimum gap between 1st and 2nd category             |
| **Authority**      | Tier 1                             | `1.0`            | Wire services, papers of record                      |
|                    | Tier 2                             | `0.7`            | Established national/digital outlets                 |
|                    | Default                            | `0.4`            | Unknown/regional publishers                          |
| **Scheduler**      | `--interval`                       | `10` min         | Time between crawl cycles                            |
|                    | `--max-articles`                   | `100`            | Max articles per publisher per cycle                 |
|                    | `--batch-size`                     | `64`             | Embedding batch size                                 |
|                    | Stale embedding age                | `7` days         | Re-embed threshold                                   |
| **API**            | Candidate limit                    | `200`            | Max articles scored per ranking query                |
|                    | Default page size                  | `20`             | Articles per page                                    |
|                    | Search limit range                 | `1–100`          | Allowed search result count                          |
| **Frontend**       | Auto-refresh interval              | `60` sec         | Home page polling frequency                          |
|                    | Related articles                   | `6`              | Similar articles on detail page                      |
|                    | Cluster display limit              | `5`              | Sources shown before "Show more"                     |
| **Categories**     | Available                          | 8                | US, Global, Business, Technology, Arts, Sports, Entertainment, General |

---

## 10. File Structure

```
fundus-recommend/
├── docker-compose.yml            # Dev: PostgreSQL only
├── docker-compose.prod.yml       # Prod: postgres + api + scheduler + frontend
├── Dockerfile                    # Python 3.12 API/scheduler image
├── .env.example                  # Environment variable template
│
├── src/fundus_recommend/
│   ├── config.py                 # Pydantic Settings (all thresholds)
│   ├── main.py                   # FastAPI app + CORS + health endpoint
│   │
│   ├── models/
│   │   ├── db.py                 # SQLAlchemy ORM models (Article, User, etc.)
│   │   └── schemas.py            # Pydantic request/response schemas
│   │
│   ├── api/
│   │   ├── articles.py           # GET /articles, /articles/{id}, POST /articles/{id}/view
│   │   ├── search.py             # GET /search
│   │   ├── recommendations.py    # GET /recommendations, /feed/{user_id}
│   │   └── preferences.py        # POST /preferences
│   │
│   ├── db/
│   │   ├── session.py            # SQLAlchemy engine & session factories
│   │   └── queries.py            # Async query functions (ranking, search, recs)
│   │
│   ├── services/
│   │   ├── embeddings.py         # SentenceTransformer encoding
│   │   ├── ranking.py            # Composite scoring & MMR reranking
│   │   ├── publisher_authority.py # 3-tier publisher authority system
│   │   ├── categorizer.py        # 7-category semantic classifier
│   │   ├── dedup.py              # Cosine similarity clustering
│   │   ├── translation.py        # Google Translate integration
│   │   └── date_resolution.py    # Date parsing & ambiguity resolution
│   │
│   └── cli/
│       ├── schedule.py           # Main scheduler loop (crawl → translate → embed → categorize → dedup → refresh)
│       ├── crawl.py              # One-shot crawl
│       ├── embed.py              # One-shot embed
│       ├── classify.py           # Batch re-categorization
│       └── fix_dates.py          # Date correction utility
│
└── frontend/
    ├── Dockerfile                # Node 20 Alpine, Next.js build
    ├── package.json              # Next.js 14, React 18, Tailwind CSS
    ├── tailwind.config.ts        # Custom theme (Playfair Display, cream/ink palette)
    │
    ├── app/
    │   ├── layout.tsx            # Root layout: Navbar, footer, Google Fonts
    │   ├── page.tsx              # Home: ranked feed + filters + 60s auto-refresh
    │   ├── globals.css           # Rules, noise texture, scrollbar, animations
    │   ├── search/page.tsx       # Semantic search results
    │   ├── recommendations/page.tsx  # Topic recommendations
    │   └── articles/[id]/page.tsx    # Article detail + related + view tracking
    │
    ├── components/
    │   ├── Navbar.tsx            # Header with navigation
    │   ├── ArticleGrid.tsx       # Featured + grid + cluster layout
    │   ├── ArticleCard.tsx       # Article card (featured/regular variants)
    │   ├── ArticleCluster.tsx    # Multi-source story group
    │   ├── CategoryTabs.tsx      # Category filter tabs
    │   ├── SearchBar.tsx         # Search input form
    │   └── Pagination.tsx        # Page navigation
    │
    └── lib/
        ├── api.ts                # API client, types, session management
        └── article-utils.ts      # Title display helpers
```

---

## 11. CLI Entry Points

Defined in `pyproject.toml`:

| Command          | Module                       | Purpose                                                |
|------------------|------------------------------|--------------------------------------------------------|
| `fr-schedule`    | `cli.schedule:main`          | Main scheduler loop (crawl + translate + embed + categorize + dedup + refresh) |
| `fr-crawl`       | `cli.crawl:main`             | One-shot crawl from specified publishers               |
| `fr-embed`       | `cli.embed:main`             | Generate embeddings for un-embedded articles           |
| `fr-classify`    | `cli.classify:main`          | Batch re-categorization of all articles                |
| `fr-fix-dates`   | `cli.fix_dates:main`         | Fix ambiguous dates for specific publishers            |

---

## 12. Dependencies

**Backend** (`pyproject.toml`, Python >= 3.10):

| Package                | Version     | Purpose                          |
|------------------------|-------------|----------------------------------|
| `fastapi`              | >= 0.110    | Web framework                    |
| `uvicorn[standard]`    | >= 0.29     | ASGI server                      |
| `sqlalchemy[asyncio]`  | >= 2.0      | ORM (async + sync sessions)      |
| `asyncpg`              | >= 0.29     | Async PostgreSQL driver          |
| `psycopg2-binary`      | >= 2.9      | Sync PostgreSQL driver           |
| `pgvector`             | >= 0.3      | Vector similarity for SQLAlchemy |
| `alembic`              | >= 1.13     | Database migrations              |
| `pydantic`             | >= 2.0      | Data validation                  |
| `pydantic-settings`    | >= 2.0      | Settings from env                |
| `sentence-transformers` | >= 3.0     | Embedding model                  |
| `numpy`                | >= 1.26     | Numerical operations             |
| `fundus`               | >= 0.5.5    | News crawler library             |
| `click`                | >= 8.0      | CLI framework                    |
| `deep-translator`      | >= 1.11     | Google Translate wrapper         |

**Frontend** (`package.json`):

| Package          | Version    | Purpose               |
|------------------|------------|------------------------|
| `next`           | 14.2.35    | React framework        |
| `react`          | ^18        | UI library             |
| `tailwindcss`    | ^3.4.1     | Utility CSS            |
| `typescript`     | ^5         | Type safety            |

## Adapter-Based Ingestion (2026-02)

### What changed
- Crawling now resolves explicit publisher IDs through an adapter registry instead of relying on Fundus country collections by default.
- Supported adapter types:
  - `rss`
  - `official_api`
  - `licensed_feed`
  - `fundus`
- Legacy country codes (for example `us`) are still accepted, but they are deprecated and routed through the Fundus adapter.

### Publisher mapping
- `reuters` -> `licensed_feed`
- `nyt` -> `official_api`
- `washington-post` -> `rss`
- `cnn` -> `rss`
- `bloomberg` -> `licensed_feed`
- `npr` -> `rss`
- `wsj` -> `licensed_feed`
- `axios` -> `licensed_feed`
- `propublica` -> `rss`
- `politico` -> `licensed_feed`
- `the-atlantic` -> `rss`

### Crawl diagnostics
Two new tables persist crawl diagnostics:
- `crawl_runs`
- `crawl_run_publishers`

`crawl_run_publishers.status_histogram` stores per-publisher status counts (for example `200`, `401`, `403`, `429`, `5xx`, `timeout`, `connection_error`, `parse_error`).

### Fetch policy controls
Configurable settings (env vars):
- `CRAWL_TIMEOUT_SECONDS`
- `CRAWL_MAX_RETRIES`
- `CRAWL_BACKOFF_SECONDS`
- `CRAWL_RATE_LIMIT_PER_MINUTE`
- `CRAWL_CIRCUIT_BREAKER_THRESHOLD`
- `CRAWL_CIRCUIT_BREAKER_COOLDOWN_SECONDS`

### CLI examples
- One-shot crawl with explicit publisher IDs:
  - `fr-crawl --publishers cnn,npr,propublica --max-articles 25`
- Scheduler run once with adapter IDs:
  - `fr-schedule --publishers cnn,npr,propublica,the-atlantic --run-once`
- Legacy compatibility (deprecated warning expected):
  - `fr-crawl --publishers us --max-articles 25`
