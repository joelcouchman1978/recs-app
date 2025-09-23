# Release Checklist (vX.Y.Z)

## Before you start
- [ ] `bash scripts/dev_bootstrap.sh`
- [ ] Record determinism snapshots once:
      `cd apps/api && UPDATE_SNAPSHOTS=1 pytest -q tests/test_seed_snapshots.py`
- [ ] Verify determinism unchanged:
      `pytest -q tests/test_seed_snapshots.py`
- [ ] Web e2e:
      `cd ../web && pnpm test:e2e || npm run test:e2e`

## Merge PRs
- [ ] PR1: determinism snapshots
- [ ] PR2: season-consistent chip + rationale hint
- [ ] Ops/Docs PRs (alerts envsubst, prom+grafana compose, alertmanager, relays, monitoring docs)

## Prod-like smoke
- [ ] `docker compose -f infra/docker-compose.prod.yml up -d --build`
- [ ] `curl -fsS http://localhost:8000/readyz`
- [ ] `make preflight && make preflight-family`
- [ ] `make open-prom && make open-grafana && make open-alerts` (optional)

## Tag and verify
- [ ] Tag vX.Y.Z (see scripts/tag_release.sh)
- [ ] CI: check `/metrics` → `recs_build_info{version="vX.Y.Z", git_sha="<workflow sha>"}`
- [ ] CI: release-smoke workflow green

## Post
- [ ] Create release notes (highlights, guardrails, rollback steps)
- [ ] Set Alertmanager webhook envs in prod & test a sample alert
