#!/usr/bin/env bash
# Setup script for eval-driven-dev skill.
# Updates the skill, installs/upgrades pixie-qa[all], initializes the
# pixie working directory, and starts the web UI server in the background.
# Failures are non-fatal — the workflow continues even if a step here is
# blocked by the environment.
set -u

echo "=== Updating skill ==="
npx skills update || echo "(skill update skipped)"

echo ""
echo "=== Installing / upgrading pixie-qa[all] ==="
if [ -f uv.lock ]; then
  uv add "pixie-qa[all]>=0.3.0,<0.4.0" --upgrade
elif [ -f poetry.lock ]; then
  poetry add "pixie-qa[all]>=0.3.0,<0.4.0"
else
  pip install --upgrade "pixie-qa[all]>=0.3.0,<0.4.0"
fi

echo ""
echo "=== Initializing pixie working directory ==="
if [ -f uv.lock ]; then
  uv run pixie init
elif [ -f poetry.lock ]; then
  poetry run pixie init
else
  pixie init
fi

echo ""
echo "=== Starting web UI server (background) ==="
PIXIE_ROOT="${PIXIE_ROOT:-pixie_qa}"
if [ -f uv.lock ]; then
  nohup uv run pixie start > "${PIXIE_ROOT}/server.log" 2>&1 &
elif [ -f poetry.lock ]; then
  nohup poetry run pixie start > "${PIXIE_ROOT}/server.log" 2>&1 &
else
  nohup pixie start > "${PIXIE_ROOT}/server.log" 2>&1 &
fi
echo "Web UI server started (PID $!, log: ${PIXIE_ROOT}/server.log)"

echo ""
echo "=== Setup complete ==="
