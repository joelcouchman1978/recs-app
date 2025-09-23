#!/usr/bin/env bash
set -euo pipefail

HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/.." && pwd)

export COMPOSE_FILE=$ROOT/infra/docker-compose.yml

echo "[1/5] Starting core services (postgres, redis)..."
docker compose -f "$COMPOSE_FILE" up -d postgres redis

echo "[2/5] Waiting for postgres to be healthy..."
until docker compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U ${POSTGRES_USER:-dev} -d ${POSTGRES_DB:-recs}; do
  sleep 2
done

echo "[3/5] Applying migrations..."
docker compose -f "$COMPOSE_FILE" run --rm api bash -lc "cd /app && pip install -q -e . && alembic -c /infra/alembic.ini upgrade head"

echo "[4/5] Seeding mock data..."
docker compose -f "$COMPOSE_FILE" run --rm api bash -lc "cd /app && pip install -q -e . && python /app/app/seed_entrypoint.py || true"

echo "[5/5] Starting all services (api, recsys, web)..."
docker compose -f "$COMPOSE_FILE" up --build -d api recsys web

echo "Done. Web: http://localhost:${WEB_PORT:-3000}  API: http://localhost:${API_PORT:-8000}/docs"

