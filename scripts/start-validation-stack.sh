#!/usr/bin/env bash
# S8 — document-only stub until full stack orchestration lands (PLAN § S8).
# Pre-commit / CI use check-validation-stack.sh against already-running services.
set -euo pipefail

echo "start-validation-stack.sh: not implemented yet."
echo "Start manually:"
echo "  1) core/topology/scripts/run-shufti-ui.sh  (Shufti :3005)"
echo "  2) Lightspeed MCP agent_detection_daemon.py (AI-Spy :8887)"
echo "  3) braid service (:4711)"
echo "Then: bash scripts/check-validation-stack.sh"
exit 1
