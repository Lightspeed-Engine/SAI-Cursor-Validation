#!/usr/bin/env bash
# Tag and push a cursor-activity release (triggers publish.yml → GitHub Release + VSIX).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck source=lib/source-env.sh
source "$(dirname "$0")/lib/source-env.sh"
PKG="$ROOT/cursor-activity/package.json"
VERSION_FILE="$ROOT/VERSION"

usage() {
  echo "Usage: $0 <version>   e.g. $0 0.1.0"
  echo "       $0            (read version from cursor-activity/package.json)"
  exit 1
}

VER="${1:-}"
if [[ -z "$VER" ]]; then
  VER="$(node -p "require('$PKG').version" 2>/dev/null || true)"
fi
[[ -n "$VER" ]] || usage

TAG="cursor-activity-v${VER}"

echo "Version: $VER"
echo "Tag:     $TAG"
echo "Root:    $ROOT"
cd "$ROOT"

if [[ -n "$(git status --porcelain)" ]]; then
  echo "ERROR: Working tree not clean. Commit or stash first." >&2
  exit 1
fi

echo "$VER" > "$VERSION_FILE"

node -e "
const fs=require('fs');
const p='$PKG';
const j=JSON.parse(fs.readFileSync(p,'utf8'));
j.version='$VER';
fs.writeFileSync(p, JSON.stringify(j,null,2)+'\n');
" 2>/dev/null || {
  echo "WARN: Could not bump package.json via node; ensure version is $VER manually"
}

bash cursor/scripts/run-phase-tests.sh 2

git add VERSION cursor-activity/package.json CHANGELOG.md 2>/dev/null || true
if git diff --cached --quiet; then
  echo "No version file changes to commit."
else
  git -c user.name="${GIT_USER_NAME:-Lightspeed Engine}" \
      -c user.email="${GIT_USER_EMAIL:-dev@lightspeed-engine.github.io}" \
      commit -m "chore(cursor-activity): release v${VER}"
fi

if git rev-parse "$TAG" >/dev/null 2>&1; then
  echo "Tag $TAG already exists locally."
else
  git tag -a "$TAG" -m "cursor-activity v${VER}"
fi

echo ""
echo "Push to GitHub (requires auth):"
echo "  git push origin main"
echo "  git push origin $TAG"
echo ""
echo "CI will run Activity Correlator on main; Publish workflow builds VSIX on tag."
