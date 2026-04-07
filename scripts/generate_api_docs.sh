#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"

rm -rf docs
mkdir -p docs

# Generate markdown API docs for the pixie package and all importable submodules.
uv run pdoc --force --output-dir docs pixie
