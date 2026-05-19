#!/usr/bin/env bash
# Full local CI gate (same as GitHub Actions activity-correlator): phase tests + coverage.
# Usage: bash cursor/scripts/run-ci-local.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
export ACTIVITY_PROJECT_ROOT="$ROOT"

REPORT_DIR="${ROOT}/reports"
REPORT_FILE="${REPORT_DIR}/ci-local-latest.txt"
COVERAGE_MIN="${COVERAGE_MIN:-85}"
COVERAGE_BRANCH_MIN="${COVERAGE_BRANCH_MIN:-80}"

mkdir -p "$REPORT_DIR"

banner() {
  echo ""
  echo "════════════════════════════════════════════════════════════"
  echo "  SAI Cursor Validation — local CI"
  echo "  Repo: ${ROOT}"
  echo "  Coverage gate: >= ${COVERAGE_MIN}% (branches >= ${COVERAGE_BRANCH_MIN}%)"
  echo "════════════════════════════════════════════════════════════"
  echo ""
}

run_logged() {
  {
    banner
    echo "── Phase tests (0–2, includes VSIX verify) ──"
    bash cursor/scripts/run-phase-tests.sh 2
    echo ""
    echo "── Braid recording gate ──"
    node --test cursor/scripts/tests/test-braid-recording.js
    echo ""
    echo "── Coverage ──"
    bash cursor/scripts/run-coverage.sh
    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo "  LOCAL CI: PASS"
    echo "  Reports:"
    echo "    ${ROOT}/coverage/index.html"
    echo "    ${REPORT_FILE}"
    if compgen -G "${ROOT}/cursor-activity/"*.vsix >/dev/null 2>&1; then
      echo "    VSIX: $(ls -1 "${ROOT}"/cursor-activity/*.vsix | tail -1)"
    fi
    echo "════════════════════════════════════════════════════════════"
  } 2>&1 | tee "$REPORT_FILE"
}

if run_logged; then
  exit 0
fi

echo ""
echo "LOCAL CI: FAILED — see ${REPORT_FILE}"
exit 1
