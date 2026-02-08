#!/usr/bin/env bash
set -euo pipefail
BASE=${API_BASE:-http://localhost:8000}
SEED=${1:-777}
TOKEN=${TOKEN:-devtoken:demo@local.test}
AUTH=(-H "Authorization: Bearer ${TOKEN}")
curl -s "${AUTH[@]}" "$BASE/recommendations?for=ross&seed=$SEED" -o "ross_${SEED}.json"
curl -s "${AUTH[@]}" "$BASE/recommendations?for=family&intent=family_mix&seed=$SEED&explain=true" -o "family_${SEED}.json"
echo "Saved: ross_${SEED}.json, family_${SEED}.json"
