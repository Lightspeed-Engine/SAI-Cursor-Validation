#!/usr/bin/env bash
# Phase 2 exit gate: cursor-activity compiles, packages, parses live log lines.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$ROOT"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Phase 2 tests ==="
fail=0

check() {
  if [[ "$1" -eq 0 ]]; then echo "PASS: $2"; else echo "FAIL: $2"; fail=$((fail + 1)); fi
}

test -f cursor-activity/package.json
check $? "cursor-activity/package.json"

test -d cursor-activity/src
check $? "cursor-activity/src"

(
  cd cursor-activity
  npm run compile --silent
)
check $? "npm run compile"

test -f cursor-activity/dist/extension.js
check $? "dist/extension.js"

for mod in store tailer types logPath sampleWriter; do
  test -f "cursor-activity/dist/activity/${mod}.js"
  check $? "dist/activity/${mod}.js"
done

node -e "
const pkg = require('./cursor-activity/package.json');
if (!pkg.engines?.vscode) throw new Error('missing engines.vscode');
if (!pkg.contributes?.views) throw new Error('missing contributes.views');
if (!pkg.contributes?.commands?.some(c => c.command === 'cursorActivity.sampleGitStatus')) {
  throw new Error('missing sample git command');
}
"
check $? "package.json contributes"

node "$SCRIPT_DIR/test-schema-parse.js"
check $? "parse live log lines (or skip if no log)"

bash "$SCRIPT_DIR/verify-vsix.sh"
check $? "npm run package + VSIX contents"

echo "Phase 2: $((fail)) failure(s)"
exit "$fail"
