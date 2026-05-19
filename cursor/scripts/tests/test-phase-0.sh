#!/usr/bin/env bash
# Phase 0 exit gate: spike + canonical log path documented.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$ROOT"

echo "=== Phase 0 tests ==="
fail=0

check() {
  if [[ "$1" -eq 0 ]]; then echo "PASS: $2"; else echo "FAIL: $2"; fail=$((fail + 1)); fi
}

test -f cursor/SPIKE-2026-05-18-hooks.md
check $? "SPIKE doc exists"

grep -q 'activity.jsonl' cursor/SPIKE-2026-05-18-hooks.md
check $? "SPIKE documents canonical log path"

test -f cursor/hooks.json.example
check $? "hooks.json.example exists"

node -e "JSON.parse(require('fs').readFileSync('cursor/hooks.json.example','utf8'))"
check $? "hooks.json.example is valid JSON"

echo "Phase 0: $((fail)) failure(s)"
exit "$fail"
