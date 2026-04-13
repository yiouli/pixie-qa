#!/usr/bin/env bash
# Setup script for eval-driven-dev skill.
# Updates the skill, installs/upgrades pixie-qa[all], initializes the
# pixie working directory, and starts the web UI server in the background.
# Failures are non-fatal — the workflow continues even if a step here is
# blocked by the environment.
set -u

echo "=== Updating skill ==="
npx skills update yiouli/pixie-qa -g -y && npx skills update yiouli/pixie-qa -p -y || {
  echo "(skill update failed — proceeding with existing version)"
}

echo ""
echo "=== Installing / upgrading pixie-qa[all] ==="
if [ -f uv.lock ]; then
  # uv add does universal resolution across all Python versions in
  # requires-python.  If the host project supports a Python version
  # where pixie-qa is unavailable (e.g. 3.10), uv add fails.
  # Fall back to uv pip install which only targets the active interpreter.
  uv add "pixie-qa[all]>=0.7.0,<0.8.0" --upgrade 2>&1 || {
    echo "(uv add failed — falling back to uv pip install)"
    uv pip install "pixie-qa[all]>=0.7.0,<0.8.0" 2>&1 || true
  }
elif [ -f poetry.lock ]; then
  poetry add "pixie-qa[all]>=0.7.0,<0.8.0"
else
  pip install --upgrade "pixie-qa[all]>=0.7.0,<0.8.0"
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
if [ -f uv.lock ]; then
  uv run pixie start
elif [ -f poetry.lock ]; then
  poetry run pixie start
else
  pixie start
fi

echo ""
echo "=== Setup complete ==="
