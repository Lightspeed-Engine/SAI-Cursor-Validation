#!/usr/bin/env bash
# Unit coverage for hook kit + activity types. Writes coverage/ (lcov + HTML + summary).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

echo "=== Coverage ==="
echo "Repo: ${ROOT}"

if [[ ! -f package-lock.json ]]; then
  npm install --no-audit --no-fund
fi

echo "Compiling cursor-activity (types for schema tests)..."
npm ci --prefix cursor-activity
npm run compile --prefix cursor-activity

export ACTIVITY_PROJECT_ROOT="$ROOT"
export NODE_ENV=test

rm -rf coverage
mkdir -p coverage

COVERAGE_MIN="${COVERAGE_MIN:-85}"

npx c8 \
  --all \
  --check-coverage \
  --lines "$COVERAGE_MIN" \
  --functions "$COVERAGE_MIN" \
  --statements "$COVERAGE_MIN" \
  --branches "${COVERAGE_BRANCH_MIN:-80}" \
  --include='cursor/scripts/hooks/**/*.js' \
  --include='cursor-activity/dist/activity/types.js' \
  --exclude='**/*.test.js' \
  --exclude='**/node_modules/**' \
  --reporter=text \
  --reporter=lcov \
  --reporter=html \
  --report-dir=coverage \
  node --test cursor/scripts/tests/coverage.test.js \
  | tee coverage/summary.txt

echo "Coverage gate: >= ${COVERAGE_MIN}% lines/statements/functions, >= ${COVERAGE_BRANCH_MIN:-80}% branches"

echo ""
echo "Reports:"
echo "  ${ROOT}/coverage/lcov.info"
echo "  ${ROOT}/coverage/index.html"
echo "=== Coverage done ==="
