#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)

API_URL=${API_URL:-http://localhost:8000}
echo "Generating OpenAPI types from $API_URL/openapi.json"
pushd "$ROOT/packages/shared" >/dev/null
if ! command -v pnpm >/dev/null 2>&1; then
  echo "pnpm not found; please install or use npm/yarn to run openapi-typescript" >&2
  exit 1
fi
pnpm install >/dev/null
pnpm exec openapi-typescript "$API_URL/openapi.json" -o src/api-types.ts
echo "Types generated at packages/shared/src/api-types.ts"
popd >/dev/null

