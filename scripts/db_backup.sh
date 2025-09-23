#!/usr/bin/env bash
set -euo pipefail

STAMP=$(date +"%Y%m%d_%H%M%S")
OUT="backup_${STAMP}.sql.gz"

docker compose -f infra/docker-compose.prod.yml exec -T postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "infra/${OUT}"
echo "Wrote infra/${OUT}"

