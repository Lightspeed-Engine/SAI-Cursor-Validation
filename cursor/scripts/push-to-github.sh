#!/usr/bin/env bash
# Push full tree + tags to GitHub (run on your machine with gh/git auth).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

# shellcheck source=lib/source-env.sh
source "$(dirname "$0")/lib/source-env.sh"
if [[ -f "$ROOT/.env.local" ]]; then
  bash "$ROOT/cursor/scripts/setup-git-auth.sh"
fi

REMOTE="${1:-origin}"
URL="${2:-https://github.com/Lightspeed-Engine/SAI-Cursor-Validation.git}"

if ! git remote get-url "$REMOTE" &>/dev/null; then
  git remote add "$REMOTE" "$URL"
fi

echo "Remote: $(git remote get-url "$REMOTE)"
echo "Commits to push:"
git log --oneline origin/main..main 2>/dev/null || git log --oneline -3

echo ""
echo "GitHub may only have a LICENSE stub — force-with-lease replaces main with this tree."
if [[ "${PUSH_YES:-}" != "1" ]]; then
  read -r -p "Push main + tags to $REMOTE? [y/N] " ans
  [[ "${ans,,}" == "y" ]] || exit 0
fi

git push --force-with-lease "$REMOTE" main
git push "$REMOTE" --tags

echo "Done. Check:"
echo "  https://github.com/Lightspeed-Engine/SAI-Cursor-Validation/actions"
echo "  https://github.com/Lightspeed-Engine/SAI-Cursor-Validation/releases"
