# AU TV Recommender — v0.1.0

## Highlights
- Deterministic slates (seeded) with spoiler-safe rationales
- Family Mix guardrail (≥1 strong pick or explicit warn)
- Season match chip + rationale hint
- AU availability freshness: daily refresh job + scheduler
- Monitoring: Prometheus (env-driven alerts), Grafana dashboards
- Alerting: Alertmanager + Slack (native) + Teams/Discord via relay
- CI: build SHA in metrics; preflight + family guard; tag-smoke workflow

## Ops expectations
- p95 latency target: `${RECS_TARGET_P95_MS}` ms (env-driven)
- Stale-ratio warn threshold: `${STALE_RATIO_WARN}`
- Daily refresh: 03:00 local, limit `${DAILY_REFRESH_LIMIT}`

## How to roll back
- `git revert <last-merge-commit>` or deploy previous tag (`git checkout v0.1.0^`)
- Confirm `/metrics` exposes prior `version/sha`, then run preflight

## Known follow-ups
- Optional: provider confidence weighting
- Stronger ranking fixtures for history adjacency

