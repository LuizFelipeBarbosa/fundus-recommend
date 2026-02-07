FROM python:3.12-slim

WORKDIR /app

# Install system deps needed for psycopg2 and sentence-transformers
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY . .

RUN pip install --no-cache-dir .

# Default command is API server; scheduler overrides this
CMD ["sh", "scripts/start-api.sh"]
