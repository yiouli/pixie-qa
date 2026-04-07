#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
TEMPLATE_DIR="${SCRIPT_DIR}/pdoc_templates"

cd "${REPO_ROOT}"

rm -rf docs
mkdir -p docs

# Generate markdown API docs for the pixie package and all importable submodules.
uv run pdoc --template-dir "${TEMPLATE_DIR}" --force --output-dir docs pixie
