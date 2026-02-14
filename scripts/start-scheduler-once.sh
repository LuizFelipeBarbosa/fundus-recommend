#!/bin/sh
set -e

PUBLISHERS="${SCHEDULER_PUBLISHERS:-cnn,npr,propublica}"
MAX_ARTICLES="${SCHEDULER_MAX_ARTICLES:-100}"
WORKERS="${SCHEDULER_WORKERS:-4}"
BATCH_SIZE="${SCHEDULER_BATCH_SIZE:-64}"
LANGUAGE="${SCHEDULER_LANGUAGE:-}"

echo "Running scheduler with publishers=$PUBLISHERS max_articles=$MAX_ARTICLES workers=$WORKERS"

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
