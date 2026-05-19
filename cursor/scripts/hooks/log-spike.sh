#!/usr/bin/env bash
# Phase 0: append raw hook stdin to spike log (plus normalized log via append-activity).
set -euo pipefail

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${HOOK_DIR}/../../.." && pwd)"
SPIKE_LOG="${ACTIVITY_SPIKE_PATH:-/tmp/cursor-hook-spike.jsonl}"

mkdir -p "$(dirname "${SPIKE_LOG}")"
ts="$(date -u +"%Y-%m-%dT%H:%M:%S.%3NZ" 2>/dev/null || date -u +"%Y-%m-%dT%H:%M:%SZ")"
raw="$(cat)"
printf '{"capturedAt":"%s","raw":%s}\n' "${ts}" "${raw}" >> "${SPIKE_LOG}"

export ACTIVITY_PROJECT_ROOT="${PROJECT_ROOT}"
export ACTIVITY_SPIKE_ENABLED=0
exec node "${HOOK_DIR}/append-activity.js" <<< "${raw}"
