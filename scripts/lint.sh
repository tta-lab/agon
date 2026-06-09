#!/usr/bin/env bash
# Lint Python files.
set -euo pipefail
cd "$(dirname "$0")/.."
echo "=== Agon: Lint ==="
if command -v uv &>/dev/null; then
  uv run ruff check agon_bench/ tests/
else
  echo "(uv not installed, skip lint)"
fi
