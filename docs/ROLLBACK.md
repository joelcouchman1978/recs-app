# Rollback

## Quick rollback
```
git checkout <previous-tag>
docker compose -f infra/docker-compose.prod.yml up -d --build
```

Verify:
- `/readyz` OK
- `/metrics` → `recs_build_info{version=<previous>, git_sha=<sha>}`
- `make preflight && make preflight-family` green

