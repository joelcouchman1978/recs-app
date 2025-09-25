#!/usr/bin/env bash
set -uo pipefail

API_BASE="${API_BASE:-http://localhost:8000}"
PROFILE="${PROFILE:-ross}"
SEED="${SEED:-99}"

if ! READY_PAYLOAD=$(curl -fsS -o /dev/null "${API_BASE}/readyz" 2>/dev/null); then
  echo "❌ API not reachable at ${API_BASE}/readyz"
  echo "   Try: make api-local    # no Docker needed (SQLite, in-proc cache)"
  exit 1
fi

pass() { printf "✅ %s\n" "$*"; }
fail() { printf "❌ %s\n" "$*"; exit 1; }

jq -V >/dev/null 2>&1 || fail "jq is required"

echo "Preflight against ${API_BASE}"

# 1) readiness
echo "$READY_PAYLOAD" | jq '.status' | grep -q '"ok"' && pass "/readyz ok" || fail "/readyz not ok"

# 2) metrics present
M="$(curl -sf "${API_BASE}/metrics")"
echo "$M" | grep -q 'recs_build_info' && pass "metrics: build info" || fail "metrics: build info missing"
echo "$M" | grep -Eq 'recs_request_latency_ms_bucket' && pass "metrics: latency histogram" || fail "metrics: latency missing"
echo "$M" | grep -Eq 'recs_cache_(hits|misses)_total' && pass "metrics: cache counters" || fail "metrics: cache counters missing"
echo "$M" | grep -q 'recs_stale_ratio_bucket' && pass "metrics: stale ratio" || fail "metrics: stale ratio missing"

# 3) seeded determinism
A=$(curl -sf "${API_BASE}/recommendations?for=${PROFILE}&seed=${SEED}" | jq -r '.[0].id // .items[0].id')
B=$(curl -sf "${API_BASE}/recommendations?for=${PROFILE}&seed=${SEED}" | jq -r '.[0].id // .items[0].id')
test -n "$A" && test "$A" = "$B" && pass "seeded determinism stable" || fail "seeded determinism drift"

# 4) family mix explain (optional meta)
FM=$(curl -sf "${API_BASE}/recommendations?for=${PROFILE}&intent=family_mix&seed=${SEED}&explain=true" | jq '.family | has("strong_min_fit")' 2>/dev/null || echo false)
test "$FM" = "true" && pass "family meta present (explain=true)" || pass "family meta not enabled (ok)"

# 5) admin config summary (if present)
if curl -sf "${API_BASE}/admin/config/summary" >/dev/null; then
  pass "admin config summary reachable"
else
  echo "ℹ️  /admin/config/summary not found (ok if not deployed)"
fi

# 6) availability stale flag (best-effort)
curl -sf "${API_BASE}/recommendations?for=${PROFILE}&seed=${SEED}" \
 | jq '(.items // .) | .[0].availability | has("stale")' 2>/dev/null \
 | grep -q true && pass "availability payload has stale flag" || pass "availability stale flag not present (ok)"

echo "All preflight checks passed."

# Optional family guardrail summary (non-blocking)
echo "• Family guardrail:"
curl -fsS -o /dev/null "${API_BASE}/recommendations?for=ross&intent=family_mix&seed=99&explain=true" \
| jq '.family | {locked: ((.strong_locked_ids//[])|length), has_warning: has("warning")}'
