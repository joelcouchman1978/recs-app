# HEALTH REPORT — 2025-09-23

## Summary
1) Tooling & env (.env dev, sqlite/redis disabled): ✅  (`.env:11-31`, `infra/env.example` patched)
2) API local (uvicorn on :8000): ❌  `make api-local` → pip cannot locate `setuptools` because `vendor/wheels/` is empty (see command below).
3) Preflight-local: ❌  `make preflight-local` prints the new guidance (“Try: make api-local …”) since `/readyz` is unreachable without the server.
4) Family guard: ❌  `make preflight-family` fails with `curl: (7)` (API offline).
5) API determinism (seed=777): ❌  `pytest -q tests/test_seed_snapshots.py` fails to import FastAPI (`ModuleNotFoundError: fastapi`).
6) Relay unit tests: ✅  `PYTHONPATH=../.. pytest -q` → 5 passed.
7) Web e2e (season chip): ❌  `pnpm install --offline` → `pnpm: command not found`; `npm install` then times out with `ENOTFOUND registry.npmjs.org`.
8) Seeded artifacts: ❌  `./scripts/grab_seed_artifacts.sh 777` cannot reach the API.
9) Docker/compose preflight: ⏭️  Docker Desktop unavailable in this sandbox (`docker: command not found`).
10) Monitoring stack (Prom/Grafana/Alertmanager): ⏭️  blocked on Docker.
11) Alerts fire/recover: ⏭️  pending monitoring stack.

## Metrics sample
API never started, so `/metrics` wasn’t reachable. Sample remains pending.

## Commands & outputs
- `ls vendor/wheels` → *(empty directory; cache not yet staged)*
- `make api-local`
  ```
  Starting API locally (SQLite, no Redis)...
  ./scripts/run_api_local.sh
  Looking in links: vendor/wheels
  Obtaining file:///Users/joelcouchman/recs-app/apps/api
    Installing build dependencies: started
    Installing build dependencies: finished with status 'error'
  ...
  ERROR: Could not find a version that satisfies the requirement setuptools (from versions: none)
  pip install failed using vendor/wheels. Verify offline cache per docs/OFFLINE_DEV.md
  make: *** [api-local] Error 1
  ```
- `make preflight-local`
  ```
  ❌ API not reachable at http://localhost:8000/readyz
     Try: make api-local    # no Docker needed (SQLite, in-proc cache)
  make: *** [preflight-local] Error 1
  ```
- `make preflight-family`
  ```
  ❌ Family Mix guardrail FAIL
  curl: (7) Failed to connect to localhost port 8000 after 0 ms: Couldn't connect to server
  make: *** [preflight-family] Error 1
  ```
- `cd apps/api && pytest -q tests/test_seed_snapshots.py`
  ```
  ModuleNotFoundError: No module named 'fastapi'
  ```
- `cd infra/relay && PYTHONPATH=../.. pytest -q`
  ```
  5 passed, 1 warning in 0.13s
  ```
- `cd apps/web && pnpm install --offline`
  ```
  bash: pnpm: command not found
  ```
- `cd apps/web && npm install`
  ```
  npm ERR! network request to https://registry.npmjs.org/@testing-library%2fjest-dom failed, reason: getaddrinfo ENOTFOUND registry.npmjs.org
  ```
- `./scripts/grab_seed_artifacts.sh 777`
  ```
  curl: (7) Failed to connect to localhost port 8000 after 0 ms: Couldn't connect to server
  ```

## Notes
- Stage Python wheels in `vendor/wheels` (see `docs/OFFLINE_DEV.md`) so `make api-local` can install FastAPI + friends offline.
- Stage a pnpm store in `vendor/pnpm-store` or install pnpm+node with network access before running web tests.
- Docker Desktop required for compose-based checks once dependencies are in place.
