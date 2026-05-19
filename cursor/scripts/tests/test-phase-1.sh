#!/usr/bin/env bash
# Phase 1 exit gate: hook kit + redaction + live log validation.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$ROOT"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Phase 1 tests ==="
fail=0

check() {
  if [[ "$1" -eq 0 ]]; then echo "PASS: $2"; else echo "FAIL: $2"; fail=$((fail + 1)); fi
}

# --- structural (no Cursor session required) ---
for f in \
  cursor/scripts/hooks/append-activity.js \
  cursor/scripts/hooks/redact.js \
  cursor/scripts/hooks/append-activity.sh \
  .cursor/hooks.json \
  .cursor/hooks/append-activity.sh; do
  test -f "$f"
  check $? "file exists: $f"
done

test -x .cursor/hooks/append-activity.sh
check $? "append-activity.sh executable"

grep -qF '.cursor/activity/' .gitignore
check $? ".gitignore contains .cursor/activity/"

node "$SCRIPT_DIR/test-redact.js"
check $? "redact unit checks"

node -e "
const cfg = JSON.parse(require('fs').readFileSync('.cursor/hooks.json','utf8'));
const fs = require('fs');
const path = require('path');
for (const [ev, arr] of Object.entries(cfg.hooks || {})) {
  for (const h of arr) {
    const p = path.join(process.cwd(), h.command);
    if (!fs.existsSync(p)) throw new Error('missing hook command: ' + p);
  }
}
"
check $? "hooks.json commands exist on disk"

# --- live log (requires prior Agent session in this workspace) ---
export ACTIVITY_PROJECT_ROOT="$ROOT"
if [[ "${ACTIVITY_REQUIRE_LIVE:-0}" == "1" ]]; then
  bash cursor/scripts/validate-live.sh >/dev/null
  check $? "validate-live (required)"
elif [[ -f .cursor/activity/activity.jsonl ]] && [[ -s .cursor/activity/activity.jsonl ]]; then
  bash cursor/scripts/validate-live.sh >/dev/null
  check $? "validate-live (log present)"
else
  echo "SKIP: validate-live — no activity.jsonl (run Agent session or ACTIVITY_REQUIRE_LIVE=1)"
fi

echo "Phase 1: $((fail)) failure(s)"
exit "$fail"
