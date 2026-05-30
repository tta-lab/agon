#!/usr/bin/env bash
# Format Python and shell files.
set -euo pipefail
cd "$(dirname "$0")/.."
echo "=== Agon: Format ==="
PYTHON_FORMATTED=0
SHELL_FORMATTED=0
if command -v ruff &>/dev/null; then
  ruff format agon_bench/ && PYTHON_FORMATTED=1
else
  echo "(ruff not installed, skip Python format)"
fi
if command -v shfmt &>/dev/null; then
  shopt -s globstar nullglob
  shfmt -w agon_bench/**/*.sh scripts/*.sh && SHELL_FORMATTED=1
else
  echo "(shfmt not installed, skip shell format)"
fi
if [ $PYTHON_FORMATTED -eq 0 ] && [ $SHELL_FORMATTED -eq 0 ]; then
  echo "No formatters installed. Install ruff and shfmt for formatting."
fi
