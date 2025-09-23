#!/usr/bin/env bash
set -euo pipefail
BASE=${API_BASE:-http://localhost:8000}
SEED=${1:-777}
curl -s "$BASE/recommendations?for=ross&seed=$SEED" -o "ross_${SEED}.json"
curl -s "$BASE/recommendations?for=ross&intent=family_mix&seed=$SEED&explain=true" -o "family_${SEED}.json"
echo "Saved: ross_${SEED}.json, family_${SEED}.json"

