#!/usr/bin/env bash
# Git credential helper: reads GITHUB_TOKEN from repo .env.local (project-local, not global git config).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/source-env.sh
source "$SCRIPT_DIR/lib/source-env.sh"

op="${1:-}"
protocol="" host="" path=""

while IFS= read -r line; do
  [[ -z "$line" ]] && break
  key="${line%%=*}"
  val="${line#*=}"
  case "$key" in
    protocol) protocol="$val" ;;
    host) host="$val" ;;
    path) path="$val" ;;
  esac
done

if [[ "$op" != "get" ]]; then
  exit 0
fi

if [[ "$host" != "github.com" ]]; then
  exit 0
fi

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "git-credential-from-env: GITHUB_TOKEN missing — copy .env.local.example to .env.local" >&2
  exit 1
fi

printf 'username=%s\n' "x-access-token"
printf 'password=%s\n' "$GITHUB_TOKEN"
