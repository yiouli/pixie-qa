#!/usr/bin/env bash
# Run the full eval pipeline for the email classifier.
#
# Usage:  bash run_evals.sh
#
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHONPATH=/home/yiouli/repo/pixie-qa
export PYTHONPATH

cd "$PROJECT_DIR"

echo "=== Step 1: Build dataset ==="
python build_dataset.py

echo ""
echo "=== Step 2: Verify dataset ==="
pixie dataset list

echo ""
echo "=== Step 3: Run eval tests ==="
pixie-test tests/ -v
