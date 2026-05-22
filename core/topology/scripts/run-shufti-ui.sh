#!/usr/bin/env bash
# Run upstream Shufti UI server (codebase topology). Does not copy Python into SAI repo.
set -euo pipefail

LIGHTSPEED_ROOT="${LIGHTSPEED_ROOT:-/mnt/lightspeed-data/Lightspeed-Engine}"
PYTHON="${SHUFTI_PYTHON:-${LIGHTSPEED_ROOT}/LSE-Shufti_venv/bin/python}"
SERVER="${SHUFTI_SERVER:-${LIGHTSPEED_ROOT}/LSE-Core-2.0-2.1/scripts/shufti_ui_server.py}"
UPSTREAM_RUNNER="${SHUFTI_RUNNER:-${LIGHTSPEED_ROOT}/LSE-Core-2.0-2.1/scripts/run_shufti_ui.sh}"
HOST="${SHUFTI_UI_HOST:-127.0.0.1}"
PORT="${SHUFTI_UI_PORT:-3005}"
ASYNC_MODE="${SHUFTI_UI_ASYNC_MODE:-threading}"

if [[ -x "${UPSTREAM_RUNNER}" ]]; then
  exec env \
    SHUFTI_UI_HOST="${HOST}" \
    SHUFTI_UI_PORT="${PORT}" \
    SHUFTI_UI_ASYNC_MODE="${ASYNC_MODE}" \
    "${UPSTREAM_RUNNER}" "${1:-foreground}"
fi

if [[ ! -f "${SERVER}" ]]; then
  echo "Shufti server not found: ${SERVER}" >&2
  echo "Set LIGHTSPEED_ROOT or SHUFTI_SERVER." >&2
  exit 1
fi

exec env SHUFTI_UI_ASYNC_MODE="${ASYNC_MODE}" "${PYTHON}" "${SERVER}" --host "${HOST}" --port "${PORT}"
