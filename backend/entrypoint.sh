#!/usr/bin/env bash
# Runs pending Alembic migrations, then starts the API. Migration failures
# abort startup loudly rather than serving against a stale/missing schema.
set -euo pipefail

echo "[entrypoint] Running database migrations..."
alembic upgrade head

echo "[entrypoint] Starting API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
