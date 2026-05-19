#!/usr/bin/env bash
set -euo pipefail

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${HOOK_DIR}/../.." && pwd)"

export ACTIVITY_PROJECT_ROOT="${PROJECT_ROOT}"
# Live build: single canonical log only (no /tmp spike unless explicitly enabled)
export ACTIVITY_SPIKE_ENABLED="${ACTIVITY_SPIKE_ENABLED:-0}"

exec "${PROJECT_ROOT}/cursor/scripts/hooks/append-activity.sh"
