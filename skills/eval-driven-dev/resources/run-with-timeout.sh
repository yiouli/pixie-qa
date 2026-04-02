#!/usr/bin/env bash
# Run a command in the background and automatically kill it after a timeout.
#
# Usage:
#   bash resources/run-with-timeout.sh <timeout_seconds> <command> [args...]
#
# Examples:
#   bash resources/run-with-timeout.sh 30 uv run uvicorn app:app --port 8000
#   bash resources/run-with-timeout.sh 60 uv run python -m myapp.server
#
# The script:
#   1. Starts the command with nohup in the background
#   2. Prints the PID for reference
#   3. Spawns a background watchdog that kills the process after <timeout_seconds>
#   4. Returns immediately so you can continue working
#
# The process will be killed automatically after the timeout, or you can
# kill it manually with: kill <PID>
set -u

if [ $# -lt 2 ]; then
  echo "Usage: bash resources/run-with-timeout.sh <timeout_seconds> <command> [args...]"
  exit 1
fi

TIMEOUT_SECS="$1"
shift

# Start the command in the background with nohup
nohup "$@" > /tmp/run-with-timeout.log 2>&1 &
CMD_PID=$!

echo "Started PID ${CMD_PID} (timeout: ${TIMEOUT_SECS}s, log: /tmp/run-with-timeout.log)"

# Spawn a watchdog that kills the process after the timeout
(
  sleep "$TIMEOUT_SECS"
  if kill -0 "$CMD_PID" 2>/dev/null; then
    kill "$CMD_PID" 2>/dev/null || true
    sleep 2
    if kill -0 "$CMD_PID" 2>/dev/null; then
      kill -9 "$CMD_PID" 2>/dev/null || true
    fi
  fi
) &
WATCHDOG_PID=$!

echo "Watchdog PID ${WATCHDOG_PID} will kill process after ${TIMEOUT_SECS}s"
