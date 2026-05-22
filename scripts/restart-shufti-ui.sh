#!/usr/bin/env bash
# Restart Shufti UI: free port 3005, then start server from Lightspeed scripts (latest on disk).
#
# Usage:
#   ./scripts/restart-shufti-ui.sh              # stop + start (supervised)
#   ./scripts/restart-shufti-ui.sh --sync     # copy viewer from this repo, then restart
#   ./scripts/restart-shufti-ui.sh --status
#   ./scripts/restart-shufti-ui.sh --stop
#   ./scripts/restart-shufti-ui.sh --foreground   # run in foreground (no supervisor)
#
# Environment (optional):
#   LIGHTSPEED_ROOT   default: /mnt/lightspeed-data/Lightspeed-Engine
#   SHUFTI_UI_HOST    default: 100.126.175.99
#   SHUFTI_UI_PORT    default: 3005
#   SHUFTI_SERVER      override path to shufti_ui_server.py
#   SHUFTI_PYTHON     override venv python

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

LIGHTSPEED_ROOT="${LIGHTSPEED_ROOT:-/mnt/lightspeed-data/Lightspeed-Engine}"
SHUFTI_UI_HOST="${SHUFTI_UI_HOST:-100.126.175.99}"
SHUFTI_UI_PORT="${SHUFTI_UI_PORT:-3005}"
SHUFTI_PYTHON="${SHUFTI_PYTHON:-${LIGHTSPEED_ROOT}/LSE-Shufti_venv/bin/python}"
SHUFTI_SCRIPTS="${SHUFTI_SCRIPTS:-${LIGHTSPEED_ROOT}/LSE-Core-2.0-2.1/scripts}"
SHUFTI_SERVER="${SHUFTI_SERVER:-${SHUFTI_SCRIPTS}/shufti_ui_server.py}"
UPSTREAM_RUNNER="${SHUFTI_SCRIPTS}/run_shufti_ui.sh"
LIVE_VIEWER="${SHUFTI_SCRIPTS}/shufti_ui/topology-map-viewer.html"
BUNDLE_VIEWER="${REPO_ROOT}/shufti-system-map/viewer/topology-map-viewer.html"

SYNC=0
ACTION="restart"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --sync|-s) SYNC=1; shift ;;
    --status) ACTION="status"; shift ;;
    --stop) ACTION="stop"; shift ;;
    --start) ACTION="start"; shift ;;
    --foreground|-f) ACTION="foreground"; shift ;;
    --help|-h)
      sed -n '2,20p' "$0"
      exit 0
      ;;
    *) echo "Unknown option: $1 (try --help)" >&2; exit 2 ;;
  esac
done

die() { echo "restart-shufti-ui: $*" >&2; exit 1; }

[[ -x "${SHUFTI_PYTHON}" ]] || die "Python not found: ${SHUFTI_PYTHON}"
[[ -f "${SHUFTI_SERVER}" ]] || die "Server not found: ${SHUFTI_SERVER}"

if [[ "${SYNC}" -eq 1 ]]; then
  if [[ -f "${BUNDLE_VIEWER}" ]]; then
    cp "${BUNDLE_VIEWER}" "${LIVE_VIEWER}"
    echo "Synced viewer: ${BUNDLE_VIEWER} -> ${LIVE_VIEWER}"
  else
    echo "No bundle viewer at ${BUNDLE_VIEWER}; skip sync." >&2
  fi
fi

export LIGHTSPEED_ROOT SHUFTI_UI_HOST SHUFTI_UI_PORT

if [[ -x "${UPSTREAM_RUNNER}" ]]; then
  echo "Using upstream runner: ${UPSTREAM_RUNNER} ${ACTION}"
  exec env \
    SHUFTI_UI_HOST="${SHUFTI_UI_HOST}" \
    SHUFTI_UI_PORT="${SHUFTI_UI_PORT}" \
    "${UPSTREAM_RUNNER}" "${ACTION}"
fi

# Fallback if run_shufti_ui.sh missing
free_port() {
  if command -v fuser >/dev/null 2>&1; then
    fuser -k "${SHUFTI_UI_PORT}/tcp" >/dev/null 2>&1 || true
  elif command -v lsof >/dev/null 2>&1; then
    local pids
    pids="$(lsof -ti ":${SHUFTI_UI_PORT}" 2>/dev/null || true)"
    [[ -n "${pids}" ]] && kill ${pids} 2>/dev/null || true
  fi
  sleep 1
}

health() {
  curl -fsS --max-time 3 "http://${SHUFTI_UI_HOST}:${SHUFTI_UI_PORT}/api/config" >/dev/null
}

case "${ACTION}" in
  stop)
    free_port
    echo "Port ${SHUFTI_UI_PORT} cleared."
    ;;
  status)
    if health; then
      echo "OK  http://${SHUFTI_UI_HOST}:${SHUFTI_UI_PORT}/"
    else
      echo "DOWN  http://${SHUFTI_UI_HOST}:${SHUFTI_UI_PORT}/"
      exit 1
    fi
    ;;
  start|restart)
    free_port
    cd "${SHUFTI_SCRIPTS}"
    nohup env SHUFTI_UI_ASYNC_MODE="${SHUFTI_UI_ASYNC_MODE:-threading}" \
      "${SHUFTI_PYTHON}" "${SHUFTI_SERVER}" --host "${SHUFTI_UI_HOST}" --port "${SHUFTI_UI_PORT}" \
      >>"${LIGHTSPEED_ROOT}/data/shufti_ui/shufti_ui_server_stdout.log" 2>&1 &
    echo "Started pid=$! (logs: ${LIGHTSPEED_ROOT}/data/shufti_ui/shufti_ui_server_stdout.log)"
    for _ in $(seq 1 30); do
      if health; then
        echo "Healthy: http://${SHUFTI_UI_HOST}:${SHUFTI_UI_PORT}/"
        echo "Viewer: http://${SHUFTI_UI_HOST}:${SHUFTI_UI_PORT}/static/topology-map-viewer.html?run_id=<run_id>"
        exit 0
      fi
      sleep 0.5
    done
    die "Server did not become healthy within 15s"
    ;;
  foreground)
    free_port
    cd "${SHUFTI_SCRIPTS}"
    exec env SHUFTI_UI_ASYNC_MODE="${SHUFTI_UI_ASYNC_MODE:-threading}" \
      "${SHUFTI_PYTHON}" "${SHUFTI_SERVER}" --host "${SHUFTI_UI_HOST}" --port "${SHUFTI_UI_PORT}"
    ;;
esac
