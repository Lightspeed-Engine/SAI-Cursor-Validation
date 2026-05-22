#!/usr/bin/env bash
# Shufti + AI-Spy slice tests (PLAN-2026-05-21-shufti-aispy-phased-slices.md)
# Central log: reports/shufti-slice-latest.jsonl (TEST_LOG_PATH)
# Usage:
#   bash scripts/run-shufti-slice-tests.sh offline   # pre-commit + PR merge gate
#   RUN_LIVE=1 bash scripts/run-shufti-slice-tests.sh live
#   bash scripts/run-shufti-slice-tests.sh all
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
MODE="${1:-offline}"
VENV="${ROOT}/tests/.venv"
export PYTHONPATH="${ROOT}"
export TEST_LOG_PATH="${ROOT}/reports/shufti-slice-latest.jsonl"
export SLICE_TEST_MODE="${MODE}"
export FINISH_RUN_DEFERRED=1

ensure_py() {
  if [[ ! -x "${VENV}/bin/python" ]]; then
    python3 -m venv "${VENV}"
  fi
  "${VENV}/bin/pip" install -q -r tests/requirements.txt
}

PY="${VENV}/bin/python"
TOOL_EXIT=0

init_log() {
  mkdir -p "${ROOT}/reports"
  : > "${TEST_LOG_PATH}"
  "${PY}" -c "
from tests.lib.test_log import TestLog
TestLog().session_start('run-shufti-slice-tests', '${MODE}')
"
}

finish_log() {
  "${PY}" -c "
from tests.lib.test_log import finish_run
import sys
sys.exit(finish_run(${TOOL_EXIT}))
"
}

banner() {
  ensure_py
  "${PY}" -c "
from tests.lib.rich_report import print_session_banner
print_session_banner('run-shufti-slice-tests', '${MODE}', '${TEST_LOG_PATH}')
" 2>/dev/null || {
    echo ""
    echo "  Shufti slice tests — mode=${MODE}"
    echo "  Log: ${TEST_LOG_PATH}"
  }
}

run_offline() {
  echo "── Python offline (META catalog + S0) ──"
  ensure_py
  "${PY}" -m pytest tests/shufti/test_selder_error_catalog.py tests/shufti/s0 -m offline -v --tb=short \
    || TOOL_EXIT=$?

  echo "── Node offline (S2, S5) ──"
  if ! command -v npx >/dev/null 2>&1; then
    echo "[TEST-LOG] FAIL SAIV-TEST-0006: npx not found"
    TOOL_EXIT=1
    return
  fi
  npx --yes tsx --test tests/shufti/s2/test_topology_merge_offline.ts || TOOL_EXIT=$?
  npx --yes tsx --test tests/shufti/s5/test_sectional_stitch_offline.ts || TOOL_EXIT=$?
}

run_contract() {
  echo "── Future-slice contracts (xfail until implemented) ──"
  ensure_py
  "${PY}" -m pytest tests/shufti/s3 tests/shufti/s8 -m offline -v --tb=short || TOOL_EXIT=$?
}

run_live() {
  if [[ "${RUN_LIVE:-0}" != "1" ]]; then
    echo "── Live slices skipped (set RUN_LIVE=1) ──"
    return
  fi
  echo "── Python live (S1) ──"
  ensure_py
  "${PY}" -m pytest tests/shufti/s1 -m live -v --tb=short || TOOL_EXIT=$?
  echo "── S8 port check ──"
  bash scripts/check-validation-stack.sh || TOOL_EXIT=$?
}

banner
init_log

case "$MODE" in
  offline) run_offline ;;
  contract) run_contract ;;
  live) run_live ;;
  all)
    run_offline
    run_contract
    run_live
    ;;
  *)
    echo "Usage: $0 offline|contract|live|all"
    exit 2
    ;;
esac

finish_log
