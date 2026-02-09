#!/bin/sh
set -e

echo "Waiting for database..."
retries=0
max_retries=30
until alembic upgrade head 2>&1; do
  retries=$((retries + 1))
  if [ "$retries" -ge "$max_retries" ]; then
    echo "Failed to connect to database after $max_retries attempts"
    exit 1
  fi
  echo "Database not ready (attempt $retries/$max_retries), retrying in 2s..."
  sleep 2
done

echo "Starting API server..."
exec uvicorn fundus_recommend.main:app --host 0.0.0.0 --port 8000
