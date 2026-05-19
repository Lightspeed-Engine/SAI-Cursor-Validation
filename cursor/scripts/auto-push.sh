#!/usr/bin/env bash
# Push current branch to origin after a successful pre-commit (non-interactive when .env.local is set).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

if [[ "$(git config --local --get activity.autoPush 2>/dev/null || echo true)" != "true" ]]; then
  echo "auto-push: disabled (git config activity.autoPush false)"
  exit 0
fi

if [[ -f "$ROOT/.env.local" ]]; then
  bash "$ROOT/cursor/scripts/setup-git-auth.sh" >/dev/null 2>&1 || true
fi

REMOTE="${GIT_REMOTE:-origin}"
BRANCH="$(git branch --show-current)"
if [[ -z "$BRANCH" ]]; then
  echo "auto-push: detached HEAD — not pushing" >&2
  exit 1
fi

if ! git remote get-url "$REMOTE" &>/dev/null; then
  URL="${GIT_REMOTE_URL:-https://github.com/Lightspeed-Engine/SAI-Cursor-Validation.git}"
  git remote add "$REMOTE" "$URL"
fi

AHEAD="new"
if git rev-parse "@{u}" &>/dev/null 2>&1; then
  AHEAD="$(git rev-list --count "@{u}..HEAD" 2>/dev/null || echo 0)"
  if [[ "$AHEAD" -eq 0 ]]; then
    echo "auto-push: already up to date with ${REMOTE}/${BRANCH}"
    exit 0
  fi
fi

echo "auto-push: ${REMOTE} ${BRANCH} (${AHEAD} commit(s))..."

if git rev-parse "@{u}" &>/dev/null 2>&1; then
  if [[ "${ACTIVITY_FORCE_PUSH:-}" == "1" ]]; then
    git push --force-with-lease "$REMOTE" "$BRANCH"
  else
    git push "$REMOTE" "$BRANCH"
  fi
else
  git push -u "$REMOTE" "$BRANCH"
fi

REPO_URL="$(git remote get-url "$REMOTE" | sed -E 's|git@github.com:|https://github.com/|; s|\.git$||')"
echo ""
echo "auto-push: done"
echo "  GitHub Actions: ${REPO_URL}/actions"
echo "  Workflow: activity-correlator.yml"
