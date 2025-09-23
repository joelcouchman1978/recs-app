#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ ! -d ".venv_api" ]; then
  python3 -m venv .venv_api
fi
# shellcheck disable=SC1091
source .venv_api/bin/activate

PYBIN="python"

if [ -d "vendor/wheels" ]; then
  "$PYBIN" -m pip install --upgrade pip >/dev/null
  if ! "$PYBIN" -m pip install --no-index --find-links=vendor/wheels -e apps/api; then
    echo "pip install failed using vendor/wheels. Verify offline cache per docs/OFFLINE_DEV.md" >&2
    exit 1
  fi
else
  "$PYBIN" -m pip install --upgrade pip >/dev/null
  if ! "$PYBIN" -m pip install -e apps/api; then
    echo "pip install failed. Provide wheels in vendor/wheels for offline installs (see docs/OFFLINE_DEV.md)." >&2
    exit 1
  fi
fi

mkdir -p .local

if [ "${SEED_MINIMAL:-1}" = "1" ]; then
  "$PYBIN" -m apps.api.app.seed_minimal >/dev/null 2>&1 || echo "⚠️  Minimal seed may be incomplete; continuing"
fi

export USE_SQLITE=${USE_SQLITE:-1}
export DISABLE_REDIS=${DISABLE_REDIS:-1}
export ENVIRONMENT=${ENVIRONMENT:-dev}
export ALLOW_ORIGINS=${ALLOW_ORIGINS:-http://localhost:3000}
export JWT_SECRET=${JWT_SECRET:-dev-only-secret}

exec "$PYBIN" -m uvicorn apps.api.app.main:app --host 0.0.0.0 --port 8000
