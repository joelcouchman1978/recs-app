#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

VENV_DIR=".venv_api"

# Prefer the repo's intended Python version when available.
VENV_PY="${VENV_PY:-}"
if [ -z "${VENV_PY}" ]; then
  if command -v python3.11 >/dev/null 2>&1; then
    VENV_PY="python3.11"
  else
    VENV_PY="python3"
  fi
fi

if [ -d "${VENV_DIR}" ]; then
  existing_ver="$("${VENV_DIR}/bin/python" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || true)"
  desired_ver="$("${VENV_PY}" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || true)"
  if [ -n "${existing_ver}" ] && [ -n "${desired_ver}" ] && [ "${existing_ver}" != "${desired_ver}" ]; then
    echo "Recreating ${VENV_DIR} (was Python ${existing_ver}, want ${desired_ver})"
    rm -rf "${VENV_DIR}"
  fi
fi

if [ ! -d "${VENV_DIR}" ]; then
  "${VENV_PY}" -m venv "${VENV_DIR}"
fi

# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

PYBIN="python"

# Ensure packaging basics exist without requiring network.
"$PYBIN" -m ensurepip --upgrade >/dev/null 2>&1 || true

REQS_FILE="apps/api/requirements.txt"
if [ ! -f "${REQS_FILE}" ]; then
  echo "Missing ${REQS_FILE}; cannot install full API deps. Falling back to lite API." >&2
  exec "$PYBIN" -m apps.api.app.lite_server --host "${HOST:-127.0.0.1}" --port "${PORT:-8000}"
fi

install_full_api_deps() {
  if [ -d "vendor/wheels" ] && compgen -G "vendor/wheels/*.whl" >/dev/null; then
    echo "Installing API deps from vendor/wheels (offline)…"
    "$PYBIN" -m pip install --no-index --find-links=vendor/wheels -r "${REQS_FILE}"
  else
    # Avoid long pip retries when completely offline (common in sandboxes).
    if ! "$PYBIN" - <<'PY' >/dev/null 2>&1
import socket
socket.setdefaulttimeout(1.0)
socket.getaddrinfo("pypi.org", 443)
print("ok")
PY
    then
      echo "No network/DNS for PyPI detected; skipping full install." >&2
      return 1
    fi
    echo "Installing API deps from PyPI…"
    "$PYBIN" -m pip install -r "${REQS_FILE}"
  fi
}

run_lite() {
  if ! "$PYBIN" - <<'PY' >/dev/null 2>&1
import socket
s = socket.socket()
s.bind(("127.0.0.1", 0))
s.close()
PY
  then
    echo "Socket bind not permitted; cannot start an HTTP server in this environment." >&2
    echo "Running lite smoke checks instead…" >&2
    exec "$PYBIN" -m apps.api.app.lite_smoke
  fi
  echo "Starting lite API (no FastAPI/DB deps)…" >&2
  exec "$PYBIN" -m apps.api.app.lite_server --host "${HOST:-127.0.0.1}" --port "${PORT:-8000}"
}

if [ "${RECS_LITE:-0}" = "1" ]; then
  run_lite
fi

if ! install_full_api_deps; then
  echo "Full API dependency install failed; falling back to lite API. (See docs/OFFLINE_DEV.md)" >&2
  run_lite
fi

if ! "$PYBIN" -c "import fastapi, uvicorn" >/dev/null 2>&1; then
  echo "FastAPI/Uvicorn not importable after install; falling back to lite API." >&2
  run_lite
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

if ! "$PYBIN" - <<'PY' >/dev/null 2>&1
import socket
s = socket.socket()
s.bind(("127.0.0.1", 0))
s.close()
PY
then
  echo "Socket bind not permitted; cannot start an HTTP server in this environment." >&2
  echo "Running lite smoke checks instead…" >&2
  exec "$PYBIN" -m apps.api.app.lite_smoke
fi

exec "$PYBIN" -m uvicorn apps.api.app.main:app --host "${HOST:-127.0.0.1}" --port "${PORT:-8000}"
