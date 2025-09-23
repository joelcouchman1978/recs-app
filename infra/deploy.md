# Deploying recs-app (prod-like)

This guide provisions a single host running Docker, using `infra/docker-compose.prod.yml`.

## 1. Provision
- Linux VM (2 vCPU, 4GB RAM, 20GB disk) with Docker + Docker Compose.
- Open ports: 80/443 (reverse proxy, if you add one), 8000 (API), 3000 (Web) – or front them with a proxy.

## 2. Fetch code
```bash
ssh ubuntu@your-host
sudo mkdir -p /opt/recs-app && sudo chown $USER /opt/recs-app
cd /opt/recs-app
# clone your repo here
```

## 3. Environment

Create `.env.prod`:

```env
ENVIRONMENT=prod
JWT_SECRET=change-me
ALLOW_ORIGINS=https://your-domain

REGION=AU
USE_REAL_JUSTWATCH=true
USE_REAL_SERIALIZD=true
SERIALIZD_USER=...
SERIALIZD_TOKEN=...

REDIS_URL=redis://redis:6379/0
RECS_CACHE_TTL=600
RECS_CACHE_MAX=5000
FAMILY_COVERAGE_MIN_FIT=0.6
```

## 4. Run

```bash
docker compose -f infra/docker-compose.prod.yml --env-file .env.prod up -d --build
# wait ~20-60s, then
curl -s localhost:8000/healthz | jq
```

## 5. Smoke

```bash
curl -s "http://localhost:8000/recommendations?for=ross&intent=default&seed=123" -H 'Authorization: Bearer devtoken:demo@local.test' | jq 'length'
```

## 6. Logs & restart

```bash
docker compose -f infra/docker-compose.prod.yml logs -f api web recsys

docker compose -f infra/docker-compose.prod.yml restart api
```

## 7. Rollback

* Keep previous images tagged; to roll back, redeploy with prior tags or revert the Git commit and rebuild.

