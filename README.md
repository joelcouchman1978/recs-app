# Personalised TV Show Recommender (MVP)

Monorepo for a web-based, text-only hybrid TV recommender for three profiles (Ross, Wife, Son) plus a Family Mix mode. AU region availability, spoiler-averse copy, transparent rationales.

## Stack
- apps/web: Next.js 14 (TypeScript, App Router, Tailwind)
- apps/api: FastAPI (Python) + SQLModel/SQLAlchemy + Alembic + pgvector
- services/recsys: Python worker (RQ) for embeddings + scoring
- packages/shared: Shared TS types (OpenAPI client), zod schemas
- infra: Docker Compose (Postgres + pgvector, Redis), migrations, env

## Quickstart

1) Copy env

```
cp infra/env.example .env
```

2) Bootstrap services (first run will build images, run migrations, seed data):

```
bash scripts/dev_bootstrap.sh
```

3) Access
- Web: http://localhost:3000
- API docs: http://localhost:8000/docs

## Production-like Run (Compose)

To run with production builds (no dev servers):

```
cd recs-app
cp infra/env.example .env  # if not already present
docker compose -f infra/docker-compose.prod.yml up -d --build
```

> After the stack is up, see **[Monitoring (Prometheus & Grafana)](#monitoring-prometheus--grafana)** for dashboards and env-driven alerts.
> Quick links (dev): Prometheus http://localhost:9090 · Grafana http://localhost:3001 (admin/admin)

Services:
- API: http://localhost:8000 (health: /healthz)
- Web: http://localhost:3000
- Postgres: localhost:5432
- Redis: localhost:6379

To stop: `docker compose -f infra/docker-compose.prod.yml down`

## OpenAPI Types (TS)
- Generate from live API: `bash scripts/generate_types.sh`
- Or inside `packages/shared`: `pnpm i && pnpm gen`

## Developer notes
- Python 3.11, Node 20
- Run alembic with config at `infra/alembic.ini` (e.g., from `apps/api`):
  `alembic -c ../../infra/alembic.ini upgrade head`
- Feature flags in `.env`: `USE_REAL_JUSTWATCH`, `USE_REAL_SERIALIZD`, `REGION=AU`
  - Admin: `ADMIN_EMAILS=demo@local.test` (comma-separated) gates `/admin/*` endpoints by email; tokens are `devtoken:<email>` in dev.
  - Cache: set `REDIS_URL` to enable distributed recommendation cache; otherwise uses in-process LRU (TTL 60s).

## Real Data Adapters (Optional)

- JustWatch (AU availability)
  - Set in `.env`: `USE_REAL_JUSTWATCH=true` and `REGION=AU`
  - Triggers nightly job and admin sync to fetch availability via public endpoints.
  - Provider mapping is best-effort; adjust `services/recsys/adapters/justwatch.py` for more providers.

- Serializd (ratings)
  - Set: `USE_REAL_SERIALIZD=true`, `SERIALIZD_USER=<your username/email>`, `SERIALIZD_TOKEN=<token>`
  - Admin sync pulls ratings and maps to shows by title/year.
  - Mapping can be extended to use external IDs if present from Serializd.


## Run Without Docker (Local DB)

If you prefer running services locally without Docker:

1) Install prerequisites
- Postgres 16, Redis 7, Python 3.11, Node 20, pnpm

2) Create database and user
```
createuser dev -s || true
createdb recs -O dev || true
psql -d recs -c "ALTER USER dev WITH PASSWORD 'dev';"
```

3) Environment for API (terminal session)
```
export POSTGRES_USER=dev
export POSTGRES_PASSWORD=dev
export POSTGRES_DB=recs
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export REDIS_URL=redis://localhost:6379/0
export REGION=AU
export USE_SQL_VECTOR=false
```

4) Apply migrations and seed (from `apps/api`)
```
cd apps/api
pip install -e .
alembic -c ../../infra/alembic.ini upgrade head
python app/seed_entrypoint.py
```
Note: If you lack permissions to `CREATE EXTENSION vector`, you can skip vector migrations for now:
```
alembic -c ../../infra/alembic.ini upgrade 0002_availability_unique_upsert
```
The recommender still works (ANN disabled; falls back to heuristics/arrays).

5) Run API (from `apps/api`)
```
uvicorn app.main:app --reload --port 8000
```

6) Run Web (from `apps/web`)
```
cd ../../apps/web
export NEXT_PUBLIC_API_URL=http://localhost:8000
pnpm i && pnpm dev
```

7) Tests
- API: `cd apps/api && pytest -q`
- Web unit: `cd apps/web && pnpm i && pnpm test`
- Web e2e: `cd apps/web && pnpm e2e`

## 🔁 Deterministic recommendations with `?seed=` (debugging)

Use a numeric `seed` to make slates reproducible while you tweak scoring, tags, or ratings.

### Why
- Reproduce a slate exactly for triage/bug reports.
- Compare “before vs after” when you change a rating/tag and expect a deterministic re-ordering.
- Stabilise Playwright e2e tests.

### How (Web)
- Append `?seed=<number>` to the web URL:
  - `http://localhost:3000/?seed=777`
- The web client forwards `seed` to the API automatically.
- A small “Seed: 777” badge may show in the UI (if enabled).

### How (API)
- Add `seed` to the recommendations query (dev magic token shown here):

```bash
TOKEN="devtoken:demo@local.test"
curl -s "http://localhost:8000/recommendations?for=ross&intent=default&seed=777" \
  -H "Authorization: Bearer $TOKEN" | jq '.[0]'
```

### Determinism contract

With the same profile, intents/filters, database state, and seed, the slate ordering is stable.

- Tie-breaks use a deterministic micro-jitter derived from `(item_id, seed)`.
- Changing a rating/tag/note invalidates cache and deterministically reorders items with the same seed.

### Known causes of drift

- Data changed (e.g., nightly JustWatch/Serializd syncs, embedding rebuilds).
- You switched profiles/intents/filters or cleared the DB/Redis.
- Code changes to scoring weights or feature extraction.

### Quick checks

- Current seed slate (IDs):

```bash
TOKEN="devtoken:demo@local.test"
curl -s "http://localhost:8000/recommendations?for=ross&intent=default&seed=99" \
  -H "Authorization: Bearer $TOKEN" | jq -r '.[].id'
```

- After rating change (BAD) on current top:

```bash
TOKEN="devtoken:demo@local.test"
# Find Ross profile id
PID=$(curl -s http://localhost:8000/me/profiles -H "Authorization: Bearer $TOKEN" \
  | jq -r '.[] | select(.name=="Ross") | .id')
# Capture current top item with fixed seed
TOP=$(curl -s "http://localhost:8000/recommendations?for=ross&intent=default&seed=99" \
  -H "Authorization: Bearer $TOKEN" | jq -r '.[0].id')
# Rate BAD (primary=0)
curl -s -X POST http://localhost:8000/ratings -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"profile_id":'"$PID"',"show_id":"'"$TOP"'","primary":0}' >/dev/null
# With the SAME seed, top should now differ
curl -s "http://localhost:8000/recommendations?for=ross&intent=default&seed=99" \
  -H "Authorization: Bearer $TOKEN" | jq -r '.[0].id'
```

### Good bug report template

- Seed: `123`
- Profile: `ross`
- Intent/filters: (if any)
- Top-N before/after (IDs or titles)

## Freshness & Alerts

- Daily offers refresh runs at 03:00 local time and refreshes the stalest titles first (by oldest `last_checked_ts`).
- Dry-run the job locally:

```
make refresh-dry
```

- Manually trigger via admin endpoint (requires admin auth):

```
curl -fsS -X POST "http://localhost:8000/admin/jobs/daily_refresh?dry_run=true" | jq
```

- Tuning knobs (set in `.env` or environment):
  - `OFFERS_STALE_DAYS` (default 14)
  - `DAILY_REFRESH_LIMIT` (default 200)
  - `DAILY_REFRESH_HOUR` (default 3)

- Grafana panels (infra/grafana/recs-dashboard.json):
  - p95 latency: `histogram_quantile(0.95, sum(rate(recs_request_latency_ms_bucket[$__interval])) by (le))`
  - 90p stale ratio: `histogram_quantile(0.90, sum(rate(recs_stale_ratio_bucket[$__interval])) by (le))`

- Prometheus alerts (infra/alerts/recs.rules.yml):
  - RecsP95LatencyHigh: p95 > 300ms for 10m
  - OffersStaleRatioHigh: p90 stale ratio > 0.3 for 20m
  - RecsErrorRateHigh: >50 errors in 10m (uses `recs_request_errors_total`)

## Monitoring (Prometheus & Grafana)

- **Prometheus** (alerts & raw metrics): http://localhost:9090  
  Loads env-driven alert rules generated from `infra/alerts/recs.rules.yml.tmpl`.
- **Grafana** (dashboards): http://localhost:3001  
  Default login (dev only): **admin / admin**. Pre-provisioned “Recs” folder includes:
  - p95 request latency
  - p90 stale-offer ratio

### Quick start
```bash
# Bring up prod-like stack with monitoring
docker compose -f infra/docker-compose.prod.yml up -d --build

# Generate traffic so graphs/alerts move
ab -n 200 -c 5 "http://localhost:8000/recommendations?for=ross&seed=77" || true

# Sanity
make preflight && make preflight-family
```

### Tuning alert thresholds (env-driven)

Set envs before starting Prometheus (or in `.env`):

* `RECS_TARGET_P95_MS` (default 250) and `RECS_LATENCY_FOR_MIN` (default 10)
* `STALE_RATIO_WARN` (default 0.30) and `STALE_RATIO_FOR_MIN` (default 20)
* `ERROR_RATE_HIGH_10M` (default 50) and `ERROR_RATE_FOR_MIN` (default 10)

Prometheus generates rules at container start via:

```
envsubst < /etc/prometheus/recs.rules.yml.tmpl > /etc/prometheus/recs.rules.yml
```

### Troubleshooting

* **Prometheus target down:** open [http://localhost:9090/targets](http://localhost:9090/targets) (job: `recs-api`, target: `api:8000`).
* **No graphs:** hit the API to create traffic (see `ab` command above).
* **Rules not loaded:** inside container, check `/etc/prometheus/recs.rules.yml` exists.
* **Grafana login:** change via `GF_SECURITY_ADMIN_USER/PASSWORD` envs in compose (dev uses admin/admin).
* **Ports:** web `3000`, Grafana `3001`, Prometheus `9090`.

### Security (prod)

Do **not** expose Grafana/Prometheus publicly with defaults. Set strong creds, restrict network access, or front with an auth proxy.

### Release flow quickstart
```bash
# From repo root
./scripts/ship_local_v010.sh
# Follow prompts to open PR1/PR2, run smoke, and tag v0.1.0
```
> Tip: `./scripts/ship_local_v010.sh --auto` will create & open PRs for you if the GitHub CLI is installed and authenticated (`gh auth status`). Otherwise it falls back to manual prompts.

Hands-free (requires gh CLI authenticated):
```bash
./scripts/ship_local_v010.sh --auto --merge --version v0.1.0 --release
```

Notes options:
- `--notes path/to/notes.md` to use a specific file
- `--notes-auto` to auto-generate `docs/releases/RELEASE_NOTES_<version>.md` from `git log`

### Alert notifications (optional)
We run Alertmanager at http://localhost:9093. To send alerts to a webhook, set:

`ALERT_WEBHOOK_URL=https://your-webhook.example` in `.env`

Restart compose and alerts will be delivered (send_resolved=true). For Slack/Teams/Discord, use a webhook bridge or direct incoming webhook URL.

#### Slack (native)
Set:

`ALERT_DEFAULT_RECEIVER=slack` and `SLACK_WEBHOOK_URL=<your Slack incoming webhook>`

Alertmanager will send alerts directly to Slack using its native integration.

#### Microsoft Teams (via relay)
Teams webhooks expect a different JSON. Use the optional `teams-relay`:
- Set:

ALERT_DEFAULT_RECEIVER=default
ALERT_WEBHOOK_URL=http://teams-relay:5000/alert
TEAMS_WEBHOOK_URL=<your Teams Incoming Webhook URL>

- The relay converts Alertmanager payloads into a simple Teams message.

Note: You can adapt the same approach for Discord by posting `{ "content": "..." }` to `DISCORD_WEBHOOK_URL` in a custom relay.

#### Discord (via relay)
Set:

ALERT_DEFAULT_RECEIVER=default
ALERT_WEBHOOK_URL=http://teams-relay:5000/discord
DISCORD_WEBHOOK_URL=<your Discord webhook URL>

The relay formats a concise message and posts to Discord.
- Commit SHA:
- Admin → Freshness: offers_last_checked / serializd_last_seen timestamps
- Notes: what you changed (e.g., rated top item BAD, liked tag “cozy”)

## 👨‍👩‍👧 Family Mix meta with `explain=true` (optional, debug)

`explain=true` returns extra Family Mix metadata alongside items without changing the default shape for other calls.

### Contract
- Default `GET /recommendations` → returns a list of items (unchanged).
- Family Mix context (e.g., multiple profiles or `intent=family_mix`) with `explain=true`: returns an object:

```json
{
  "items": [/* ... */],
  "family": {
    "strong_locked_ids": ["tt01234", "tt05678"],
    "warning": { "code": "no_strong_pick", "message": "No single title clears the strong-fit bar for everyone; showing best shared options." },
    "strong_min_fit": 0.78,
    "strong_rule": "min"
  }
}
```

Per-item field `family_strong: boolean` remains present and safe to read in all responses.

### Why

- See whether a strong family pick was locked into the slate.
- Understand when no strong title exists (and why a warning shows in the UI).
- Inspect thresholds used (`strong_min_fit`, `strong_rule`).

### Calls (replace `for=` with `profile_id=` if your API uses that)

- Default behavior (list only):

```bash
curl -s "http://localhost:8000/recommendations?for=ross&intent=family_mix&seed=123" | jq 'type'   # -> "array"
```

- With meta (object with items + family):

```bash
curl -s "http://localhost:8000/recommendations?for=ross&intent=family_mix&seed=123&explain=true" | jq '.family'
```

### Notes

- No breaking change: meta appears only when `explain=true` in Family Mix context.
- Caching: by design, `explain=true` responses bypass the recs cache; default responses remain cached.
- Thresholds come from environment:
  - `FAMILY_STRONG_MIN_FIT` (default `0.78`)
  - `FAMILY_STRONG_RULE` (`min`|`avg`, default `min`)
  - `FAMILY_STRONG_LOCK_COUNT` (default `1`)

### Good bug report template (Family Mix)

- Intent: `family_mix`
- Profiles: `ross, wife, son` (or your identifiers)
- Seed: `123`
- Meta: output of `...&explain=true` (`strong_locked_ids`, `warning`)
- Commit SHA / environment

See: docs/BUG_BASH.md for a 15-minute bug-bash checklist.

## Backups (prod-like compose)

Create a gzip'd SQL dump of Postgres:

```bash
bash scripts/db_backup.sh
```

Restore from a snapshot:

```bash
bash scripts/db_restore.sh infra/backup_YYYYmmdd_HHMMSS.sql.gz
```
