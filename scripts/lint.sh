#!/usr/bin/env bash
# Lint Python files.
set -euo pipefail
cd "$(dirname "$0")/.."
echo "=== Agon: Lint ==="
if command -v ruff &>/dev/null; then
  ruff check agon_bench/
else
  echo "(ruff not installed, skip lint)"
fi
