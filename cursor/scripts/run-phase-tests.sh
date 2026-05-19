#!/usr/bin/env bash
# Run automated phase test suites with regression (each phase runs all prior phases).
#
# Usage:
#   bash cursor/scripts/run-phase-tests.sh          # through latest implemented (2)
#   bash cursor/scripts/run-phase-tests.sh 1        # phase 0 + 1 only
#   ACTIVITY_REQUIRE_LIVE=1 bash cursor/scripts/run-phase-tests.sh  # fail if no live log
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TESTS="$(cd "$(dirname "${BASH_SOURCE[0]}")/tests" && pwd)"
MAX_PHASE="${1:-2}"

export ACTIVITY_PROJECT_ROOT="$ROOT"

echo "Activity correlator — phase tests through Phase ${MAX_PHASE}"
echo "Repo: ${ROOT}"
echo ""

total_fail=0

run_phase() {
  local n="$1"
  local script="${TESTS}/test-phase-${n}.sh"
  if [[ ! -f "$script" ]]; then
    echo "SKIP: Phase ${n} tests not implemented yet (${script})"
    return 0
  fi
  echo "──────── Phase ${n} ────────"
  if bash "$script"; then
    echo ""
  else
    total_fail=$((total_fail + 1))
    echo "Phase ${n} FAILED"
    echo ""
  fi
}

for p in $(seq 0 "$MAX_PHASE"); do
  run_phase "$p"
done

if [[ "$total_fail" -gt 0 ]]; then
  echo "RESULT: FAIL (${total_fail} phase suite(s) failed)"
  exit 1
fi

echo "RESULT: PASS (phases 0–${MAX_PHASE})"
