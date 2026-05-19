#!/usr/bin/env bash
# Project hook wrapper — run from repo root via .cursor/hooks.json
set -euo pipefail

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# cursor/scripts/hooks -> cursor/scripts -> cursor -> repo root
PROJECT_ROOT="$(cd "${HOOK_DIR}/../../.." && pwd)"
SCRIPTS_DIR="${HOOK_DIR}"

export ACTIVITY_PROJECT_ROOT="${PROJECT_ROOT}"
export ACTIVITY_SPIKE_ENABLED="${ACTIVITY_SPIKE_ENABLED:-0}"

exec node "${SCRIPTS_DIR}/append-activity.js"
