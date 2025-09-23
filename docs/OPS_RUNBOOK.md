# Ops Runbook (Quick)

## When an alert fires
1) Check Grafana panels (p95 latency, stale ratio).
2) Inspect `/metrics` for error counters; tail API logs for `request_id`.
3) If stale ratio rises: `make refresh-dry` → consider triggering real refresh.

## Family Mix guard failures
- Run: `make preflight-family` locally to reproduce; check thresholds in Admin → Config Summary.

## Links
- Prometheus: http://localhost:9090
- Grafana:    http://localhost:3001
- Alertmanager: http://localhost:9093

