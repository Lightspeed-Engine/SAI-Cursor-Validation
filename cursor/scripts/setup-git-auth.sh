#!/usr/bin/env bash
# Configure this repo only (--local) to push via GITHUB_TOKEN in .env.local.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

# shellcheck source=lib/source-env.sh
source "$(dirname "$0")/lib/source-env.sh"

if [[ ! -f "$ROOT/.env.local" ]]; then
  echo "Missing $ROOT/.env.local"
  echo "  cp .env.local.example .env.local"
  echo "  # edit GITHUB_TOKEN=..."
  exit 1
fi

if [[ -z "${GITHUB_TOKEN:-}" ]] || [[ "$GITHUB_TOKEN" == *"REPLACE_ME"* ]]; then
  echo "Set a real GITHUB_TOKEN in .env.local" >&2
  exit 1
fi

HELPER="$ROOT/cursor/scripts/git-credential-from-env.sh"
chmod +x "$HELPER" "$ROOT/cursor/scripts/lib/source-env.sh"

REMOTE_URL="${GIT_REMOTE_URL:-https://github.com/Lightspeed-Engine/SAI-Cursor-Validation.git}"
if git remote get-url origin &>/dev/null; then
  git remote set-url origin "$REMOTE_URL"
else
  git remote add origin "$REMOTE_URL"
fi

# Repo-local only — does not touch global git config.
git config --local --replace-all credential.helper "$HELPER"
git config --local credential.useHttpPath true

NAME="${GIT_USER_NAME:-Lightspeed Engine}"
EMAIL="${GIT_USER_EMAIL:-dev@lightspeed-engine.github.io}"
git config --local user.name "$NAME"
git config --local user.email "$EMAIL"

echo "OK: git auth for $ROOT (credential helper → .env.local)"
echo "Remote: $(git remote get-url origin)"

# Quick probe (no token printed)
if GIT_TERMINAL_PROMPT=0 git ls-remote origin HEAD &>/dev/null; then
  echo "OK: can read from origin"
else
  echo "WARN: ls-remote failed — check token scopes and org SSO authorization" >&2
  exit 1
fi
