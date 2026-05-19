#!/usr/bin/env bash
# Start braid + aardvark daemons (recording off until UI/API start).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

export BRAID_HOST="${BRAID_HOST:-127.0.0.1}"
export BRAID_PORT="${BRAID_PORT:-4711}"
export AARDVARK_HOST="${AARDVARK_HOST:-127.0.0.1}"
export AARDVARK_PORT="${AARDVARK_PORT:-4712}"
export BRAID_LOG_PATH="${BRAID_LOG_PATH:-$ROOT/.cursor/activity/activity.jsonl}"

chmod +x core/braid/bin/braid.js core/aardvark/bin/aardvark.js

echo "Starting sai-braid on ${BRAID_HOST}:${BRAID_PORT}..."
node core/braid/bin/braid.js &
BRAID_PID=$!

echo "Starting sai-aardvark control on ${AARDVARK_HOST}:${AARDVARK_PORT}..."
node core/aardvark/bin/aardvark.js &
AARDVARK_PID=$!

echo ""
echo "PIDs: braid=${BRAID_PID} aardvark=${AARDVARK_PID}"
echo "Stop: kill ${BRAID_PID} ${AARDVARK_PID}"
echo "Recording: OFF until Activity: Start Recording or POST /v1/recording/start"
wait
