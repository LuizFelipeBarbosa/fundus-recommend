#!/bin/sh
set -e

PUBLISHERS="${SCHEDULER_PUBLISHERS:-all-countries}"
MAX_ARTICLES="${SCHEDULER_MAX_ARTICLES:-25}"
WORKERS="${SCHEDULER_WORKERS:-8}"
BATCH_SIZE="${SCHEDULER_BATCH_SIZE:-64}"
INTERVAL_MINUTES="${SCHEDULER_INTERVAL_MINUTES:-5}"
RUN_MODE="${SCHEDULER_RUN_MODE:-loop}"
LANGUAGE="${SCHEDULER_LANGUAGE:-}"

echo "Running scheduler (mode=$RUN_MODE) with publishers=$PUBLISHERS max_articles=$MAX_ARTICLES workers=$WORKERS interval=${INTERVAL_MINUTES}m"

echo "Applying migrations before scheduler run..."
retries=0
max_retries=30
until alembic upgrade head 2>&1; do
  retries=$((retries + 1))
  if [ "$retries" -ge "$max_retries" ]; then
    echo "Failed to run migrations after $max_retries attempts"
    exit 1
  fi
  echo "Database not ready (attempt $retries/$max_retries), retrying in 2s..."
  sleep 2
done

if [ "$RUN_MODE" = "once" ]; then
  if [ -n "$LANGUAGE" ]; then
    exec fr-schedule \
      --publishers "$PUBLISHERS" \
      --max-articles "$MAX_ARTICLES" \
      --workers "$WORKERS" \
      --batch-size "$BATCH_SIZE" \
      --language "$LANGUAGE" \
      --run-once
  fi

  exec fr-schedule \
    --publishers "$PUBLISHERS" \
    --max-articles "$MAX_ARTICLES" \
    --workers "$WORKERS" \
    --batch-size "$BATCH_SIZE" \
    --run-once
fi

if [ -n "$LANGUAGE" ]; then
  exec fr-schedule \
    --publishers "$PUBLISHERS" \
    --max-articles "$MAX_ARTICLES" \
    --workers "$WORKERS" \
    --batch-size "$BATCH_SIZE" \
    --language "$LANGUAGE" \
    --interval "$INTERVAL_MINUTES"
fi

exec fr-schedule \
  --publishers "$PUBLISHERS" \
  --max-articles "$MAX_ARTICLES" \
  --workers "$WORKERS" \
  --batch-size "$BATCH_SIZE" \
  --interval "$INTERVAL_MINUTES"
