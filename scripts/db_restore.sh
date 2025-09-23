#!/usr/bin/env bash
set -euo pipefail

IN="${1:-}"
if [ -z "$IN" ] || [ ! -f "$IN" ]; then
  echo "Usage: $0 infra/backup_YYYYmmdd_HHMMSS.sql.gz" >&2
  exit 1
fi

gunzip -c "$IN" | docker compose -f infra/docker-compose.prod.yml exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
echo "Restored from $IN"

