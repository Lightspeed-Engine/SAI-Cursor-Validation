#!/usr/bin/env bash
# S8 — exit 0 when Shufti :3005, AI-Spy :8887, braid :4711 accept TCP (PLAN § S8).
set -euo pipefail

SHUFTI_HOST="${SHUFTI_HOST:-127.0.0.1}"
SHUFTI_PORT="${SHUFTI_PORT:-3005}"
SPY_PORT="${AI_SPY_PORT:-8887}"
BRAID_PORT="${BRAID_PORT:-4711}"

check_port() {
  local name="$1" host="$2" port="$3"
  if timeout 2 bash -c "echo >/dev/tcp/${host}/${port}" 2>/dev/null; then
    echo "OK  ${name} ${host}:${port}"
    return 0
  fi
  echo "FAIL ${name} ${host}:${port} not listening"
  return 1
}

failed=0
check_port "shufti" "$SHUFTI_HOST" "$SHUFTI_PORT" || failed=1
check_port "ai-spy" "$SHUFTI_HOST" "$SPY_PORT" || failed=1
check_port "braid" "$SHUFTI_HOST" "$BRAID_PORT" || failed=1

if [[ "$failed" -ne 0 ]]; then
  exit 1
fi
echo "S8 check-validation-stack: PASS"
exit 0
