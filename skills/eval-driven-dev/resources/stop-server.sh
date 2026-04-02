#!/usr/bin/env bash
# Stop the pixie web UI server by reading the port from server.lock
# and killing the process bound to that port.
set -u

PIXIE_ROOT="${PIXIE_ROOT:-pixie_qa}"
LOCK_FILE="${PIXIE_ROOT}/server.lock"

if [ ! -f "$LOCK_FILE" ]; then
  echo "No server.lock found at ${LOCK_FILE} — server may not be running."
  exit 0
fi

PORT=$(cat "$LOCK_FILE")
echo "Found server.lock with port ${PORT}"

# Find the process listening on that port and kill it
PID=$(lsof -ti "tcp:${PORT}" 2>/dev/null || ss -tlnp "sport = :${PORT}" 2>/dev/null | grep -oP 'pid=\K[0-9]+' || true)

if [ -z "$PID" ]; then
  echo "No process found on port ${PORT} — cleaning up stale lock."
  rm -f "$LOCK_FILE"
  exit 0
fi

echo "Killing server process ${PID} on port ${PORT}"
kill "$PID" 2>/dev/null || true
sleep 1

# Force kill if still running
if kill -0 "$PID" 2>/dev/null; then
  echo "Process still running, sending SIGKILL"
  kill -9 "$PID" 2>/dev/null || true
fi

rm -f "$LOCK_FILE"
echo "Server stopped."
