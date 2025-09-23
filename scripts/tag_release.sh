#!/usr/bin/env bash
set -euo pipefail
VER="${1:-}"
if [ -z "$VER" ]; then
  echo "Usage: $0 vX.Y.Z"; exit 1
fi
# Optionally persist version in the repo-root .env that compose loads
if [ -f .env ]; then
  if grep -q "^APP_VERSION=" .env; then
    sed -i.bak "s/^APP_VERSION=.*/APP_VERSION=${VER}/" .env
  else
    echo "APP_VERSION=${VER}" >> .env
  fi
  git add .env || true
fi
git commit -m "release: ${VER}" || true
git tag -a "${VER}" -m "AU TV Recommender ${VER}"
git push origin "${VER}"
