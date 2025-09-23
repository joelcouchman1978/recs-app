#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
API_URL=${API_URL:-http://localhost:8000}

echo "[typegen-check] Comparing generated types to committed types from $API_URL/openapi.json"
pushd "$ROOT/packages/shared" >/dev/null

if ! command -v pnpm >/dev/null 2>&1; then
  echo "pnpm not found; install pnpm to run typegen check" >&2
  exit 2
fi

pnpm install >/dev/null
TMP=$(mktemp)
pnpm exec openapi-typescript "$API_URL/openapi.json" -o "$TMP"

if ! diff -u src/api-types.ts "$TMP" >/dev/null; then
  echo "[typegen-check] Drift detected between committed types and live OpenAPI schema" >&2
  echo "Tip: bash scripts/generate_types.sh (with API running)" >&2
  diff -u src/api-types.ts "$TMP" || true
  exit 1
fi

echo "[typegen-check] OK: Types are up to date"
popd >/dev/null

