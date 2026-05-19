#!/usr/bin/env bash
# Validate governed activity correlator using ONLY live Cursor hook data.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export ACTIVITY_PROJECT_ROOT="${ACTIVITY_PROJECT_ROOT:-$ROOT}"

exec node "${ROOT}/cursor/scripts/validate-live.js" "$@"
