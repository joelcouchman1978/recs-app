# 🚦 Recs App — 15-Minute Bug-Bash

## 0) Preflight (copy-paste)
API_BASE=http://localhost:8000 PROFILE=ross SEED=99 ./scripts/preflight.sh

## 1) Seeded determinism
- Open Web: `http://localhost:3000/?seed=99`
- Reload → top card unchanged.
- Rate top item BAD → reload same seed → top changes (deterministic re-order).

## 2) Rationale safety
- Cards show “Why this fits you”.
- No spoilers; short and premise-only.

## 3) Family Mix
- Switch to Family mode (or `?intent=family_mix&seed=99`).
- Expect **Strong** banner or **No strong title** warning.

## 4) Availability freshness
- Cards show provider + “as of …”.
- If data is older than `OFFERS_STALE_DAYS`, “stale” badge appears.

## 5) Admin → Config Summary
- Version, SHA, env, thresholds visible for screenshots.

## 6) Metrics sanity (Prometheus)
- `/metrics` includes: `recs_build_info`, latency buckets, cache hits/misses, stale ratio.
- Optional Grafana: import `infra/grafana/recs-dashboard.json`.

## 7) Background jobs (optional)
- Trigger JustWatch/Serializd sync (dry-run first).
- Check Admin → Freshness timestamps update.
