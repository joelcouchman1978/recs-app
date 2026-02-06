#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

API_BASE="${API_BASE:-http://localhost:8000}"
TOKEN="${TOKEN:-devtoken:demo@local.test}"

PY="${PY:-}"
if [ -z "${PY}" ]; then
  if command -v python3.11 >/dev/null 2>&1; then
    PY="python3.11"
  else
    PY="python3"
  fi
fi

# Some sandboxes disallow binding sockets entirely, so running an HTTP server is impossible.
if ! "$PY" - <<'PY' >/dev/null 2>&1
import socket
s = socket.socket()
s.bind(("127.0.0.1", 0))
s.close()
PY
then
  echo "ℹ️  Socket bind not permitted here; running lite smoke checks (no HTTP server)…"
  exec "$PY" -m apps.api.app.lite_smoke
fi

LOG="/tmp/recs_api.log"
mkdir -p .local

(API_BASE="$API_BASE" TOKEN="$TOKEN" bash ./scripts/run_api_local.sh) >"$LOG" 2>&1 &
pid=$!
trap 'kill "$pid" >/dev/null 2>&1 || true' EXIT

for _ in {1..80}; do
  if curl -fsS "${API_BASE}/readyz" >/dev/null 2>&1; then
    break
  fi
  sleep 0.25
done

curl -fsS "${API_BASE}/readyz" >/dev/null

API_BASE="$API_BASE" TOKEN="$TOKEN" bash ./scripts/preflight.sh
echo "✅ sandbox-smoke OK (log: ${LOG})"
