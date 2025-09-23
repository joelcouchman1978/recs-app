.PHONY: preflight preflight-family refresh-dry smoke open-prom open-grafana open-alerts api-local api-local-stop preflight-local sandbox-smoke

API_BASE ?= http://localhost:8000

preflight:
	API_BASE=$(API_BASE) bash ./scripts/preflight.sh

preflight-family:
	@curl -fsS "$(API_BASE)/recommendations?for=ross&intent=family_mix&seed=99&explain=true" \
	| jq -e '.family | (has("strong_locked_ids") and (.strong_locked_ids|length>0)) or has("warning")' >/dev/null \
	&& echo "✅ Family Mix guardrail OK" || (echo "❌ Family Mix guardrail FAIL"; exit 1)

refresh-dry:
	@curl -fsS -X POST "$(API_BASE)/admin/jobs/daily_refresh?dry_run=true" | jq

smoke: preflight preflight-family

open-prom:
	@python -c "import webbrowser; webbrowser.open('http://localhost:9090')"

open-grafana:
	@python -c "import webbrowser; webbrowser.open('http://localhost:3001')"

open-alerts:
	@python -c "import webbrowser; webbrowser.open('http://localhost:9093')"


api-local:
	@echo "Starting API locally (SQLite, no Redis)..."
	./scripts/run_api_local.sh

api-local-stop:
	@echo "Stopping local API (best-effort)"
	@pkill -f "uvicorn apps.api.app.main:app" || true

preflight-local:
	@API_BASE=$${API_BASE:-http://localhost:8000} bash ./scripts/preflight.sh

sandbox-smoke: api-local
	@sleep 1
	@$(MAKE) preflight-local
