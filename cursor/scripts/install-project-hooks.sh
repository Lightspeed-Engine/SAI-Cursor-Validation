#!/usr/bin/env bash
# Copy hook templates into a project's .cursor/ (run from repo root).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET="${1:-$ROOT}"

mkdir -p "${TARGET}/.cursor/hooks"
cp "${ROOT}/cursor/hooks.json.example" "${TARGET}/.cursor/hooks.json"
cp "${ROOT}/.cursor/hooks/append-activity.sh" "${TARGET}/.cursor/hooks/append-activity.sh"
chmod +x "${TARGET}/.cursor/hooks/append-activity.sh"
chmod +x "${ROOT}/cursor/scripts/hooks/"*.sh 2>/dev/null || true

if ! grep -qF '.cursor/activity/' "${TARGET}/.gitignore" 2>/dev/null; then
  printf '\n# Governed activity correlator (sensitive audit log)\n.cursor/activity/\n' >> "${TARGET}/.gitignore"
fi

echo "Installed hooks into ${TARGET}/.cursor/"
echo "Run an Agent session, then inspect ${TARGET}/.cursor/activity/activity.jsonl"
