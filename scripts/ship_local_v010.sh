#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

AUTO_PR=false
DRY_RUN=false
MERGE_AFTER=false
RELEASE_AFTER=false
VERSION="v0.1.0"
NOTES_PATH=""
NOTES_AUTO=false

# --- arg parsing ---
for a in "$@"; do
  case "$a" in
    --auto) AUTO_PR=true ;;
    --dry-run) DRY_RUN=true ;;
    --merge) MERGE_AFTER=true ;;
    --release) RELEASE_AFTER=true ;;
    --version)
      shift || true
      VERSION="${1:-$VERSION}"
      ;;
    --notes)
      shift || true
      NOTES_PATH="${1:-}"
      ;;
    --notes-auto)
      NOTES_AUTO=true
      ;;
    -h|--help)
      echo "Usage: $0 [--auto] [--dry-run] [--merge] [--version vX.Y.Z] [--release] [--notes path] [--notes-auto]"
      echo "  --auto    Create and open PRs automatically (requires gh CLI, authenticated)"
      echo "  --dry-run Print the commands that would run"
      echo "  --merge   Auto-merge PRs with gh when checks pass (requires --auto)"
      echo "  --version Tag version (default v0.1.0; format vX.Y.Z)"
      echo "  --release Create a GitHub Release with notes and seeded artifacts after tagging"
      echo "  --notes <path>   Use a specific markdown file for release notes"
      echo "  --notes-auto     Auto-generate notes from git log (previous tag..HEAD) if missing"
      exit 0;;
  esac
done

# --- helpers ---
need() { command -v "$1" >/dev/null 2>&1 || { echo "Missing dependency: $1"; exit 1; }; }
maybe() { command -v "$1" >/dev/null 2>&1; }

require_clean_git() {
  if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "Working tree is dirty. Commit/stash changes before shipping."; exit 1
  fi
}

gh_ready=false
if $AUTO_PR && maybe gh; then
  if gh auth status >/dev/null 2>&1; then gh_ready=true; else echo "gh not authenticated; falling back to manual PRs."; fi
fi

run() { echo "+ $*"; $DRY_RUN || eval "$*"; }

echo "== AU TV Recommender — ship helper =="
echo "Repo: $ROOT"
need docker; need git
require_clean_git

# Base branch auto-detect
BASE_BRANCH="$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null | sed 's@^origin/@@' || true)"
[ -z "$BASE_BRANCH" ] && BASE_BRANCH="main"
echo "Base branch: $BASE_BRANCH"

# Validate version if set/overridden
if ! echo "$VERSION" | grep -Eq '^v[0-9]+\.[0-9]+\.[0-9]+$'; then
  echo "Invalid --version '$VERSION'. Expected format vX.Y.Z (e.g., v0.1.0)."; exit 1
fi

echo "== bootstrap =="
run "bash scripts/dev_bootstrap.sh"

# PR1 — determinism snapshots
echo "== PR1: record & verify snapshots =="
run "cd apps/api && UPDATE_SNAPSHOTS=1 pytest -q tests/test_seed_snapshots.py"
run "cd apps/api && pytest -q tests/test_seed_snapshots.py"
if $AUTO_PR && $gh_ready; then
  run "git checkout -b chore/seed-snapshot-tests"
  run "git add apps/api/tests"
  run "git commit -m \"tests(api): add seeded ID-only snapshot tests for profiles and Family Mix\""
  run "git push -u origin chore/seed-snapshot-tests"
  run "gh pr create -B \"$BASE_BRANCH\" -H chore/seed-snapshot-tests -t \"tests(api): lock determinism with seed=777\" -b \"IDs-only snapshots + double-call equality for ross/wife/son + Family Mix (explain=true).\""
else
  echo "Manual PR1 steps:"
  echo "  git checkout -b chore/seed-snapshot-tests"
  echo "  git add apps/api/tests"
  echo "  git commit -m 'tests(api): add seeded ID-only snapshot tests for profiles and Family Mix'"
  echo "  git push -u origin chore/seed-snapshot-tests"
  echo "  (Open PR: tests(api): lock determinism with seed=777)"
  $DRY_RUN || read -p 'Press Enter after opening PR1…' _
fi

# PR2 — season chip + rationale hint
echo "== PR2: e2e + determinism recheck =="
if maybe pnpm; then run "cd apps/web && pnpm test:e2e"; else run "cd apps/web && npm run test:e2e"; fi
run "cd apps/api && pytest -q tests/test_seed_snapshots.py"
if $AUTO_PR && $gh_ready; then
  run "git checkout -b feat/season-consistent-chip"
  run "git add apps/api apps/web"
  run "git commit -m \"feat(offers): add season-consistent rationale hint and UI chip with tooltip\""
  run "git push -u origin feat/season-consistent-chip"
  run "gh pr create -B \"$BASE_BRANCH\" -H feat/season-consistent-chip -t \"feat(offers): season-consistent UI chip + rationale hint\" -b \"API adds '(showing S{season} on {provider})' when safe; Web shows 'Season match' chip; e2e included.\""
else
  echo "Manual PR2 steps:"
  echo "  git checkout -b feat/season-consistent-chip"
  echo "  git add apps/api apps/web"
  echo "  git commit -m 'feat(offers): add season-consistent rationale hint and UI chip with tooltip'"
  echo "  git push -u origin feat/season-consistent-chip"
  echo "  (Open PR: feat(offers): season-consistent UI chip + rationale hint)"
  $DRY_RUN || read -p 'Press Enter after opening PR2…' _
fi

# prod-like smoke
echo "== prod-like smoke =="
run "docker compose -f infra/docker-compose.prod.yml up -d --build"
run "make smoke"
run "bash -lc 'curl -s http://localhost:8000/metrics | grep recs_build_info || true'"
echo "Open dashboards: make open-prom && make open-grafana && make open-alerts"

# tag (left as an explicit final command)
echo "== tag =="
# Optional auto-merge of PRs when checks pass
if $AUTO_PR && $gh_ready && $MERGE_AFTER; then
  PR1=$(gh pr list --head chore/seed-snapshot-tests --json number --jq '.[0].number' || true)
  PR2=$(gh pr list --head feat/season-consistent-chip --json number --jq '.[0].number' || true)
  if [ -n "${PR1:-}" ]; then run "gh pr merge \"$PR1\" --auto --squash"; else echo "PR1 not found or already merged"; fi
  if [ -n "${PR2:-}" ]; then run "gh pr merge \"$PR2\" --auto --squash"; else echo "PR2 not found or already merged"; fi
  echo "Auto-merge set; GitHub will merge when checks pass."
fi

# Warn on missing prod-like envs before tagging
warn_env=false
for v in JWT_SECRET ALLOW_ORIGINS; do
  if ! grep -q "^$v=" .env 2>/dev/null; then echo "WARN: $v not set in .env"; warn_env=true; fi
done
$warn_env && echo "Set the above before tagging for prod-like correctness."

if git rev-parse -q --verify "refs/tags/$VERSION" >/dev/null; then
  echo "Tag $VERSION already exists; choose a new version before tagging."
else
  echo "Run to tag the release:"
  echo "  ./scripts/tag_release.sh $VERSION"
fi
echo "Tag workflow verifies /readyz, metrics {version, git_sha}, and preflight."

# Optional GitHub Release creation
if $RELEASE_AFTER; then
  need gh
  if ! gh auth status >/dev/null 2>&1; then echo "gh not authed"; exit 1; fi
  # helper for previous tag
  prev_tag() { git describe --tags --abbrev=0 2>/dev/null || true; }
  # Determine notes file
  NOTES_FILE=""
  DEFAULT_NOTES="docs/releases/RELEASE_NOTES_${VERSION}.md"
  FALLBACK_NOTES="docs/releases/RELEASE_NOTES_v0.1.0.md"
  if [ -n "${NOTES_PATH}" ]; then
    if [ -f "${NOTES_PATH}" ]; then
      NOTES_FILE="${NOTES_PATH}"
    else
      echo "ERROR: --notes path not found: ${NOTES_PATH}"; exit 1
    fi
  elif [ -f "${DEFAULT_NOTES}" ]; then
    NOTES_FILE="${DEFAULT_NOTES}"
  elif ${NOTES_AUTO}; then
    PREV="$(prev_tag)"
    echo "Generating release notes from git log (${PREV:-<none>}..HEAD) → ${DEFAULT_NOTES}"
    mkdir -p docs/releases
    {
      echo "# AU TV Recommender — ${VERSION}"
      echo
      echo "Released: $(date -u +%Y-%m-%d)"
      echo
      if [ -n "$PREV" ]; then
        echo "## Changes since ${PREV}"
        git log --pretty='- %s (%h)' "${PREV}..HEAD"
      else
        echo "## Changes"
        git log --pretty='- %s (%h)'
      fi
      echo
      echo "## Notes"
      echo "- Auto-generated via ship script (--notes-auto). Edit as needed."
    } > "${DEFAULT_NOTES}"
    NOTES_FILE="${DEFAULT_NOTES}"
  elif [ -f "${FALLBACK_NOTES}" ]; then
    NOTES_FILE="${FALLBACK_NOTES}"
  else
    echo "WARN: No release notes found. Proceeding without -F notes file."
  fi
  run "./scripts/grab_seed_artifacts.sh 777"
  REL_ARGS=()
  [ -n "${NOTES_FILE:-}" ] && REL_ARGS+=( -F "${NOTES_FILE}" )
  REL_ARGS+=( -t "AU TV Recommender ${VERSION}" )
  REL_ARGS+=( ross_777.json family_777.json )
  run "gh release create \"$VERSION\" ${REL_ARGS[*]}"
fi
