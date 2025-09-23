# Recs App — Grafana Dashboard

This folder contains a ready-to-import Grafana dashboard for the app's Prometheus metrics.

## Import
1. Open Grafana → Dashboards → Import.
2. Upload `recs-dashboard.json`.
3. Select your Prometheus datasource.

## Panels
- Build / Env: shows current version, sha, env via `recs_build_info`.
- P95 latency (ms): `histogram_quantile(0.95, sum(rate(recs_request_latency_ms_bucket[5m])) by (le))`
- Cache hit ratio: `hits/(hits+misses)` over 5m
- Stale ratio (p90): `histogram_quantile(0.9, …recs_stale_ratio_bucket…)`
- Job failures (1h): `increase(jobs_failure_total[1h])` by `job`
- Adapter errors (1h): `increase(adapter_errors_total[1h])` by `adapter`
- Slow requests rate: `rate(recs_slow_requests_total[5m])`

> Tip: Add a panel for `sum by (intent) (rate(recs_items_total[5m]))` to see traffic per intent.
